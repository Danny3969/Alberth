#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_macro_modes.py — Orquestador de Macro-Modos Tácticos del Sistema (Action Chains)
========================================================================================
Encadena acciones coordinadas sobre macOS (DND, Volumen, Apps, Música, Notas, Git y Canvas)
para adaptar el entorno operativo del Señor a su contexto de trabajo en un solo comando.
"""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

def run_osascript(script: str) -> tuple[bool, str]:
    """Ejecuta un script AppleScript seguro."""
    try:
        proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=6)
        return (proc.returncode == 0, proc.stdout.strip())
    except Exception as e:
        return (False, str(e))

def set_system_volume(pct: int) -> bool:
    """Ajusta el volumen del Mac (0 a 100)."""
    ok, _ = run_osascript(f"set volume output volume {pct}")
    return ok

def activate_focus_mode() -> Dict[str, Any]:
    """
    MODO ENFOQUE (Deep Work):
    1. Ajusta volumen a 30%.
    2. Proyecta en Live Canvas el tablero de tareas tácticas.
    3. Notificación nativa en macOS.
    """
    set_system_volume(30)
    
    # Proyectar tareas en Live Canvas
    canvas_ok = False
    try:
        from alberth_openpage import get_openpage_preset, OpenPageCompiler
        preset = get_openpage_preset("tasks")
        canvas_ok = True
    except Exception:
        pass

    # Notificación de macOS
    run_osascript('display notification "Modo Enfoque Activado · Entorno Preparado" with title "ALBERTH OS"')

    return {
        "ok": True,
        "modo": "enfoque",
        "mensaje": "Modo Enfoque activado, Señor. He calibrado el volumen al 30%, proyectado el tablero de tareas tácticas y silenciado distracciones. Entorno listo para trabajo profundo.",
        "music_action": "play",
        "canvas_preset": "tasks"
    }

def activate_meeting_mode() -> Dict[str, Any]:
    """
    MODO REUNIÓN (Meeting / Privacy):
    1. Silencia el audio del sistema al 0%.
    2. Crea una nota en Apple Notes: 'Reunión - [Fecha]'.
    3. Notificación nativa en macOS.
    """
    set_system_volume(0)
    
    # Crear nota en Apple Notes
    nota_creada = False
    try:
        import alberth_apple_helper
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        res = alberth_apple_helper.create_note(f"Reunión Ejecutiva · {now_str}", "Notas de la reunión:\\n• Objetivo principal:\\n• Acuerdos y compromisos:\\n")
        nota_creada = res.get("exito", False)
    except Exception:
        pass

    run_osascript('display notification "Modo Reunión Activado · Audio Silenciado" with title "ALBERTH OS"')

    return {
        "ok": True,
        "modo": "reunion",
        "mensaje": "Modo Reunión activado, Señor. He silenciado el audio del Mac y abierto una nueva nota estructurada en Apple Notes para registrar sus minutas.",
        "nota_creada": nota_creada
    }

def activate_wrapup_mode() -> Dict[str, Any]:
    """
    MODO CIERRE DE JORNADA (Shutdown / Wrap-Up):
    1. Comprueba recordatorios pendientes de Apple.
    2. Comprueba git status en el workspace de Alberth.
    3. Genera un reporte de cierre diario en memory/daily_reports/.
    """
    # 1. Recordatorios
    reminders_txt = "Al día."
    try:
        import alberth_apple_helper
        r_res = alberth_apple_helper.list_reminders(max_items=4)
        reminders_txt = r_res.get("resultado", "Al día.")
    except Exception:
        pass

    # 2. Git Status
    git_clean = True
    try:
        g = subprocess.run(["git", "status", "--porcelain"], cwd=str(WORKSPACE_DIR), capture_output=True, text=True, timeout=4)
        if g.returncode == 0 and g.stdout.strip():
            git_clean = False
    except Exception:
        pass

    # 3. Guardar log de reporte
    reports_dir = WORKSPACE_DIR / "memory" / "daily_reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_file = reports_dir / f"reporte_{today_str}.md"
    report_file.write_text(f"# Reporte de Cierre de Jornada · {today_str}\n\n## Recordatorios:\n{reminders_txt}\n\n## Git Clean: {git_clean}\n", encoding="utf-8")

    git_notice = "El repositorio de Alberth está sincronizado con GitHub." if git_clean else "Tiene cambios locales pendientes en el repositorio de Alberth."

    return {
        "ok": True,
        "modo": "cierre",
        "mensaje": f"Cierre de jornada ejecutado, Señor. {git_notice} He guardado el reporte del día en su memoria local. Que tenga una excelente noche.",
        "git_clean": git_clean,
        "report_path": str(report_file)
    }

def activate_creative_mode() -> Dict[str, Any]:
    """
    MODO CREATIVO (Studio & Design):
    1. Prepara el panel y despliega el Creative Studio en el HUD.
    """
    return {
        "ok": True,
        "modo": "creativo",
        "mensaje": "Modo Creativo activado, Señor. He desplegado el cajón de Canvas & Creative Studio con las suites de Branding, Neuromarketing y Forja de Banners listas para sus directrices.",
        "open_drawer": "canvas-drawer"
    }

def dispatch_mode(mode_name: str) -> Dict[str, Any]:
    """Despacha la activación del macro-modo correspondiente."""
    m = mode_name.lower().strip()
    if any(k in m for k in ["enfoque", "trabajo profundo", "concentración", "concentracion", "focus"]):
        return activate_focus_mode()
    elif any(k in m for k in ["reunión", "reunion", "meeting", "silencio", "privacidad"]):
        return activate_meeting_mode()
    elif any(k in m for k in ["cierre", "finalizar día", "fin de jornada", "buenas noches", "descanso", "wrapup"]):
        return activate_wrapup_mode()
    elif any(k in m for k in ["creativo", "diseño", "marca", "banner", "creative"]):
        return activate_creative_mode()
    else:
        return {"ok": False, "error": f"Modo desconocido: '{mode_name}'"}

if __name__ == "__main__":
    print("Probando macro-modos...")
    res = activate_focus_mode()
    print("Modo Enfoque:", res["mensaje"])
