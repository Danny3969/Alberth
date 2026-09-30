#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_hindsight.py — Skill de Memoria Evolutiva (Inspirado en Vectorize.io Hindsight)
=====================================================================================
Permite a cualquier agente de Alberth:
- Retener aprendizajes y preferencias del Señor.
- Recuperar experiencias pasadas antes de ejecutar misiones.
- Ejecutar el ciclo de reflexión para destilar modelos mentales.
"""

from __future__ import annotations

import os
from typing import Dict, Any

NAME = "hindsight"
DESCRIPTION = "Memoria evolutiva continua con ciclo Retain, Recall y Reflect para aprender de experiencias y preferencias."
TRIGGER_KEYWORDS = [
    "aprende que", "recuerda que", "leccion aprendida", "lección aprendida",
    "reflexiona sobre", "que opinas de lo que paso", "qué opinas de lo que pasó",
    "hindsight", "memorias acumuladas", "experiencias previas"
]


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    import alberth_hindsight as hs

    query = args.get("query", "") or args.get("mission", "")
    action = args.get("action", "")

    # Si se pide reflexionar
    if "reflexiona" in query.lower() or action == "reflect":
        return hs.reflect(topic=query)

    # Si se pide aprender o retener
    if any(k in query.lower() for k in ["aprende", "recuerda que", "guarda que"]):
        content = query
        for k in ["aprende que", "recuerda que", "guarda que"]:
            if k in content.lower():
                content = content.lower().split(k, 1)[1].strip()
                break
        mem_id = hs.retain(content=content, memory_type="observation", context="Interacción directa con el Señor")
        return {
            "status": "retained",
            "memory_id": mem_id,
            "learned_content": content,
            "message": "He registrado esta observación en mi memoria evolutiva, Señor."
        }

    # Por defecto: Recall
    results = hs.recall(query, limit=4)
    return {
        "status": "recalled",
        "query": query,
        "matches": results,
        "stats": hs.get_stats()
    }
