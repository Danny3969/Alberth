#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_devops.py — Operaciones, PM2 & Despliegue de Infraestructura (Inspirado en @devops de GODMODE)
=====================================================================================================
Especialista en:
- Monitoreo y control de procesos PM2 (status, reload, logs).
- Inspección de puertos abiertos y sockets locales.
- Automatización de despliegues y verificación de salud de servicios.
"""

from __future__ import annotations

import os
import subprocess
import socket
from pathlib import Path
from typing import Dict, Any, List

NAME = "devops"
DESCRIPTION = "Operaciones de sistemas, control de PM2, estado de puertos de red, despliegue y reinicio de microservicios."
TRIGGER_KEYWORDS = [
    "pm2 status", "reiniciar servicios", "servicios activos", "devops",
    "puertos abiertos", "revisar puertos", "desplegar servicio", "deploy",
    "estado del servidor", "ecosystem"
]


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Verifica si un puerto local está respondiendo."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def get_pm2_status() -> List[Dict[str, Any]]:
    """Consulta el estado de PM2 en formato JSON."""
    try:
        res = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            import json
            raw = json.loads(res.stdout)
            return [
                {
                    "name": p.get("name"),
                    "status": p.get("pm2_env", {}).get("status"),
                    "cpu": p.get("monit", {}).get("cpu"),
                    "memory_mb": round(p.get("monit", {}).get("memory", 0) / (1024 * 1024), 1),
                    "restarts": p.get("pm2_env", {}).get("restart_time", 0),
                }
                for p in raw
            ]
    except Exception:
        pass
    return []


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    query = args.get("query", "").lower()

    # Si se pide reiniciar o recargar PM2
    if "reload" in query or "reiniciar" in query:
        try:
            res = subprocess.run(["pm2", "reload", "ecosystem.config.js"], capture_output=True, text=True, timeout=10)
            return {
                "action": "pm2_reload",
                "success": res.returncode == 0,
                "output": res.stdout.strip() or res.stderr.strip()
            }
        except Exception as e:
            return {"error": str(e)}

    # Chequeo de puertos estándar de Alberth
    ports_to_check = {
        "8000 (Web/FastAPI)": check_port(8000),
        "8001 (Voice/STT)": check_port(8001),
        "8765 (Vision/WS)": check_port(8765),
        "4173 (GodsEye/Vite)": check_port(4173),
        "11434 (Ollama)": check_port(11434)
    }

    pm2_list = get_pm2_status()

    return {
        "pm2_services": pm2_list,
        "ports_health": ports_to_check,
        "total_active_services": len([p for p in pm2_list if p.get("status") == "online"])
    }
