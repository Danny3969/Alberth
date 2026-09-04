#!/usr/bin/env python3
# =============================================================================
# ALBERTH SCREEN COPILOT — Asistente de Pantalla en Tiempo Real
#
# Modos de operación:
#   1. MODO COPILOTO (--watch): Monitoreo continuo. Captura la pantalla cada N
#      segundos y la analiza con IA. Alberth "ve" lo que estás haciendo.
#
#   2. MODO SNAPSHOT (default): Captura única + análisis inmediato.
#      Equivalente al alberth_screen.py existente pero con prompts mejorados.
#
#   3. MODO COMPARATIVO (--diff): Captura dos pantallas con intervalo y
#      describe QUÉ CAMBIÓ entre ellas (útil para detectar errores nuevos).
#
# Uso:
#   python3 alberth_screen_copilot.py                        → snapshot único
#   python3 alberth_screen_copilot.py "prompt personalizado" → snapshot + prompt
#   python3 alberth_screen_copilot.py --watch 30             → copiloto cada 30s
#   python3 alberth_screen_copilot.py --diff 5               → diferencial (5s)
#   python3 alberth_screen_copilot.py --stop                 → detiene el copiloto
# =============================================================================

import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error
import time
import signal
import argparse

# ── Configuración ─────────────────────────────────────────────────────────────
WORKSPACE_DIR    = "/Users/digitalspace/.openclaw/workspace"
VOICE_DIR        = os.path.join(WORKSPACE_DIR, "voice_exchange")
SCREEN_CURRENT   = os.path.join(VOICE_DIR, "copilot_screen_current.jpg")
SCREEN_PREVIOUS  = os.path.join(VOICE_DIR, "copilot_screen_previous.jpg")
COPILOT_PID_FILE = os.path.join(WORKSPACE_DIR, ".copilot_watcher.pid")
COPILOT_LOG      = os.path.join(WORKSPACE_DIR, "logs", "copilot.log")
CONFIG_PATH      = os.path.expanduser("~/.openclaw/openclaw.json")

# Calidad de la captura JPEG (1-100). 60 = balance tamaño/calidad para IA
JPEG_QUALITY = 60

# Prompt base para el modo copiloto continuo
COPILOT_SYSTEM_PROMPT = (
    "Eres el copiloto de pantalla de Alberth. Observas la pantalla del usuario "
    "y describes brevemente en 2-3 oraciones lo más relevante: qué aplicación está activa, "
    "qué está haciendo, si hay errores visibles, o cualquier cosa que merezca atención. "
    "Sé conciso y directo. Responde siempre en español."
)

DIFF_PROMPT = (
    "Compara estas dos capturas de pantalla (ANTES y DESPUÉS). "
    "Identifica qué cambió: nuevos errores, ventanas abiertas/cerradas, cambios en código, "
    "notificaciones nuevas, o cualquier diferencia relevante. "
    "Sé específico sobre los cambios detectados. Responde en español."
)


def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[Copilot {ts}] {msg}"
    print(line, file=sys.stderr, flush=True)
    # También escribir al log file
    try:
        os.makedirs(os.path.dirname(COPILOT_LOG), exist_ok=True)
        with open(COPILOT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def get_api_key() -> str | None:
    env_key = os.environ.get("NVIDIA_API_KEY")
    if env_key:
        return env_key
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        key = (config.get("models", {})
                     .get("providers", {})
                     .get("nvidia", {})
                     .get("apiKey"))
        if key:
            return key
        return config.get("env", {}).get("NVIDIA_API_KEY")
    except Exception:
        return None


def get_vision_model() -> str:
    return "meta/llama-3.2-11b-vision-instruct"


def capture_screen(output_path: str) -> bool:
    """Captura la pantalla macOS silenciosamente."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tmp_png = output_path.replace(".jpg", "_tmp.png")

    try:
        # Captura en PNG primero (screencapture no hace JPEG nativo con buena calidad)
        result = subprocess.run(
            ["screencapture", "-x", "-t", "png", tmp_png],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8
        )

        if not os.path.exists(tmp_png) or os.path.getsize(tmp_png) == 0:
            # Intentar directamente como jpg
            result = subprocess.run(
                ["screencapture", "-x", output_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=8
            )
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0

        # Convertir PNG → JPEG comprimido con sips (nativo macOS)
        subprocess.run(
            ["sips", "-s", "format", "jpeg",
             "-s", "formatOptions", str(JPEG_QUALITY),
             tmp_png, "--out", output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10
        )
        os.remove(tmp_png)

        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

    except Exception as e:
        log(f"Error en captura: {e}")
        return False


def encode_image(path: str) -> str | None:
    """Lee y codifica imagen a base64."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log(f"Error al codificar imagen: {e}")
        return None


def analyze_image(api_key: str, image_b64: str, prompt: str,
                  image_b64_2: str | None = None) -> str | None:
    """
    Envía imagen(es) a OpenRouter para análisis.
    Si se proporciona image_b64_2, se analizan ambas (modo diff).
    """
    model = get_vision_model()
    content = [{"type": "text", "text": prompt}]

    # Imagen principal (ANTES o única)
    content.append({
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
    })

    # Imagen secundaria (DESPUÉS) para modo diff
    if image_b64_2:
        content.insert(1, {"type": "text", "text": "[IMAGEN 1 — ANTES:]"})
        content.append({"type": "text", "text": "[IMAGEN 2 — DESPUÉS:]"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64_2}"}
        })

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 600
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    req = urllib.request.Request(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"Error al analizar imagen: {e}")
        return None


def snapshot_mode(api_key: str, custom_prompt: str | None = None) -> str | None:
    """Captura única + análisis inmediato. Retorna la descripción."""
    prompt = custom_prompt or COPILOT_SYSTEM_PROMPT
    log("Capturando pantalla...")

    if not capture_screen(SCREEN_CURRENT):
        log("Error: no se pudo capturar la pantalla.")
        return None

    img_b64 = encode_image(SCREEN_CURRENT)
    if not img_b64:
        return None

    log(f"Analizando con {get_vision_model()}...")
    description = analyze_image(api_key, img_b64, prompt)

    if description:
        log(f"Análisis completo ({len(description)} chars)")
    return description


def diff_mode(api_key: str, interval_sec: int = 5) -> str | None:
    """
    Captura DOS pantallas separadas por `interval_sec` segundos
    y describe qué cambió entre ellas.
    """
    log(f"Modo DIFF: captura 1/2...")
    if not capture_screen(SCREEN_PREVIOUS):
        return None
    # Renombrar a "previous"
    import shutil
    shutil.copy2(SCREEN_CURRENT, SCREEN_PREVIOUS)

    log(f"Esperando {interval_sec}s para segunda captura...")
    time.sleep(interval_sec)

    log("Captura 2/2...")
    if not capture_screen(SCREEN_CURRENT):
        return None

    img_before = encode_image(SCREEN_PREVIOUS)
    img_after  = encode_image(SCREEN_CURRENT)

    if not img_before or not img_after:
        return None

    log("Analizando diferencias...")
    return analyze_image(api_key, img_before, DIFF_PROMPT, img_after)


def watch_mode(api_key: str, interval_sec: int = 30):
    """
    Modo daemon: captura y analiza la pantalla cada `interval_sec` segundos.
    Escribe el PID en COPILOT_PID_FILE para poder detenerlo.
    """
    # Guardar PID
    with open(COPILOT_PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    log(f"🔍 Copiloto activo — analizando pantalla cada {interval_sec}s")
    log(f"   Para detener: python3 alberth_screen_copilot.py --stop")

    def handle_stop(sig, frame):
        log("Copiloto detenido.")
        if os.path.exists(COPILOT_PID_FILE):
            os.remove(COPILOT_PID_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    while True:
        try:
            description = snapshot_mode(api_key)
            if description:
                # Escribir la descripción en un archivo que el master puede leer
                copilot_output = os.path.join(VOICE_DIR, "copilot_latest.txt")
                with open(copilot_output, "w", encoding="utf-8") as f:
                    f.write(description)
                log(f"✅ Pantalla analizada: {description[:80]}...")
            else:
                log("⚠️  No se pudo analizar la pantalla en este ciclo.")
        except Exception as e:
            log(f"Error en ciclo copiloto: {e}")

        time.sleep(interval_sec)


def stop_watch():
    """Detiene el proceso copiloto si está corriendo."""
    if not os.path.exists(COPILOT_PID_FILE):
        print("El copiloto no está activo.")
        return
    try:
        pid = int(open(COPILOT_PID_FILE).read().strip())
        os.kill(pid, signal.SIGTERM)
        os.remove(COPILOT_PID_FILE)
        print(f"Copiloto detenido (PID {pid}).")
    except ProcessLookupError:
        print("El proceso ya había terminado.")
        os.remove(COPILOT_PID_FILE)
    except Exception as e:
        print(f"Error al detener el copiloto: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Alberth Screen Copilot — análisis de pantalla con IA"
    )
    parser.add_argument("prompt", nargs="?", help="Prompt personalizado para análisis")
    parser.add_argument("--watch", type=int, metavar="SEGUNDOS", nargs="?", const=30,
                        help="Modo copiloto continuo (default: 30s)")
    parser.add_argument("--diff", type=int, metavar="SEGUNDOS", nargs="?", const=5,
                        help="Modo diferencial (default: 5s entre capturas)")
    parser.add_argument("--stop", action="store_true",
                        help="Detiene el copiloto en modo watch")
    args = parser.parse_args()

    if args.stop:
        stop_watch()
        sys.exit(0)

    api_key = get_api_key()
    if not api_key:
        print("Error: API Key no encontrada.", file=sys.stderr)
        sys.exit(1)

    if args.watch is not None:
        watch_mode(api_key, args.watch)
        # watch_mode bloquea — no llega aquí en condiciones normales

    elif args.diff is not None:
        result = diff_mode(api_key, args.diff)
        if result:
            print(result)
            sys.exit(0)
        else:
            sys.exit(1)

    else:
        # Modo snapshot (default)
        result = snapshot_mode(api_key, args.prompt)
        if result:
            print(result)
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
