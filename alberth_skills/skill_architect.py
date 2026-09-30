#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_architect.py — Asesor Senior de Arquitectura de Software (Inspirado en @architect de GODMODE)
==================================================================================================
Especialista en:
- Evaluación de escalabilidad y patrones de diseño (Hexagonal, Event-Driven, Microservicios vs Monolito).
- Modelado de bases de datos (SQL vs NoSQL, normalización, índices óptimos).
- Análisis de tradeoffs (latencia vs consistencia, costos en la nube vs autohospedado).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

NAME = "architect"
DESCRIPTION = "Asesoría de arquitectura de software senior, patrones de diseño, escalabilidad y tradeoffs técnicos."
TRIGGER_KEYWORDS = [
    "arquitectura de software", "como estructurar el proyecto", "cómo estructurar el proyecto",
    "diseño de base de datos", "patron de diseño", "patrón de diseño", "monolito o microservicios",
    "arquitectura del sistema", "tradeoffs de arquitectura", "architect", "hexagonal", "event-driven"
]


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    query = args.get("query", "") or args.get("mission", "")
    
    prompt = (
        f"Consulta Arquitectónica del Señor:\n\"{query}\"\n\n"
        "Eres el Agente Arquitecto Principal de Alberth. Formula una propuesta arquitectónica senior, pragmática y de nivel Google/SOTA.\n"
        "Estructura tu respuesta en:\n"
        "1. DIAGNÓSTICO & REQUISITOS CLAVE\n"
        "2. PATRÓN ARQUITECTÓNICO RECOMENDADO (justificando el porqué)\n"
        "3. MODELO DE DATOS & FLUJO DE EVENTOS\n"
        "4. TRADEOFFS & DECISIONES DIFÍCILES (qué ganamos y a qué renunciamos)\n"
        "5. PLAN DE IMPLEMENTACIÓN POR ETAPAS\n"
        "Mantén un tono ejecutivo, técnico y de alta precisión sin rodeos."
    )

    try:
        import alberth_foundation_models as models
        analysis, model_used = models.query_deepseek_reasoning(prompt=prompt, max_tokens=600)
        return {
            "status": "success",
            "model_used": model_used,
            "architecture_blueprint": analysis
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
