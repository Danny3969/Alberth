#!/usr/bin/env python3
"""
skill_rag.py — Búsqueda en Documentos Locales (RAG)
Indexa y recupera información de PDFs, Markdown y archivos de texto locales.
"""
from __future__ import annotations
from typing import Dict, Any

NAME = "rag"
DESCRIPTION = "Búsqueda semántica BM25 en documentos locales: PDFs, Markdown, código y notas"
TRIGGER_KEYWORDS = [
    "busca en el documento", "busca en mis archivos", "en el pdf",
    "documento local", "en mis notas", "busca en el archivo",
    "rag", "busca en el manual", "información del proyecto",
    "en el código de", "en mis documentos",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        query (str): texto a buscar en los documentos indexados
        limit (int): número máximo de resultados (default: 3)
    """
    query = args.get("query", "").strip()
    limit = int(args.get("limit", 3))
    if not query:
        return {"error": "Se requiere un 'query' para buscar.", "success": False}
    try:
        import alberth_rag_memory as rag
        result = rag.search_documents(query, limit=limit)
        resultados = result.get("resultados", []) if result else []
        return {
            "success": True,
            "query": query,
            "results_count": len(resultados),
            "results": resultados,
            "summary": f"Se encontraron {len(resultados)} fragmentos relevantes para '{query}' en los documentos indexados.",
        }
    except ImportError:
        return {"error": "Módulo alberth_rag_memory no disponible.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
