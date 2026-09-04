#!/usr/bin/env python3
# =============================================================================
# ALBERTH REMINDERS DAEMON — Daemon de Recordatorios y Timers
# 
# Revisa periódicamente la base de datos de memoria SQLite en busca de
# recordatorios pendientes cuyo tiempo de disparo haya llegado o pasado.
# Genera una voz premium y notifica al usuario.
# =============================================================================

import os
import sys
import time
import subprocess
import json

WORKSPACE_DIR   = "/Users/digitalspace/.openclaw/workspace"
MEMORY_SCRIPT   = os.path.join(WORKSPACE_DIR, "alberth_memory.py")
TTS_SCRIPT      = os.path.join(WORKSPACE_DIR, "alberth_tts_premium.py")
LOG_DIR         = os.path.join(WORKSPACE_DIR, "voice_exchange", "logs")
LOCK_FILE       = "/tmp/alberth_reminders.lock"

os.makedirs(LOG_DIR, exist_ok=True)
LOGFILE = os.path.join(LOG_DIR, "alberth_reminders.log")


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")


def check_reminders():
    try:
        # 1. Obtener recordatorios pendientes listos para disparar
        proc = subprocess.run(
            ["python3", MEMORY_SCRIPT, "--pending-reminders"],
            capture_output=True, text=True, check=True
        )
        reminders = json.loads(proc.stdout.strip())
        if not reminders:
            return

        for r in reminders:
            r_id    = r["id"]
            message = r["message"]
            trigger = r["trigger_at"]
            
            log(f"⏰ Recordatorio disparado! [ID: {r_id}] '{message}'")

            # 2. Notificación macOS
            script = f'display notification "{message}" with title "Alberth - Recordatorio" sound name "Glass"'
            subprocess.run(["osascript", "-e", script])

            # 3. Generar audio
            spoken_text = f"Señor, le recuerdo que: {message}"
            temp_mp3 = f"/tmp/reminder_{r_id}.mp3"
            
            tts_ok = False
            try:
                # Usar edge-tts premium
                subprocess.run(["python3", TTS_SCRIPT, spoken_text, temp_mp3], check=True, capture_output=True)
                tts_ok = os.path.exists(temp_mp3)
            except Exception as e:
                log(f"WARN: Error en TTS Premium para recordatorio: {e}")

            # 4. Reproducir
            if tts_ok:
                subprocess.run(["afplay", temp_mp3])
                try:
                    os.remove(temp_mp3)
                except Exception:
                    pass
            else:
                # Fallback: macOS 'say'
                subprocess.run(["say", "-v", "Diego", spoken_text])

            # 5. Marcar como completado
            subprocess.run(["python3", MEMORY_SCRIPT, "--mark-reminder-done", str(r_id)], check=True)

    except Exception as e:
        log(f"ERROR: {e}")


def main():
    # Evitar múltiples instancias corriendo al mismo tiempo
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            print(f"Daemon de recordatorios ya está corriendo (PID {old_pid}). Saliendo.")
            sys.exit(0)
        except (ValueError, OSError):
            # PID huérfano o inválido
            pass
            
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    log("="*60)
    log("Alberth Reminders Daemon iniciado")
    log(f"Monitoreando base de datos a través de {MEMORY_SCRIPT}")
    log("="*60)

    try:
        while True:
            check_reminders()
            time.sleep(10)
    except KeyboardInterrupt:
        log("🛑 Daemon detenido por KeyboardInterrupt.")
    finally:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    main()
