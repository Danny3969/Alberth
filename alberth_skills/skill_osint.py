#!/usr/bin/env python3
"""
skill_osint.py — OSINT & Huella Digital
Rastrea nombres de usuario, correos y presencia digital en redes sociales.
"""
from __future__ import annotations
from typing import Dict, Any

NAME = "osint"
DESCRIPTION = "Rastrea nombres de usuario, correos y huella digital en redes sociales (OSINT)"
TRIGGER_KEYWORDS = [
    "rastrea a", "huella digital", "perfil de", "busca el usuario",
    "investiga a", "quién es", "quien es", "brechas de datos",
    "busca en redes", "osint", "find username", "correo de",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        target (str): nombre de usuario, correo o nombre real a investigar
    """
    target = args.get("target", "").strip()
    if not target:
        return {"error": "Se requiere un 'target' (usuario, email o nombre).", "success": False}
    try:
        import alberth_osint as osint
        results = osint.search_username(target)
        found = [r for r in (results or []) if r.get("found")]
        return {
            "success": True,
            "target": target,
            "total_checked": len(results or []),
            "found_count": len(found),
            "profiles": found[:15],
            "summary": f"Se encontraron {len(found)} perfiles activos para '{target}' en {len(results or [])} plataformas.",
        }
    except ImportError:
        return {"error": "Módulo alberth_osint no disponible.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
