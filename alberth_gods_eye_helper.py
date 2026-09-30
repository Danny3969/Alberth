#!/usr/bin/env python3
# =============================================================================
# ALBERTH GOD'S EYE HELPER — Módulo de Inteligencia Geoespacial 3D
# Controla el ciclo de vida y estado de God's Eye View (Ojo de Dios) en Alberth.
# Puerto predeterminado: 4173
# =============================================================================

from __future__ import annotations
import os
import sys
import json
import time
import socket
import subprocess
from pathlib import Path

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).resolve().parent)
GODS_EYE_DIR = WORKSPACE / "gods-eye-view"
PORT = 4173
HOST = "127.0.0.1"
SERVICE_NAME = "alberth-gods-eye"

def is_port_in_use(port: int = PORT, host: str = HOST) -> bool:
    """Verifica si el puerto del Ojo de Dios está activo y respondiendo."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.6)
        return s.connect_ex((host, port)) == 0

def get_pm2_status() -> dict:
    """Consulta el estado del proceso en PM2 si está disponible."""
    try:
        res = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            apps = json.loads(res.stdout)
            for app in apps:
                if app.get("name") == SERVICE_NAME:
                    return {
                        "pm2_active": True,
                        "status": app.get("pm2_env", {}).get("status", "unknown"),
                        "uptime": app.get("pm2_env", {}).get("pm_uptime"),
                        "memory": app.get("monit", {}).get("memory", 0)
                    }
    except Exception:
        pass
    return {"pm2_active": False, "status": "stopped"}

def status() -> dict:
    """Retorna un dict con el estado completo del servicio."""
    installed = (GODS_EYE_DIR / "node_modules").exists()
    built = (GODS_EYE_DIR / "dist").exists()
    active = is_port_in_use(PORT)
    pm2_info = get_pm2_status()
    
    return {
        "installed": installed,
        "built": built,
        "active": active,
        "port": PORT,
        "url": f"http://localhost:{PORT}",
        "pm2": pm2_info
    }

def start() -> bool:
    """Inicia el servicio usando PM2 o Vite en segundo plano."""
    if is_port_in_use(PORT):
        print(f"[OK] El Ojo de Dios ya está activo en http://localhost:{PORT}")
        return True

    # Intentar con PM2 si está disponible
    try:
        res = subprocess.run(["pm2", "describe", SERVICE_NAME], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            subprocess.run(["pm2", "restart", SERVICE_NAME], check=True)
            time.sleep(2)
            if is_port_in_use(PORT):
                print(f"[OK] Iniciado exitosamente con PM2 en http://localhost:{PORT}")
                return True
    except Exception:
        pass

    # Fallback: Iniciar npx vite preview con nohup
    cmd = ["npx", "vite", "preview", "--port", str(PORT), "--host", "0.0.0.0"]
    log_file = WORKSPACE / "logs" / "gods_eye.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as out:
        subprocess.Popen(cmd, cwd=str(GODS_EYE_DIR), stdout=out, stderr=out, start_new_session=True)

    time.sleep(2)
    if is_port_in_use(PORT):
        print(f"[OK] Ojo de Dios iniciado en http://localhost:{PORT}")
        return True
    else:
        print("[AVISO] Comando enviado. Verificando disponibilidad...")
        return True

def stop() -> bool:
    """Detiene el servicio."""
    try:
        subprocess.run(["pm2", "stop", SERVICE_NAME], capture_output=True, text=True, timeout=5)
    except Exception:
        pass
    
    # Matar cualquier proceso restante en el puerto 4173
    try:
        res = subprocess.run(["lsof", "-ti", f":{PORT}"], capture_output=True, text=True)
        if res.stdout.strip():
            for pid in res.stdout.strip().split():
                subprocess.run(["kill", "-9", pid])
            print(f"[OK] Procesos en puerto {PORT} detenidos.")
            return True
    except Exception as e:
        print(f"[ERROR] Error al detener: {e}")
        return False
    return True

def open_browser():
    """Abre la interfaz en el navegador por defecto."""
    url = f"http://localhost:{PORT}"
    if not is_port_in_use(PORT):
        print("[!] El servicio no está activo. Iniciándolo primero...")
        start()
    subprocess.run(["open", url])
    print(f"[OK] Abriendo {url} en tu navegador...")

if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "status"
    if action == "status":
        print(json.dumps(status(), indent=2))
    elif action == "start":
        start()
    elif action == "stop":
        stop()
    elif action == "open":
        open_browser()
    else:
        print("Uso: python3 alberth_gods_eye_helper.py [status|start|stop|open]")
