#!/usr/bin/env python3
"""
skill_system.py — Control del Sistema macOS
Volumen, brillo, notas, recordatorios, información del sistema y control de apps.
"""
from __future__ import annotations
from typing import Dict, Any

NAME = "system"
DESCRIPTION = "Control de macOS: volumen, brillo, notas, recordatorios, apps, información del sistema"
TRIGGER_KEYWORDS = [
    "sube el volumen", "baja el volumen", "silencia", "sube el brillo",
    "baja el brillo", "modo oscuro", "reinicia el", "apaga el mac",
    "crea una nota", "nueva nota", "abre la app", "cierra la app",
    "qué apps tengo abiertas", "uso de cpu", "uso de memoria",
    "espacio en disco", "información del sistema", "muestra el escritorio",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        command (str): comando en lenguaje natural para el sistema
    """
    command = args.get("command", "").strip()
    if not command:
        return {"error": "Se requiere un 'command'.", "success": False}
    try:
        import alberth_system_helper as sys_helper
        import json as _json
        raw = sys_helper.run(command) if hasattr(sys_helper, "run") else None
        if raw:
            try:
                data = _json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                data = {"resultado": str(raw)}
            return {"success": True, "command": command, **data}
        return {"success": True, "command": command, "resultado": "Comando ejecutado."}
    except ImportError:
        # Fallback: subprocess directo para comandos AppleScript simples
        import subprocess
        result = subprocess.run(
            ["python3", "alberth_system_helper.py", command],
            capture_output=True, text=True, timeout=10
        )
        return {
            "success": result.returncode == 0,
            "command": command,
            "resultado": result.stdout.strip() or result.stderr.strip(),
        }
    except Exception as e:
        return {"error": str(e), "success": False}
