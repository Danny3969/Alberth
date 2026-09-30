#!/usr/bin/env python3
"""
skill_websec.py — Escáner de Seguridad Web
Detecta tecnologías, cabeceras inseguras, vulnerabilidades y CVEs de un sitio.
"""
from __future__ import annotations
import re
from typing import Dict, Any

NAME = "websec"
DESCRIPTION = "Escanea seguridad web: headers, SSL, tecnologías, CVEs y vulnerabilidades"
TRIGGER_KEYWORDS = [
    "escanea la web", "escanea el sitio", "analiza la seguridad",
    "vulnerabilidades de", "headers de seguridad", "qué tan seguro es",
    "ssl de", "certificado de", "analiza https", "websec", "seguridad web",
    "escanear dominio", "analiza el dominio",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        url (str): URL o dominio a escanear
    """
    url = args.get("url", "").strip()
    if not url:
        return {"error": "Se requiere una 'url' o dominio.", "success": False}
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import alberth_websec_scanner as websec
        result = websec.analyze_headers(url)
        if not result:
            return {"error": f"No se pudo conectar a {url}.", "success": False}
        return {
            "success": True,
            "url": url,
            "security_score": result.get("security_score", "N/A"),
            "grade": result.get("grade", "?"),
            "headers_analysis": result.get("headers_analysis", []),
            "technologies": result.get("technologies", []),
            "summary": (
                f"Sitio {url} — Score: {result.get('security_score', '?')}/100 "
                f"(Grado {result.get('grade', '?')}). "
                f"{len(result.get('headers_analysis', []))} headers analizados."
            ),
        }
    except ImportError:
        return {"error": "Módulo alberth_websec_scanner no disponible.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
