#!/usr/bin/env python3
"""
skill_web_search.py — Búsqueda Web en Tiempo Real
DuckDuckGo + web scraping para noticias, clima y datos externos actuales.
"""
from __future__ import annotations
from typing import Dict, Any

NAME = "web_search"
DESCRIPTION = "Búsqueda web en tiempo real: noticias, clima, precios y cualquier dato externo actual"
TRIGGER_KEYWORDS = [
    "busca en internet", "busca en google", "noticias de", "clima en",
    "temperatura en", "precio de", "qué pasó con", "últimas noticias",
    "busca información sobre", "qué es", "cuánto cuesta", "cotización de",
    "busca en la web",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        query   (str): término a buscar
        results (int): número de resultados deseados (default: 5)
    """
    query   = args.get("query", "").strip()
    n       = int(args.get("results", 5))
    if not query:
        return {"error": "Se requiere un 'query'.", "success": False}
    try:
        import alberth_search_helper as sh
        raw = sh.search_duckduckgo_live(query, max_results=n)
        return {
            "success": True,
            "query": query,
            "results": raw or [],
            "count": len(raw or []),
            "summary": f"Se encontraron {len(raw or [])} resultados para '{query}' en la web.",
        }
    except ImportError:
        return {"error": "Módulo alberth_search_helper no disponible.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
