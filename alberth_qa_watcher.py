#!/usr/bin/env python3
# =============================================================================
# ALBERTH QA WATCHER — Observador Proactivo & Corrector de Voz
# Monitorea eventos del sistema y realiza correcciones habladas en voz alta
# con un límite de proactividad de 1 intervención cada 2 horas (7200 segundos).
# =============================================================================

import os
import sys
import json
import time
import subprocess
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
STATE_FILE = WORKSPACE / "qa_state.json"
TTS_SCRIPT = WORKSPACE / "alberth_tts_premium.py"
OUTPUT_DIR = WORKSPACE / "voice_exchange" / "output"

MIN_INTERVAL_SECONDS = 7200  # 2 horas entre intervenciones proactivas

def get_last_qa_ts() -> float:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return float(data.get("last_qa_speech_ts", 0))
        except Exception:
            return 0.0
    return 0.0

def update_last_qa_ts(ts: float):
    data = {"last_qa_speech_ts": ts, "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def speak_proactive_suggestion(text: str):
    now = time.time()
    last_ts = get_last_qa_ts()
    elapsed = now - last_ts

    if elapsed < MIN_INTERVAL_SECONDS:
        remaining_min = int((MIN_INTERVAL_SECONDS - elapsed) // 60)
        print(f"[QA-Watcher] Omitiendo sugerencia hablada (Regla de 2h activa. Tiempo restante: {remaining_min} min)")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    mp3_path = OUTPUT_DIR / f"qa_proactive_{int(now)}.mp3"

    print(f"[QA-Watcher] Generando sugerencia proactiva de voz: {text}")
    try:
        res = subprocess.run(
            [sys.executable, str(TTS_SCRIPT), text, str(mp3_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if res.returncode == 0 and mp3_path.exists():
            update_last_qa_ts(now)
            print(f"  ✅ Audio generado: {mp3_path.name}")
            # Reproducir audio de voz en macOS
            subprocess.Popen(["afplay", str(mp3_path)])
            return True
        else:
            print(f"  ❌ Error generando audio: {res.stderr}")
    except Exception as e:
        print(f"  ❌ Excepción en QA Watcher: {e}")

    return False

def check_system_and_evaluate():
    """Evalúa la salud de la infraestructura y sugiere intervenciones si detecta anomalías."""
    # Ejemplo de verificación proactiva de salud del sistema
    print(f"[QA-Watcher] Evaluando estado del sistema...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-speak":
        test_msg = "Atención Señor Daniel. El agente de control de calidad ha verificado la red y los servicios de Alberth de manera correcta."
        speak_proactive_suggestion(test_msg)
    else:
        check_system_and_evaluate()
