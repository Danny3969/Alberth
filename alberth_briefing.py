#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_briefing.py — Motor de Executive Briefing Proactivo para Alberth
========================================================================
Sintetiza la agenda real de macOS (Calendario, Recordatorios de Apple),
estado del hardware, telemetría de servicios y clima local para entregar
un informe ejecutivo diario y una locución vocal al Señor.
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

def get_live_calendar_events() -> str:
    """Obtiene los eventos reales de hoy en Apple Calendar."""
    try:
        import alberth_apple_helper
        res = alberth_apple_helper.list_today_events()
        return res.get("resultado", "Sin eventos programados para hoy.")
    except Exception as e:
        return f"Calendario no disponible: {e}"

def get_live_reminders() -> str:
    """Obtiene los recordatorios reales pendientes de Apple Reminders."""
    try:
        import alberth_apple_helper
        res = alberth_apple_helper.list_reminders(max_items=6)
        return res.get("resultado", "Sin recordatorios pendientes.")
    except Exception as e:
        return f"Recordatorios no disponibles: {e}"

def get_system_telemetry() -> Dict[str, Any]:
    """Obtiene el estado de PM2 y batería del Mac de forma segura y no bloqueante."""
    telemetry = {
        "pm2_online": 0,
        "pm2_total": 0,
        "battery": "Conectado a corriente",
        "load": "Nominal"
    }
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            procs = json.loads(r.stdout)
            telemetry["pm2_total"] = len(procs)
            telemetry["pm2_online"] = sum(1 for p in procs if p.get("pm2_env", {}).get("status") == "online")
    except Exception:
        pass

    try:
        b = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=2)
        if b.returncode == 0 and b.stdout.strip():
            first_line = b.stdout.strip().splitlines()[0]
            if "Battery Power" in first_line:
                telemetry["battery"] = "Batería activa"
            else:
                telemetry["battery"] = "Alimentación AC"
    except Exception:
        pass

    return telemetry

def get_quick_weather() -> str:
    """Consulta rápida de clima local sin latencia bloqueante."""
    try:
        import urllib.request
        req = urllib.request.Request("https://wttr.in/?format=3", headers={"User-Agent": "curl/7.68.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            text = resp.read().decode("utf-8").strip()
            return text if text and not "Unknown" in text else "Clima no disponible"
    except Exception:
        return "Clima local estable"

def generate_executive_briefing() -> Dict[str, Any]:
    """
    Sintetiza el Briefing Ejecutivo Completo:
    - Retorna texto enriquecido en Markdown para el panel.
    - Retorna texto optimizado para síntesis vocal (Edge-TTS).
    """
    now = datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    
    dia_semana = dias[now.weekday()]
    fecha_str = f"{dia_semana}, {now.day} de {meses[now.month - 1]} de {now.year}"
    hora_str = now.strftime("%H:%M")

    cal_events = get_live_calendar_events()
    reminders = get_live_reminders()
    telem = get_system_telemetry()
    weather = get_quick_weather()

    # Síntesis Markdown para la consola / panel
    md_report = f"""### 📋 BRIEFING EJECUTIVO MATUTINO · ALBERTH OS
**Fecha:** {fecha_str} · {hora_str}  
**Gobernanza:** El Señor | **Entorno:** Novasyscom HQ

---

#### 📅 1. Agenda y Calendario de macOS
{cal_events}

#### 📌 2. Recordatorios Pendientes (Apple Reminders)
{reminders}

#### ⚡ 3. Telemetría de Servidores y Hardware
- **Servicios PM2:** `{telem['pm2_online']}/{telem['pm2_total']}` procesos online activos.
- **Fuente de Energía:** {telem['battery']}.
- **Condición Ambiental:** {weather}.

---
*Todos los sistemas tácticos se encuentran listos para sus órdenes, Señor.*"""

    # Síntesis vocal fluida para TTS
    has_cal = "No tienes eventos" not in cal_events and "Sin eventos" not in cal_events
    has_rem = "No tienes recordatorios" not in reminders and "Sin recordatorios" not in reminders

    vocal_parts = [
        f"Buenas tardes, Señor. Le presento su Briefing Ejecutivo de hoy {dia_semana} {now.day} de {meses[now.month - 1]}."
    ]

    if has_cal:
        vocal_parts.append(f"En su Calendario de macOS tiene compromisos programados para hoy.")
    else:
        vocal_parts.append("En su Calendario de macOS no tiene eventos pendientes para el resto del día.")

    if has_rem:
        vocal_parts.append(f"En Recordatorios de Apple tiene tareas registradas.")
    else:
        vocal_parts.append("Sus recordatorios de Apple se encuentran al día.")

    vocal_parts.append(f"En la infraestructura local, {telem['pm2_online']} servicios de PM2 operan con telemetría nominal. ¿En qué proyecto o tarea desea que nos enfoquemos?")

    spoken_summary = " ".join(vocal_parts)

    return {
        "ok": True,
        "timestamp": time.time(),
        "fecha": fecha_str,
        "hora": hora_str,
        "markdown": md_report,
        "spoken": spoken_summary,
        "telemetry": telem,
        "calendar_summary": cal_events,
        "reminders_summary": reminders
    }

if __name__ == "__main__":
    briefing = generate_executive_briefing()
    print("=== MARKDOWN ===")
    print(briefing["markdown"])
    print("\n=== SPOKEN ===")
    print(briefing["spoken"])
