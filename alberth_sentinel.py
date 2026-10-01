#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# ALBERTH SENTINEL — Demonio Proactivo & Consciencia Situacional (v4.0)
# =============================================================================
# Transforma a Alberth de un asistente REACTIVO a uno PREDICTIVO:
# 1. Monitoreo pasivo no invasivo (<0.5% CPU en macOS) mediante osascript
# 2. Detección de ventana activa, proyecto en foco y modo reunión (Zoom/Teams/Meet)
# 3. Detección de proyectos con cambios pendientes sin auditar ni commitear
# 4. Emisión de Whispers Proactivos (sugerencias contextuales en el Quantum HUD)
# =============================================================================

from __future__ import annotations
import os
import sys
import time
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional, List

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).resolve().parent)
SCRATCH_DIR = WORKSPACE.parent
API_URL = "http://localhost:8080/api/sentinel"

MEETING_APPS = {"zoom.us", "microsoft teams", "facetime", "webex", "google meet", "slack"}
DEV_APPS = {"electron", "code", "cursor", "terminal", "iterm2", "antigravity", "xcode", "obsidian"}

KNOWN_PROJECTS = ["Alberth", "MacondoExpress", "GlobalMarket", "Divisas"]


def get_frontmost_app_info() -> Dict[str, str]:
    """Obtiene la aplicación y título de ventana en foco usando osascript nativo."""
    app_name = "Unknown"
    window_title = ""
    try:
        cmd_app = "tell application \"System Events\" to get name of first application process whose frontmost is true"
        r1 = subprocess.run(["osascript", "-e", cmd_app], capture_output=True, text=True, timeout=2)
        if r1.returncode == 0:
            app_name = r1.stdout.strip()
    except Exception:
        pass

    try:
        cmd_win = "tell application \"System Events\" to get title of window 1 of (first application process whose frontmost is true)"
        r2 = subprocess.run(["osascript", "-e", cmd_win], capture_output=True, text=True, timeout=2)
        if r2.returncode == 0:
            window_title = r2.stdout.strip()
    except Exception:
        pass

    return {"app": app_name, "window": window_title}


def check_running_meeting_apps() -> bool:
    """Verifica si alguna aplicación de videoconferencia está activa en macOS."""
    try:
        r = subprocess.run(["ps", "-axco", "comm"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            running_procs = {line.strip().lower() for line in r.stdout.splitlines()}
            for m in MEETING_APPS:
                if any(m in proc for proc in running_procs):
                    return True
    except Exception:
        pass
    return False


def check_uncommitted_projects() -> List[Dict[str, Any]]:
    """Inspecciona si los proyectos del Señor tienen archivos modificados sin commitear."""
    results = []
    for proj in KNOWN_PROJECTS:
        p_dir = SCRATCH_DIR / proj
        if (p_dir / ".git").exists():
            try:
                r = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(p_dir),
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if r.returncode == 0 and r.stdout.strip():
                    lines = [line.strip() for line in r.stdout.strip().splitlines() if line.strip()]
                    results.append({
                        "project": proj,
                        "path": str(p_dir),
                        "dirty_files_count": len(lines),
                        "files_preview": lines[:3]
                    })
            except Exception:
                pass
    return results


def post_to_server(endpoint: str, payload: Dict[str, Any]) -> bool:
    """Envía el estado al servidor web de Alberth para difusión WebSocket."""
    url = f"{API_URL}/{endpoint}"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_sentinel_loop():
    """Bucle principal del centinela (intervalo de 20 segundos)."""
    print("[Sentinel] 👁️ Alberth Sentinel iniciado — Vigilancia proactiva activa.")
    last_whisper_time = 0.0
    last_whisper_topic = ""
    last_meeting_state = False

    while True:
        try:
            info = get_frontmost_app_info()
            is_meeting = check_running_meeting_apps()
            dirty_projects = check_uncommitted_projects()

            state = {
                "active_app": info["app"],
                "active_window": info["window"],
                "meeting_mode": is_meeting,
                "uncommitted_projects": dirty_projects,
                "timestamp": time.time()
            }

            # Enviar actualización de telemetría situacional al servidor
            post_to_server("state", state)

            now = time.time()
            cooldown_passed = (now - last_whisper_time) > 300  # 5 minutos entre sugerencias normales

            # 1. Alerta proactiva: Cambio a modo reunión
            if is_meeting and not last_meeting_state:
                post_to_server("whisper", {
                    "title": "🛡️ Modo Búnker Activado",
                    "message": "Señor, he detectado una reunión activa. He modulado mis respuestas al modo ultra-conciso.",
                    "type": "meeting",
                    "action": "view_mode"
                })
                last_meeting_state = True
                last_whisper_time = now
            elif not is_meeting and last_meeting_state:
                last_meeting_state = False

            # 2. Sugerencia proactiva: Proyecto con cambios desatendidos
            if cooldown_passed and dirty_projects:
                proj = dirty_projects[0]
                topic_key = f"dirty_{proj['project']}"
                if topic_key != last_whisper_topic:
                    count = proj["dirty_files_count"]
                    post_to_server("whisper", {
                        "title": f"💡 Sugerencia Proactiva: {proj['project']}",
                        "message": f"Señor, detecto {count} archivo(s) con cambios en {proj['project']}. ¿Desea que ejecute una verificación de código o auditoría de seguridad?",
                        "type": "project_hint",
                        "project": proj["project"],
                        "action": "verify_project"
                    })
                    last_whisper_time = now
                    last_whisper_topic = topic_key

        except Exception as e:
            print(f"[Sentinel Error] {e}")

        time.sleep(20)


if __name__ == "__main__":
    run_sentinel_loop()
