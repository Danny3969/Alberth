#!/usr/bin/env python3
# =============================================================================
# ALBERTH APPLE HELPER — Automatización Nativa de macOS (AppleScript + Shortcuts)
#
# 100% Gratuito y sin dependencias cloud externas:
#   - Recordatorios de Apple (Reminders): Listar, crear tareas
#   - Calendario de Apple (Calendar): Listar eventos de hoy, crear eventos
#   - Notas de Apple (Notes): Crear notas, buscar notas
#   - Atajos de macOS (Apple Shortcuts): Ejecutar atajos creados por el usuario
#   - Notificaciones del Sistema (macOS Notification Center)
#
# Uso: python3 alberth_apple_helper.py "<orden>"
# =============================================================================

from __future__ import annotations
import sys
import subprocess
import json
import re
from typing import Dict, Any, List


def run_osascript(script: str) -> tuple[bool, str]:
    """Ejecuta un script AppleScript y devuelve (éxito, salida)."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=8
        )
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        else:
            return False, proc.stderr.strip()
    except Exception as e:
        return False, str(e)


# ── 1. Apple Reminders (Recordatorios) ─────────────────────────────────────────
def create_reminder(title: str, notes: str = "", list_name: str = "") -> Dict[str, Any]:
    """Crea un recordatorio en la app Recordatorios de macOS."""
    clean_title = title.replace('"', '\\"')
    clean_notes = notes.replace('"', '\\"')
    
    if list_name:
        clean_list = list_name.replace('"', '\\"')
        script = f'''
        tell application "Reminders"
            if not (exists list "{clean_list}") then
                make new list with properties {{name:"{clean_list}"}}
            end if
            tell list "{clean_list}"
                make new reminder with properties {{name:"{clean_title}", body:"{clean_notes}"}}
            end tell
        end tell
        '''
    else:
        script = f'''
        tell application "Reminders"
            make new reminder with properties {{name:"{clean_title}", body:"{clean_notes}"}}
        end tell
        '''
    ok, out = run_osascript(script)
    if ok:
        return {"exito": True, "accion": "crear_recordatorio", "mensaje": f"Recordatorio '{title}' guardado exitosamente en Apple Reminders."}
    return {"exito": False, "accion": "crear_recordatorio", "mensaje": f"No se pudo crear el recordatorio: {out}"}


def list_reminders(max_items: int = 5) -> Dict[str, Any]:
    """Lista los recordatorios no completados."""
    script = f'''
    tell application "Reminders"
        set output to ""
        set remList to (reminders whose completed is false)
        set maxCount to {max_items}
        set curCount to 0
        repeat with r in remList
            set curCount to curCount + 1
            if curCount > maxCount then exit repeat
            set output to output & "• " & name of r & linefeed
        end repeat
        return output
    end tell
    '''
    ok, out = run_osascript(script)
    if ok and out:
        return {"exito": True, "accion": "listar_recordatorios", "resultado": f"Recordatorios pendientes:\n{out}"}
    return {"exito": True, "accion": "listar_recordatorios", "resultado": "No tienes recordatorios pendientes en este momento."}


# ── 2. Apple Calendar (Calendario) ─────────────────────────────────────────────
def list_today_events() -> Dict[str, Any]:
    """Lista los eventos agendados para el día de hoy en Calendario."""
    script = '''
    tell application "Calendar"
        set todayStart to current date
        set time of todayStart to 0
        set todayEnd to todayStart + (24 * 60 * 60)
        set eventList to ""
        tell calendar 1
            set curEvents to (every event whose start date ≥ todayStart and start date < todayEnd)
            repeat with ev in curEvents
                set eventList to eventList & "• " & summary of ev & " (Inicio: " & (start date of ev as string) & ")" & linefeed
            end repeat
        end tell
        return eventList
    end tell
    '''
    ok, out = run_osascript(script)
    if ok and out.strip():
        return {"exito": True, "accion": "listar_eventos", "resultado": f"Eventos de hoy en su Calendario:\n{out}"}
    return {"exito": True, "accion": "listar_eventos", "resultado": "No tienes eventos programados en tu calendario para el día de hoy."}


# ── 3. Apple Notes (Notas) ─────────────────────────────────────────────────────
def create_note(title: str, body: str = "") -> Dict[str, Any]:
    """Crea una nueva nota en la aplicación Notas de macOS."""
    clean_title = title.replace('"', '\\"')
    clean_body = body.replace('"', '\\"')
    content = f"<h1>{clean_title}</h1><br><p>{clean_body}</p>"
    script = f'''
    tell application "Notes"
        tell account "iCloud" to make new note at folder "Notes" with properties {{name:"{clean_title}", body:"{content}"}}
    end tell
    '''
    ok, out = run_osascript(script)
    if not ok:
        # Fallback a cuenta por defecto si iCloud no se llama así
        script_default = f'''
        tell application "Notes"
            make new note with properties {{name:"{clean_title}", body:"{content}"}}
        end tell
        '''
        ok, out = run_osascript(script_default)

    if ok:
        return {"exito": True, "accion": "crear_nota", "mensaje": f"Nota '{title}' creada con éxito en la aplicación Notas."}
    return {"exito": False, "accion": "crear_nota", "mensaje": f"Error al crear nota: {out}"}


# ── 4. Apple Shortcuts CLI (/usr/bin/shortcuts) ───────────────────────────────
def list_shortcuts() -> List[str]:
    """Obtiene la lista de Atajos configurados en macOS."""
    try:
        res = subprocess.run(["/usr/bin/shortcuts", "list"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            return [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
    except Exception:
        pass
    return []


def run_shortcut(name: str) -> Dict[str, Any]:
    """Ejecuta un atajo de macOS por su nombre."""
    try:
        res = subprocess.run(["/usr/bin/shortcuts", "run", name], capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return {"exito": True, "accion": "ejecutar_atajo", "mensaje": f"Atajo '{name}' ejecutado correctamente."}
        return {"exito": False, "accion": "ejecutar_atajo", "mensaje": f"Fallo al ejecutar atajo '{name}': {res.stderr.strip()}"}
    except Exception as e:
        return {"exito": False, "accion": "ejecutar_atajo", "mensaje": str(e)}


# ── 5. Notificación Visual de macOS ───────────────────────────────────────────
def show_system_notification(title: str, message: str, subtitle: str = "Alberth AI") -> bool:
    """Muestra una notificación en el Centro de Notificaciones de macOS."""
    script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "default"'
    ok, _ = run_osascript(script)
    return ok


# ── Despachador de Lenguaje Natural ────────────────────────────────────────────
def dispatch_apple_command(query: str) -> Dict[str, Any] | None:
    """Interpreta la orden del usuario y ejecuta la función nativa de Apple."""
    q = query.lower().strip()

    # 1. Recordatorios
    if any(k in q for k in ["recordatorio", "recuérdame", "recuerdame", "anota en recordatorios"]):
        if any(k in q for k in ["qué tengo pendiente", "que tengo pendiente", "lista de recordatorios", "mis recordatorios", "qué debo hacer", "que debo hacer"]):
            return list_reminders()
        # Crear recordatorio
        title = re.sub(r'^(crea un recordatorio de|crear recordatorio|recuérdame|recuerdame|anota en recordatorios)\s*', '', query, flags=re.I).strip()
        return create_reminder(title or query)

    # 2. Calendario
    if any(k in q for k in ["calendario", "agenda", "qué tengo hoy", "que tengo hoy", "mis reuniones", "mis citas"]):
        return list_today_events()

    # 3. Notas
    if any(k in q for k in ["crea una nota", "anota esto", "guardar nota", "en notas", "nueva nota"]):
        title = re.sub(r'^(crea una nota de|crear nota de|crea una nota que diga|nueva nota que diga|anota esto|en notas:?)\s*', '', query, flags=re.I).strip()
        return create_note(title[:40], title)

    # 4. Atajos (Shortcuts)
    if any(k in q for k in ["ejecuta el atajo", "corre el atajo", "atajo de", "shortcut"]):
        match = re.search(r'atajo\s+(?:de\s+)?([a-zA-Z0-9\s_-]+)', query, re.I)
        if match:
            sc_name = match.group(1).strip()
            return run_shortcut(sc_name)

    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta comando de Apple"}))
        sys.exit(1)

    cmd = " ".join(sys.argv[1:])
    res = dispatch_apple_command(cmd)
    if res:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({"exito": False, "mensaje": "Comando no reconocido por el asistente de Apple."}, ensure_ascii=False))
