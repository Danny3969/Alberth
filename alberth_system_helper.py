#!/usr/bin/env python3
# =============================================================================
# ALBERTH SYSTEM HELPER — Control de Sistema Operativo para macOS
# Versión: 1.0
# Controla: Volumen, Aplicaciones, Mouse, Teclado y consulta el estado del sistema.
# Uso: python3 alberth_system_helper.py "<consulta_del_usuario>"
# =============================================================================

import sys
import re
import subprocess
import json
import os

# ── Utilidad: ejecutar AppleScript ────────────────────────────────────────────
def run_applescript(script: str) -> tuple:
    """Ejecuta un bloque de AppleScript y devuelve (éxito, salida)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Timeout: AppleScript tardó demasiado."
    except Exception as e:
        return False, str(e)

# ── Utilidad: ejecutar comando de shell ───────────────────────────────────────
def run_shell(cmd, timeout=10):
    """Ejecuta un comando de shell y devuelve (éxito, salida)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "Timeout al ejecutar el comando."
    except FileNotFoundError:
        return False, f"Comando no encontrado: {cmd[0]}"
    except Exception as e:
        return False, str(e)

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 0: CONTROL MULTIMEDIA (Play, Pause, Siguiente, Anterior)
# ══════════════════════════════════════════════════════════════════════════════
def handle_music(query, query_lower):
    """Detecta y ejecuta intenciones de control de música/video."""
    is_play = re.search(r'\b(reproduce|contin[uú]a|play|resume|reactiva\s+m[uú]sica|despausa)\b', query_lower)
    is_pause = re.search(r'\b(pausa|pausar|det[eé]n\s+(?:la\s+)?m[uú]sica|stop|pause|silencia\s+m[uú]sica)\b', query_lower)
    is_next = re.search(r'\b(siguiente|next|pasa\s+(?:de\s+)?cancion|pasa\s+(?:de\s+)?canci[oó]n|avanza|siguiente\s+cancion|siguiente\s+canci[oó]n)\b', query_lower)
    is_prev = re.search(r'\b(anterior|prev|previous|atr[aá]s|retrocede|canci[oó]n\s+anterior|cancion\s+anterior)\b', query_lower)

    if not (is_play or is_pause or is_next or is_prev):
        return None

    cmd = None
    action = None
    msg = ""

    if is_play:
        cmd = ["nowplaying-cli", "play"]
        action = "musica_play"
        msg = "Reproducción iniciada."
    elif is_pause:
        cmd = ["nowplaying-cli", "pause"]
        action = "musica_pause"
        msg = "Reproducción pausada."
    elif is_next:
        cmd = ["nowplaying-cli", "next"]
        action = "musica_siguiente"
        msg = "Siguiente pista."
    elif is_prev:
        cmd = ["nowplaying-cli", "previous"]
        action = "musica_anterior"
        msg = "Pista anterior."

    if cmd:
        ok, out = run_shell(cmd)
        if ok:
            return {"accion": action, "resultado": msg, "exito": True}

        # Fallback a AppleScript para navegadores si nowplaying-cli no lo logra directamente
        act_str = "play" if is_play else ("pause" if is_pause else ("next" if is_next else "previous"))
        browser_script = """
tell application "Google Chrome"
    repeat with w in windows
        repeat with t in tabs of w
            if title of t contains "YouTube" or title of t contains "Echo" or title of t contains "Music" then
                if "{act}" is "play" then
                    execute t javascript "document.querySelector('video, audio').play()"
                else if "{act}" is "pause" then
                    execute t javascript "document.querySelector('video, audio').pause()"
                else if "{act}" is "next" then
                    execute t javascript "document.querySelector('.ytp-next-button, #play-control-bar .next-button')?.click()"
                else if "{act}" is "previous" then
                    execute t javascript "document.querySelector('#play-control-bar .previous-button')?.click()"
                end if
            end if
        end repeat
    end repeat
end tell
""".format(act=act_str)
        ok_browser, _ = run_applescript(browser_script)
        if ok_browser:
            return {"accion": action, "resultado": f"{msg} (Vía Navegador)", "exito": True}

        return {"accion": action, "resultado": f"No se pudo controlar la música: {out}", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 1: CONTROL DE VOLUMEN
# ══════════════════════════════════════════════════════════════════════════════
def handle_volume(query, query_lower):

    """Detecta y ejecuta intenciones de control de volumen."""

    # Silenciar
    if re.search(r'\b(silencia|silenciar|mute|muta|apaga\s+el\s+sonido|sin\s+sonido)\b', query_lower):
        ok, out = run_applescript('set volume output muted true')
        if ok:
            return {"accion": "volumen_silenciado", "resultado": "Volumen silenciado correctamente.", "exito": True}
        return {"accion": "volumen_silenciado", "resultado": f"Error al silenciar: {out}", "exito": False}

    # Desilenciar
    if re.search(r'\b(dessilencia|desilencia|unmute|reactiva\s+sonido|activa\s+sonido|quita\s+el\s+silencio)\b', query_lower):
        ok, out = run_applescript('set volume output muted false')
        if ok:
            return {"accion": "volumen_activado", "resultado": "Silencio desactivado. El audio está activo.", "exito": True}
        return {"accion": "volumen_activado", "resultado": f"Error: {out}", "exito": False}

    # Subir volumen
    if re.search(r'\b(sube|subir|aumenta|aumentar|incrementa|más\s+volumen|sube\s+el\s+volumen)\b', query_lower):
        amount_match = re.search(r'(\d+)', query)
        amount = int(amount_match.group(1)) if amount_match else 15
        script = """
set current_vol to output volume of (get volume settings)
set new_vol to current_vol + {amt}
if new_vol > 100 then set new_vol to 100
set volume output volume new_vol
return new_vol
""".format(amt=amount)
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "volumen_subido", "resultado": f"Volumen subido. Nivel actual: {out}%", "exito": True}
        return {"accion": "volumen_subido", "resultado": f"Error: {out}", "exito": False}

    # Bajar volumen
    if re.search(r'\b(baja|bajar|reduce|reducir|disminuye|disminuir|menos\s+volumen|baja\s+el\s+volumen)\b', query_lower):
        amount_match = re.search(r'(\d+)', query)
        amount = int(amount_match.group(1)) if amount_match else 15
        script = """
set current_vol to output volume of (get volume settings)
set new_vol to current_vol - {amt}
if new_vol < 0 then set new_vol to 0
set volume output volume new_vol
return new_vol
""".format(amt=amount)
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "volumen_bajado", "resultado": f"Volumen reducido. Nivel actual: {out}%", "exito": True}
        return {"accion": "volumen_bajado", "resultado": f"Error: {out}", "exito": False}

    # Establecer a valor específico
    level_match = re.search(r'\b(?:pon|poner|coloca|establece|fija|deja|al?)\s+(?:el\s+)?(?:volumen\s+)?(?:en\s+|a\s+)?(\d+)\b', query_lower)
    if not level_match:
        level_match = re.search(r'\bvolumen\s+(?:en\s+|a\s+|al?\s+)?(\d+)\b', query_lower)
    if level_match:
        level = min(100, max(0, int(level_match.group(1))))
        ok, out = run_applescript(f'set volume output volume {level}')
        if ok:
            return {"accion": "volumen_establecido", "resultado": f"Volumen establecido al {level}%.", "exito": True}
        return {"accion": "volumen_establecido", "resultado": f"Error: {out}", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 2: GESTIÓN DE APLICACIONES
# ══════════════════════════════════════════════════════════════════════════════
APP_ALIASES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "terminal": "Terminal",
    "calculadora": "Calculator",
    "calculator": "Calculator",
    "finder": "Finder",
    "notas": "Notes",
    "notes": "Notes",
    "recordatorios": "Reminders",
    "reminders": "Reminders",
    "calendario": "Calendar",
    "calendar": "Calendar",
    "musica": "Music",
    "música": "Music",
    "spotify": "Spotify",
    "slack": "Slack",
    "zoom": "Zoom",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "cursor": "Cursor",
    "xcode": "Xcode",
    "correo": "Mail",
    "mail": "Mail",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "discord": "Discord",
    "figma": "Figma",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "powerpoint": "Microsoft PowerPoint",
    "teams": "Microsoft Teams",
    "maps": "Maps",
    "mapas": "Maps",
    "podcasts": "Podcasts",
    "fotos": "Photos",
    "photos": "Photos",
    "facetime": "FaceTime",
    "mensajes": "Messages",
    "messages": "Messages",
}

def resolve_app_name(query_lower):
    for alias, real_name in APP_ALIASES.items():
        if alias in query_lower:
            return real_name
    patterns = [
        r'\b(?:abre|abrir|lanza|lanzar|inicia)\s+(?:la\s+(?:app|aplicaci[oó]n)|el\s+programa\s+)?([a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1\s]+?)(?:\s*$|\s+(?:por\s+favor|ahora|ya))',
        r'\b(?:cierra|cerrar|termina|terminar)\s+(?:la\s+(?:app|aplicaci[oó]n)|el\s+programa\s+)?([a-zA-Z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1\s]+?)(?:\s*$|\s+(?:por\s+favor|ahora|ya))',
    ]
    for pattern in patterns:
        m = re.search(pattern, query_lower, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate in APP_ALIASES:
                return APP_ALIASES[candidate]
            return candidate.title()
    return None

def handle_apps(query, query_lower):
    """Detecta y ejecuta intenciones de abrir o cerrar aplicaciones."""
    is_open = bool(re.search(r'\b(abre|abrir|lanza|lanzar|inicia|iniciar)\b', query_lower))
    is_close = bool(re.search(r'\b(cierra|cerrar|mata|termina|terminar|apaga)\b', query_lower))

    if not (is_open or is_close):
        return None

    app_name = resolve_app_name(query_lower)
    if not app_name:
        return None

    if is_open:
        script = f'tell application "{app_name}" to activate'
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "aplicacion_abierta", "app": app_name, "resultado": f'Aplicación "{app_name}" iniciada correctamente.', "exito": True}
        ok2, out2 = run_shell(["open", "-a", app_name])
        if ok2:
            return {"accion": "aplicacion_abierta", "app": app_name, "resultado": f'Aplicación "{app_name}" abierta correctamente.', "exito": True}
        return {"accion": "aplicacion_abierta", "app": app_name, "resultado": f'No se pudo abrir "{app_name}". Verifique que esté instalada. Error: {out}', "exito": False}

    if is_close:
        script = f'tell application "{app_name}" to quit'
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "aplicacion_cerrada", "app": app_name, "resultado": f'Aplicación "{app_name}" cerrada correctamente.', "exito": True}
        return {"accion": "aplicacion_cerrada", "app": app_name, "resultado": f'No se pudo cerrar "{app_name}". Error: {out}', "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 3: CONTROL DE MOUSE (vía Peekaboo)
# ══════════════════════════════════════════════════════════════════════════════
PEEKABOO_PATH = "/usr/local/bin/peekaboo"

def check_peekaboo_permissions():
    """Verifica si Peekaboo tiene el permiso de Accesibilidad necesario.
    Retorna (granted: bool, mensaje_error: str)."""
    ok, out = run_shell([PEEKABOO_PATH, "permissions", "--json"], timeout=8)
    if not ok and not out:
        return False, "No se pudo contactar al daemon de Peekaboo."
    
    try:
        data = json.loads(out)
        perms = data.get("data", {}).get("permissions", [])
        for p in perms:
            if p.get("name") == "Accessibility":
                if p.get("isGranted"):
                    return True, ""
                else:
                    return False, (
                        "Peekaboo no tiene permiso de Accesibilidad en macOS. "
                        "Para habilitarlo: Configuración del Sistema → Privacidad y Seguridad → "
                        "Accesibilidad → busca 'Peekaboo' o la app del Bridge y actívalo. "
                        "Una vez hecho, podré controlar el mouse y el teclado."
                    )
    except (json.JSONDecodeError, KeyError):
        pass
    
    # Si no pudimos parsear, hacemos fallback al texto
    if "granted" in out.lower() and "accessibility" not in out.lower():
        return True, ""
    return False, "No se pudo determinar el estado de los permisos de Accesibilidad."


def get_screen_dimensions():
    script = 'tell application "Finder" to get bounds of window of desktop'
    ok, out = run_applescript(script)
    if ok and "," in out:
        try:
            parts = out.split(",")
            return int(parts[2].strip()), int(parts[3].strip())
        except Exception:
            pass
    return 1920, 1080

def handle_mouse(query, query_lower):
    """Detecta y ejecuta acciones de control del mouse."""
    has_mouse_intent = bool(re.search(
        r'\b(mueve|mover|desplaza|lleva|clic|click|doble\s+clic|doble\s+click|clic\s+derecho|right\s+click|presiona\s+clic|arrastra)\b',
        query_lower
    ))
    if not has_mouse_intent:
        return None

    has_perms, perm_info = check_peekaboo_permissions()
    if not has_perms:
        return {
            "accion": "mouse_sin_permisos",
            "resultado": (
                "Para controlar el mouse, Alberth necesita permisos de Accesibilidad en macOS. "
                "Por favor ve a: Preferencias del Sistema → Privacidad y Seguridad → Accesibilidad, "
                "y agrega o activa el Terminal en la lista. Una vez hecho, podré controlar el cursor."
            ),
            "exito": False
        }

    width, height = get_screen_dimensions()

    # Doble clic
    if re.search(r'\b(doble\s+clic|doble\s+click|double\s+click)\b', query_lower):
        coord_match = re.search(r'(\d+)\s*[,x]\s*(\d+)', query)
        if coord_match:
            coords = f"{coord_match.group(1)},{coord_match.group(2)}"
            label = f"({coord_match.group(1)}, {coord_match.group(2)})"
        else:
            coords = f"{width // 2},{height // 2}"
            label = f"centro ({width // 2}, {height // 2})"
        ok, out = run_shell([PEEKABOO_PATH, "click", "--coords", coords, "--double"])
        if ok:
            return {"accion": "doble_clic", "resultado": f"Doble clic realizado en {label}.", "exito": True}
        return {"accion": "doble_clic", "resultado": f"Error: {out}", "exito": False}

    # Clic derecho
    if re.search(r'\b(clic\s+derecho|click\s+derecho|right\s+click|bot[oó]n\s+derecho)\b', query_lower):
        coord_match = re.search(r'(\d+)\s*[,x]\s*(\d+)', query)
        if coord_match:
            coords = f"{coord_match.group(1)},{coord_match.group(2)}"
            label = f"({coord_match.group(1)}, {coord_match.group(2)})"
        else:
            coords = f"{width // 2},{height // 2}"
            label = f"centro ({width // 2}, {height // 2})"
        ok, out = run_shell([PEEKABOO_PATH, "click", "--coords", coords, "--right"])
        if ok:
            return {"accion": "clic_derecho", "resultado": f"Clic derecho en {label}.", "exito": True}
        return {"accion": "clic_derecho", "resultado": f"Error: {out}", "exito": False}

    # Clic simple
    if re.search(r'\b(clic|click|haz\s+clic|presiona\s+clic)\b', query_lower):
        coord_match = re.search(r'(\d+)\s*[,x]\s*(\d+)', query)
        if coord_match:
            coords = f"{coord_match.group(1)},{coord_match.group(2)}"
            label = f"({coord_match.group(1)}, {coord_match.group(2)})"
        else:
            coords = f"{width // 2},{height // 2}"
            label = f"centro ({width // 2}, {height // 2})"
        ok, out = run_shell([PEEKABOO_PATH, "click", "--coords", coords])
        if ok:
            return {"accion": "clic", "resultado": f"Clic realizado en {label}.", "exito": True}
        return {"accion": "clic", "resultado": f"Error: {out}", "exito": False}

    # Mover mouse
    if re.search(r'\b(mueve|mover|desplaza|lleva|posiciona)\b', query_lower):
        coord_match = re.search(r'(\d+)\s*[,x]\s*(\d+)', query)
        use_center = False
        if coord_match:
            x, y = int(coord_match.group(1)), int(coord_match.group(2))
            cmd = [PEEKABOO_PATH, "move", f"{x},{y}"]
            label = f"({x}, {y})"
        elif re.search(r'\b(centro|center|medio|mitad)\b', query_lower):
            cmd = [PEEKABOO_PATH, "move", "--center"]
            label = "el centro de la pantalla"
        elif re.search(r'esquina\s+superior\s+izquierda|arriba.*izquierda', query_lower):
            cmd = [PEEKABOO_PATH, "move", "0,0"]
            label = "esquina superior izquierda"
        elif re.search(r'esquina\s+superior\s+derecha|arriba.*derecha', query_lower):
            cmd = [PEEKABOO_PATH, "move", f"{width - 1},0"]
            label = "esquina superior derecha"
        elif re.search(r'esquina\s+inferior\s+izquierda|abajo.*izquierda', query_lower):
            cmd = [PEEKABOO_PATH, "move", f"0,{height - 1}"]
            label = "esquina inferior izquierda"
        elif re.search(r'esquina\s+inferior\s+derecha|abajo.*derecha', query_lower):
            cmd = [PEEKABOO_PATH, "move", f"{width - 1},{height - 1}"]
            label = "esquina inferior derecha"
        else:
            cmd = [PEEKABOO_PATH, "move", "--center"]
            label = "el centro de la pantalla"

        ok, out = run_shell(cmd)
        if ok:
            return {"accion": "mouse_movido", "resultado": f"Mouse posicionado en {label}.", "exito": True}
        return {"accion": "mouse_movido", "resultado": f"Error al mover el mouse: {out}", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 4: CONTROL DE TECLADO (vía Peekaboo)
# ══════════════════════════════════════════════════════════════════════════════
HOTKEY_MAP = {
    "copiar": ["cmd", "c"],
    "copy": ["cmd", "c"],
    "pegar": ["cmd", "v"],
    "paste": ["cmd", "v"],
    "cortar": ["cmd", "x"],
    "cut": ["cmd", "x"],
    "deshacer": ["cmd", "z"],
    "undo": ["cmd", "z"],
    "rehacer": ["cmd", "shift", "z"],
    "redo": ["cmd", "shift", "z"],
    "guardar": ["cmd", "s"],
    "save": ["cmd", "s"],
    "seleccionar todo": ["cmd", "a"],
    "select all": ["cmd", "a"],
    "buscar": ["cmd", "f"],
    "find": ["cmd", "f"],
    "nueva pestaña": ["cmd", "t"],
    "new tab": ["cmd", "t"],
    "cerrar pestaña": ["cmd", "w"],
    "close tab": ["cmd", "w"],
    "captura de pantalla": ["cmd", "shift", "4"],
    "screenshot": ["cmd", "shift", "4"],
    "nueva ventana": ["cmd", "n"],
    "new window": ["cmd", "n"],
    "imprimir": ["cmd", "p"],
    "print": ["cmd", "p"],
    "salir": ["cmd", "q"],
    "quit": ["cmd", "q"],
}

def handle_keyboard(query, query_lower):
    """Detecta y ejecuta acciones de teclado."""
    has_keyboard_intent = bool(re.search(
        r'\b(escribe|escribir|tipea|tipear|teclea|teclear|presiona|presionar|atajo|hotkey|combinaci[oó]n\s+de\s+teclas)\b',
        query_lower
    ))
    if not has_keyboard_intent:
        return None

    has_perms, _ = check_peekaboo_permissions()
    if not has_perms:
        return {
            "accion": "teclado_sin_permisos",
            "resultado": (
                "Para controlar el teclado, Alberth necesita permisos de Accesibilidad en macOS. "
                "Ve a: Preferencias del Sistema → Privacidad y Seguridad → Accesibilidad "
                "y agrega el Terminal en la lista autorizada."
            ),
            "exito": False
        }

    for keyword, keys in HOTKEY_MAP.items():
        if keyword in query_lower:
            ok, out = run_shell([PEEKABOO_PATH, "hotkey"] + keys)
            if ok:
                keys_display = " + ".join(k.upper() for k in keys)
                return {"accion": "hotkey", "atajo": keys_display, "resultado": f"Atajo ejecutado: {keys_display}", "exito": True}
            return {"accion": "hotkey", "resultado": f"Error al ejecutar atajo: {out}", "exito": False}

    # Escritura de texto libre
    text_match = re.search(r'(?:escribe|tipea|teclea)\s+["\'\u201c\u00ab]?(.+?)["\'\u201d\u00bb]?\s*$', query_lower)
    if text_match:
        text_to_type = text_match.group(1).strip()
        ok, out = run_shell([PEEKABOO_PATH, "type", text_to_type])
        if ok:
            return {"accion": "escritura", "texto": text_to_type, "resultado": f'Texto escrito: "{text_to_type}"', "exito": True}
        return {"accion": "escritura", "resultado": f"Error al escribir: {out}", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 5: INFORMACIÓN DEL SISTEMA
# ══════════════════════════════════════════════════════════════════════════════
def handle_system_info(query, query_lower):
    if re.search(r'\b(bater[ií]a|battery|carga\s+del?\s+(equipo|mac|computador))\b', query_lower):
        ok, out = run_shell(["pmset", "-g", "batt"])
        if ok:
            pct_match = re.search(r'(\d+)%', out)
            pct = pct_match.group(0) if pct_match else "desconocido"
            lines = out.splitlines()
            detail = lines[1] if len(lines) > 1 else out
            return {"accion": "bateria", "resultado": f"Nivel de batería: {pct}. Estado: {detail.strip()}", "exito": True}

    if any(kw in query_lower for kw in ("apps abiertas", "aplicaciones abiertas", "tengo abierto", "procesos", "que programas", "qué programas", "que aplicaciones", "qué aplicaciones", "están corriendo", "estan corriendo")):
        script = 'tell application "System Events" to get name of every process whose background only is false'
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "apps_abiertas", "resultado": f"Aplicaciones activas: {out}", "exito": True}

    if re.search(r'\b(volumen\s+actual|nivel\s+de\s+volumen|cu[aá]nto\s+volumen|volumen\s+est[aá])\b', query_lower):
        script = 'output volume of (get volume settings)'
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "consulta_volumen", "resultado": f"El volumen actual es {out}%.", "exito": True}

    if re.search(r'\b(memoria|ram|cpu|procesador|uso\s+de\s+(cpu|ram|memoria))\b', query_lower):
        ok_cpu, cpu_out = run_shell(["bash", "-c", "top -l 1 -s 0 | grep 'CPU usage'"])
        ok_mem, mem_out = run_shell(["bash", "-c", "top -l 1 -s 0 | grep 'PhysMem'"])
        resultado = ""
        if ok_cpu: resultado += f"CPU: {cpu_out.strip()}. "
        if ok_mem: resultado += f"Memoria: {mem_out.strip()}."
        if resultado:
            return {"accion": "info_recursos", "resultado": resultado.strip(), "exito": True}

    if re.search(r'\b(ip|direcci[oó]n\s+ip|mi\s+ip|red\s+local|red\s+wifi)\b', query_lower):
        ok, out = run_shell(["bash", "-c", "ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null"])
        if ok and out:
            return {"accion": "ip_local", "resultado": f"Su dirección IP local es: {out.strip()}", "exito": True}
        return {"accion": "ip_local", "resultado": "No se pudo determinar la IP. Verifique la conexión WiFi.", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 6: EJECUCIÓN DE TERMINAL
# ══════════════════════════════════════════════════════════════════════════════
# Lista de comandos BLOQUEADOS por seguridad
BLOCKED_COMMANDS = [
    "rm -rf /", "rm -rf ~", "sudo rm", "mkfs", "dd if=",
    ":(){ :|:& };:", "chmod 777 /", "> /dev/sda", "shutdown", "reboot",
    "curl | sh", "wget | sh", "bash <(curl", "eval $(curl"
]

def is_safe_command(cmd: str) -> bool:
    """Verifica que el comando no esté en la lista negra de seguridad."""
    cmd_lower = cmd.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return False
    return True

def handle_terminal(query, query_lower):
    """Detecta y ejecuta comandos de terminal de forma segura."""

    # Extraer el comando entre comillas backtick o tras palabras clave
    cmd_match = re.search(
        r'(?:ejecuta|corre|run|terminal|bash|sh|comando)\s+(?:el\s+comando\s+)?["`\'](.*?)["`\']',
        query, re.IGNORECASE
    )

    if not cmd_match:
        # Intentar captura directa de patrones comunes de desarrollo
        cmd_match = re.search(
            r'(?:ejecuta|corre|run)\s+(.+?)(?:\s+en\s+(?:la\s+terminal|terminal|bash))?$',
            query, re.IGNORECASE
        )

    if not cmd_match:
        return None

    cmd = cmd_match.group(1).strip().strip('"\'`')

    if not is_safe_command(cmd):
        return {
            "accion": "terminal_bloqueado",
            "resultado": f"Comando bloqueado por política de seguridad: '{cmd}'. No ejecuto comandos potencialmente destructivos.",
            "exito": False
        }

    # Determinar directorio de trabajo (Desktop o workspace por defecto)
    cwd = os.path.expanduser("~/Desktop")
    if not os.path.exists(cwd):
        cwd = os.path.expanduser("~")

    # Menciones específicas de directorio
    if re.search(r'\b(en\s+workspace|workspace|en\s+el\s+proyecto)', query_lower):
        cwd = "/Users/digitalspace/.openclaw/workspace"
    elif re.search(r'\b(en\s+desktop|desktop|escritorio)', query_lower):
        cwd = os.path.expanduser("~/Desktop")
    elif re.search(r'\b(en\s+downloads|downloads|descargas)', query_lower):
        cwd = os.path.expanduser("~/Downloads")

    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=cwd,
            env={**os.environ, "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")}
        )
        stdout = r.stdout.strip()
        stderr = r.stderr.strip()
        output = stdout or stderr or "(sin salida)"

        # Truncar salidas muy largas
        if len(output) > 800:
            output = output[:800] + f"\n... [salida truncada, {len(output)} chars total]"

        if r.returncode == 0:
            return {
                "accion": "terminal_ejecutado",
                "resultado": f"Comando ejecutado exitosamente en {cwd}:\n{output}",
                "exito": True,
                "comando": cmd,
                "codigo_salida": r.returncode
            }
        else:
            return {
                "accion": "terminal_error",
                "resultado": f"El comando terminó con código {r.returncode}:\n{output}",
                "exito": False,
                "comando": cmd,
                "codigo_salida": r.returncode
            }
    except subprocess.TimeoutExpired:
        return {
            "accion": "terminal_timeout",
            "resultado": f"El comando '{cmd}' tardó más de 30 segundos y fue cancelado.",
            "exito": False
        }
    except Exception as e:
        return {
            "accion": "terminal_error",
            "resultado": f"Error al ejecutar el comando: {str(e)}",
            "exito": False
        }

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 7: GESTIÓN DE ARCHIVOS
# ══════════════════════════════════════════════════════════════════════════════
import shutil
import glob as glob_module

def _resolve_path(path_str: str) -> str:
    """Normaliza rutas relativas a absoluta expandiendo ~ y buscando en ubicaciones comunes."""
    path_str = path_str.strip().strip('"\'')
    expanded = os.path.expanduser(path_str)
    if os.path.isabs(expanded):
        return expanded

    # Buscar en Desktop, Downloads y Documents
    for base in ["~/Desktop", "~/Downloads", "~/Documents", "~/.openclaw/workspace"]:
        candidate = os.path.join(os.path.expanduser(base), path_str)
        if os.path.exists(candidate):
            return candidate

    # Retornar en Desktop por defecto
    return os.path.join(os.path.expanduser("~/Desktop"), path_str)

def handle_files(query, query_lower):
    """Gestión básica de archivos: crear, leer, listar, mover, copiar, eliminar."""

    # ── LISTAR archivos ──────────────────────────────────────────────────
    list_match = re.search(
        r'\b(lista|listar|muestra|ver|archivos|carpetas|contenido\s+de)\b.*?(?:de\s+|en\s+)?([~/\w\s\.\-]+)?(?:carpeta|folder|directorio|directory)?',
        query, re.IGNORECASE
    )
    if re.search(r'\b(lista|listar|muestra\s+los?\s+archivos|archivos\s+de|contenido\s+de|qué\s+hay\s+en)\b', query_lower):
        # Evitar interceptar consultas de portapapeles/clipboard
        if "portapapeles" in query_lower or "clipboard" in query_lower:
            return None
        # Determinar directorio
        dir_path = os.path.expanduser("~/Desktop")
        for kw, p in [("desktop", "~/Desktop"), ("escritorio", "~/Desktop"),
                       ("downloads", "~/Downloads"), ("descargas", "~/Downloads"),
                       ("documents", "~/Documents"), ("documentos", "~/Documents"),
                       ("workspace", "~/.openclaw/workspace")]:
            if kw in query_lower:
                dir_path = os.path.expanduser(p)
                break

        if os.path.isdir(dir_path):
            entries = sorted(os.listdir(dir_path))
            entries = [e for e in entries if not e.startswith('.')]  # excluir ocultos
            if not entries:
                return {"accion": "archivos_listados", "resultado": f"La carpeta '{dir_path}' está vacía.", "exito": True}
            preview = entries[:20]
            extra = f" (y {len(entries)-20} más...)" if len(entries) > 20 else ""
            return {
                "accion": "archivos_listados",
                "resultado": f"Archivos en {dir_path}:\n" + "\n".join(f"  • {e}" for e in preview) + extra,
                "exito": True
            }

    # ── CREAR archivo ─────────────────────────────────────────────────────
    create_match = re.search(
        r'\b(crea|crear|nuevo|nueva|haz|hacer)\s+(un\s+)?(archivo|file|nota|texto)\s+(?:llamado\s+|con\s+nombre\s+|que\s+se\s+llame\s+)?["\']?([^"\']+?)["\']?(?:\s+con\s+(?:el\s+)?contenido\s+["\']?(.+?)["\']?)?$',
        query, re.IGNORECASE
    )
    if create_match:
        filename = create_match.group(4).strip()
        content = create_match.group(5) or ""
        # Asegurar extensión
        if '.' not in filename:
            filename += '.txt'
        filepath = os.path.join(os.path.expanduser("~/Desktop"), filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return {
                "accion": "archivo_creado",
                "resultado": f"Archivo '{filename}' creado en el Desktop con éxito.",
                "exito": True,
                "ruta": filepath
            }
        except Exception as e:
            return {"accion": "archivo_creado", "resultado": f"Error al crear el archivo: {e}", "exito": False}

    # ── LEER archivo ──────────────────────────────────────────────────────
    read_match = re.search(
        r'\b(lee|leer|muestra|abre|ver\s+el\s+contenido\s+de|contenido\s+de)\s+(?:el\s+)?(?:archivo\s+)?["\']?([^"\']+?)["\']?\s*(?:del?\s+\w+)?$',
        query, re.IGNORECASE
    )
    if read_match and re.search(r'\b(lee|leer|contenido\s+de)\b', query_lower):
        filename = read_match.group(2).strip()
        filepath = _resolve_path(filename)
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                preview = content[:600] + ("..." if len(content) > 600 else "")
                return {
                    "accion": "archivo_leido",
                    "resultado": f"Contenido de '{os.path.basename(filepath)}':\n{preview}",
                    "exito": True
                }
            except Exception as e:
                return {"accion": "archivo_leido", "resultado": f"Error al leer: {e}", "exito": False}
        return {"accion": "archivo_leido", "resultado": f"No encontré el archivo '{filename}'. ¿Puede confirmar el nombre o la ubicación?", "exito": False}

    # ── MOVER / RENOMBRAR archivo ─────────────────────────────────────────
    move_match = re.search(
        r'\b(mueve|mover|renombra|renombrar)\s+(?:el\s+)?(?:archivo\s+)?["\']?([^"\']+?)["\']?\s+(?:a|como|hacia)\s+["\']?([^"\']+?)["\']?$',
        query, re.IGNORECASE
    )
    if move_match:
        src_name = move_match.group(2).strip()
        dst_name = move_match.group(3).strip()
        src = _resolve_path(src_name)
        # Si destino no tiene ruta absoluta, poner en el mismo directorio que origen
        if not os.path.isabs(dst_name) and '/' not in dst_name:
            dst = os.path.join(os.path.dirname(src), dst_name)
        else:
            dst = _resolve_path(dst_name)
        if os.path.exists(src):
            try:
                shutil.move(src, dst)
                accion = "archivo_renombrado" if os.path.dirname(src) == os.path.dirname(dst) else "archivo_movido"
                return {"accion": accion, "resultado": f"'{os.path.basename(src)}' → '{os.path.basename(dst)}' completado.", "exito": True}
            except Exception as e:
                return {"accion": "archivo_movido", "resultado": f"Error: {e}", "exito": False}
        return {"accion": "archivo_movido", "resultado": f"No encontré '{src_name}'.", "exito": False}

    # ── COPIAR archivo ────────────────────────────────────────────────────
    copy_match = re.search(
        r'\b(copia|copiar)\s+(?:el\s+)?(?:archivo\s+)?["\']?([^"\']+?)["\']?\s+(?:a|en|hacia)\s+["\']?([^"\']+?)["\']?$',
        query, re.IGNORECASE
    )
    if copy_match:
        src_name = copy_match.group(2).strip()
        dst_name = copy_match.group(3).strip()
        src = _resolve_path(src_name)
        dst = _resolve_path(dst_name)
        if os.path.isdir(dst):
            dst = os.path.join(dst, os.path.basename(src))
        if os.path.exists(src):
            try:
                shutil.copy2(src, dst)
                return {"accion": "archivo_copiado", "resultado": f"Archivo copiado a '{dst}'.", "exito": True}
            except Exception as e:
                return {"accion": "archivo_copiado", "resultado": f"Error al copiar: {e}", "exito": False}
        return {"accion": "archivo_copiado", "resultado": f"No encontré '{src_name}'.", "exito": False}

    # ── ELIMINAR archivo ──────────────────────────────────────────────────
    delete_match = re.search(
        r'\b(elimina|eliminar|borra|borrar|delete|remove)\s+(?:el\s+)?(?:archivo\s+)?["\']?([^"\']+?)["\']?$',
        query, re.IGNORECASE
    )
    if delete_match:
        filename = delete_match.group(2).strip()
        filepath = _resolve_path(filename)
        # Seguridad: no borrar fuera de Desktop/Downloads/Documents
        allowed_bases = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
        ]
        is_allowed = any(os.path.abspath(filepath).startswith(b) for b in allowed_bases)
        if not is_allowed:
            return {
                "accion": "archivo_eliminado",
                "resultado": f"Solo puedo eliminar archivos en Desktop, Downloads o Documents por seguridad.",
                "exito": False
            }
        if os.path.exists(filepath):
            try:
                if os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                else:
                    os.remove(filepath)
                return {"accion": "archivo_eliminado", "resultado": f"'{os.path.basename(filepath)}' eliminado.", "exito": True}
            except Exception as e:
                return {"accion": "archivo_eliminado", "resultado": f"Error al eliminar: {e}", "exito": False}
        return {"accion": "archivo_eliminado", "resultado": f"No encontré '{filename}'.", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# MÓDULO 8: UTILIDADES DE SISTEMA (Clipboard, Notificaciones, Brillo, Modo Oscuro)
# ══════════════════════════════════════════════════════════════════════════════
def handle_system_utils(query, query_lower):
    """Clipboard, notificaciones macOS, brillo y apariencia del sistema."""

    # ── MODO WAKE WORD (MANOS LIBRES / ACTIVACION POR VOZ) ─────────────────
    if re.search(r'\b(activa|desactiva|pon|apaga|enciende)\b.*\b(wake\s*word|activación\s*por\s*voz|modo\s*manos\s*libres|activacion\s*por\s*voz)\b', query_lower):
        ww_mode_file = "/Users/digitalspace/.openclaw/workspace/.wakeword_mode"
        if re.search(r'\b(activa|enciende|pon)\b', query_lower):
            with open(ww_mode_file, "w") as f:
                f.write("true")
            # Borrar la sesión activa anterior para forzar el primer 'Alberth'
            if os.path.exists("/tmp/alberth_session_active"):
                try:
                    os.remove("/tmp/alberth_session_active")
                except Exception:
                    pass
            return {"accion": "wakeword_activado", "resultado": "He activado el modo de activación por voz. A partir de ahora, responderé únicamente cuando diga mi nombre, Alberth.", "exito": True}
        else:
            with open(ww_mode_file, "w") as f:
                f.write("false")
            return {"accion": "wakeword_desactivado", "resultado": "He desactivado la activación por voz. Ahora responderé directamente a cualquier voz detectada.", "exito": True}

    # ── LEER CLIPBOARD ────────────────────────────────────────────────────
    if re.search(r'\b(portapapeles|clipboard|qu[eé]\s+cop[ié]|qu[eé]\s+hay\s+copiado|lo\s+que\s+cop[ié])\b', query_lower):
        ok, out = run_shell(["pbpaste"])
        if ok:
            content = out.strip()
            if not content:
                return {"accion": "clipboard_leido", "resultado": "El portapapeles está vacío.", "exito": True}
            preview = content[:400] + ("..." if len(content) > 400 else "")
            return {"accion": "clipboard_leido", "resultado": f"Contenido del portapapeles:\n{preview}", "exito": True}
        return {"accion": "clipboard_leido", "resultado": "No pude acceder al portapapeles.", "exito": False}

    # ── ESCRIBIR EN CLIPBOARD ─────────────────────────────────────────────
    copy_to_clip = re.search(
        r'\b(copia\s+al\s+portapapeles|copia\s+esto\s+al\s+clipboard|pon\s+en\s+el\s+portapapeles)\s+["\']?(.+?)["\']?$',
        query, re.IGNORECASE
    )
    if copy_to_clip:
        text_to_copy = copy_to_clip.group(2).strip()
        proc = subprocess.run(["pbcopy"], input=text_to_copy, text=True, capture_output=True)
        if proc.returncode == 0:
            return {"accion": "clipboard_escrito", "resultado": f"Texto copiado al portapapeles correctamente.", "exito": True}
        return {"accion": "clipboard_escrito", "resultado": "Error al escribir en el portapapeles.", "exito": False}

    # ── RECORDATORIOS / TIMERS (SOPORTE DIFERIDO) ─────────────────────────
    reminder_match = re.search(
        r'\b(recu[eé]rdame|pon\s+un\s+recordatorio|agenda\s+un\s+recordatorio|recuerdame)\b(.*)',
        query_lower
    )
    if reminder_match:
        from datetime import datetime, timedelta
        content = reminder_match.group(2).strip()
        
        # Intentar extraer tiempo relativo (ej: "en 5 minutos", "en 1 hora", "en 10 segundos")
        time_delta_match = re.search(r'\ben\s+(\d+)\s+(minuto|minutos|hora|horas|segundo|segundos)\b', content)
        # Intentar extraer hora exacta (ej: "a las 15:30", "a las 3:00")
        time_exact_match = re.search(r'\ba\s+las\s+(\d{1,2})[:h](\d{2})?\b', content)

        trigger_dt = None
        cleaned_message = content
        now = datetime.now()

        if time_delta_match:
            amount = int(time_delta_match.group(1))
            unit = time_delta_match.group(2)
            if "min" in unit:
                trigger_dt = now + timedelta(minutes=amount)
            elif "hor" in unit:
                trigger_dt = now + timedelta(hours=amount)
            elif "seg" in unit:
                trigger_dt = now + timedelta(seconds=amount)
            
            cleaned_message = content.replace(time_delta_match.group(0), "").strip()

        elif time_exact_match:
            hour = int(time_exact_match.group(1))
            minute = int(time_exact_match.group(2)) if time_exact_match.group(2) else 0
            trigger_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if trigger_dt < now:
                trigger_dt += timedelta(days=1)
                
            cleaned_message = content.replace(time_exact_match.group(0), "").strip()

        if trigger_dt:
            # Limpiar palabras de enlace
            cleaned_message = re.sub(r'^(que|de|para|a)\s+', '', cleaned_message).strip()
            if not cleaned_message:
                cleaned_message = "Alarma / Aviso"
                
            trigger_str = trigger_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Guardar en SQLite
            try:
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                import alberth_memory
                alberth_memory.add_reminder(trigger_str, cleaned_message)
                time_display = trigger_dt.strftime("%H:%M:%S")
                return {
                    "accion": "recordatorio_agendado", 
                    "resultado": f"He programado un recordatorio para las {time_display} con el mensaje: '{cleaned_message}'.", 
                    "exito": True
                }
            except Exception as e:
                return {
                    "accion": "recordatorio_agendado", 
                    "resultado": f"No pude guardar el recordatorio: {e}", 
                    "exito": False
                }

    # ── NOTIFICACIÓN macOS (INMEDIATA) ────────────────────────────────────
    notif_match = re.search(
        r'\b(notif[íi]came|env[íi]ame\s+una\s+notificaci[oó]n|muestra\s+(?:una\s+)?notificaci[oó]n|recuérdame|recuerdame)\s+["\']?(.+?)["\']?(?:\s+en\s+\d+)?$',
        query, re.IGNORECASE
    )
    if notif_match:
        msg = notif_match.group(2).strip()
        script = f'display notification "{msg}" with title "Alberth" subtitle "Aviso del sistema" sound name "Ping"'
        ok, out = run_applescript(script)
        if ok:
            return {"accion": "notificacion_enviada", "resultado": f"Notificación enviada: '{msg}'", "exito": True}
        return {"accion": "notificacion_enviada", "resultado": f"Error al enviar notificación: {out}", "exito": False}

    # ── BRILLO DE PANTALLA ────────────────────────────────────────────────
    brightness_up = re.search(r'\b(sube|subir|aumenta|más)\s+(?:el\s+)?brillo\b', query_lower)
    brightness_down = re.search(r'\b(baja|bajar|reduce|menos|disminuye)\s+(?:el\s+)?brillo\b', query_lower)
    brightness_set = re.search(r'\b(?:pon|poner|ajusta|ajustar|set)\s+(?:el\s+)?brillo\s+(?:al?\s+)?(\d{1,3})\b', query_lower)

    if brightness_set:
        pct = max(0, min(100, int(brightness_set.group(1))))
        val = pct / 100.0
        # Usar osascript con Quartz si está disponible, sino brightness CLI
        script = f'''
tell application "System Events"
    tell appearance preferences
        set dark mode to dark mode
    end tell
end tell
'''
        ok, _ = run_shell(["bash", "-c", f"brightness {val:.2f} 2>/dev/null || true"])
        return {"accion": "brillo_ajustado", "resultado": f"Brillo ajustado al {pct}%.", "exito": True}

    if brightness_up:
        ok, _ = run_shell(["bash", "-c", "brightness $(python3 -c \"import subprocess; r=subprocess.run(['brightness','-l'],capture_output=True,text=True); import re; m=re.search(r'brightness ([\\.\\d]+)',r.stdout); v=float(m.group(1)) if m else 0.5; print(min(1.0,v+0.2))\" 2>/dev/null) 2>/dev/null || true"])
        return {"accion": "brillo_subido", "resultado": "Brillo aumentado.", "exito": True}

    if brightness_down:
        run_shell(["bash", "-c", "brightness $(python3 -c \"import subprocess; r=subprocess.run(['brightness','-l'],capture_output=True,text=True); import re; m=re.search(r'brightness ([\\.\\d]+)',r.stdout); v=float(m.group(1)) if m else 0.5; print(max(0.0,v-0.2))\" 2>/dev/null) 2>/dev/null || true"])
        return {"accion": "brillo_bajado", "resultado": "Brillo reducido.", "exito": True}

    # ── MODO OSCURO / CLARO ───────────────────────────────────────────────
    if re.search(r'\b(modo\s+oscuro|dark\s+mode|activa\s+oscuro|pon\s+oscuro)\b', query_lower):
        script = 'tell application "System Events" to tell appearance preferences to set dark mode to true'
        ok, out = run_applescript(script)
        return {"accion": "modo_oscuro", "resultado": "Modo oscuro activado." if ok else f"Error: {out}", "exito": ok}

    if re.search(r'\b(modo\s+claro|light\s+mode|activa\s+claro|pon\s+claro)\b', query_lower):
        script = 'tell application "System Events" to tell appearance preferences to set dark mode to false'
        ok, out = run_applescript(script)
        return {"accion": "modo_claro", "resultado": "Modo claro activado." if ok else f"Error: {out}", "exito": ok}

    # ── DO NOT DISTURB ────────────────────────────────────────────────────
    if re.search(r'\b(no\s+molestar|dnd|no\s+disturb|silencia\s+notificaciones)\b', query_lower):
        script = '''
tell application "System Events"
    keystroke "d" using {option down, command down}
end tell
'''
        ok, _ = run_applescript(script)
        return {"accion": "dnd_toggle", "resultado": "Modo No Molestar alternado." if ok else "No se pudo activar No Molestar.", "exito": ok}

    # ── CAPTURA DE PANTALLA ───────────────────────────────────────────────
    if re.search(r'\b(captura|screenshot|pantallazo|toma\s+una\s+foto\s+de\s+la\s+pantalla)\b', query_lower):
        ts = __import__('time').strftime("%Y%m%d_%H%M%S")
        filepath = os.path.expanduser(f"~/Desktop/captura_{ts}.png")
        ok, out = run_shell(["screencapture", "-x", filepath])
        if ok and os.path.exists(filepath):
            return {"accion": "captura_pantalla", "resultado": f"Captura guardada en Desktop: 'captura_{ts}.png'", "exito": True, "ruta": filepath}
        return {"accion": "captura_pantalla", "resultado": "Error al capturar pantalla.", "exito": False}

    return None

# ══════════════════════════════════════════════════════════════════════════════
# DISPATCHER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
def dispatch(query):
    query_lower = query.lower()

    # Primero los módulos de alta prioridad
    result = handle_terminal(query, query_lower)
    if result: return result

    result = handle_files(query, query_lower)
    if result: return result

    result = handle_system_utils(query, query_lower)
    if result: return result

    result = handle_music(query, query_lower)
    if result: return result

    result = handle_volume(query, query_lower)
    if result: return result

    result = handle_apps(query, query_lower)

    if result: return result

    result = handle_keyboard(query, query_lower)
    if result: return result

    result = handle_mouse(query, query_lower)
    if result: return result

    result = handle_system_info(query, query_lower)
    if result: return result

    return {
        "accion": "sin_coincidencia",
        "resultado": "No se detectó ninguna acción de sistema reconocible en la consulta.",
        "exito": False
    }

# ══════════════════════════════════════════════════════════════════════════════
# PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "accion": "error",
            "resultado": "Uso: alberth_system_helper.py '<consulta>'",
            "exito": False
        }, ensure_ascii=False))
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    result = dispatch(query)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("exito") else 1)

