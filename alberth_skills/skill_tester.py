#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_tester.py — Generador y Ejecutor de Pruebas Automatizadas (Inspirado en @testing de GODMODE)
==================================================================================================
Especialista en:
- Generación de tests unitarios y de integración (pytest / unittest / node:test).
- Ejecución aislada de suites de prueba con reporte de cobertura y fallas.
- Verificación de casos borde, mocks y aserciones rigurosas.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Any

NAME = "tester"
DESCRIPTION = "Generación y ejecución de suites de pruebas automatizadas (pytest, unittest, jest), detección de regresiones."
TRIGGER_KEYWORDS = [
    "crear tests", "generar pruebas", "ejecutar tests", "pytest", "unit test",
    "pruebas unitarias", "testing", "probar este modulo", "probar este módulo",
    "hazle tests", "cobertura de pruebas"
]


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    query = args.get("query", "") or args.get("mission", "")
    target_file = args.get("target_file", "")

    # Si se pide ejecutar tests existentes en el directorio
    if any(k in query.lower() for k in ["ejecutar tests", "corre los tests", "run tests"]):
        try:
            res = subprocess.run(
                ["pytest", "-q"],
                capture_output=True,
                text=True,
                timeout=20
            )
            return {
                "status": "executed",
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # Si se pide generar tests para un archivo o especificación
    prompt = (
        f"Requerimiento de pruebas solicitado por el Señor:\n\"{query}\"\n\n"
        "Eres el Agente Especialista en Testing & QA de Alberth.\n"
        "Diseña una suite completa de pruebas con pytest para este código o especificación.\n"
        "Incluye:\n"
        "- Pruebas de camino feliz (happy path)\n"
        "- Pruebas de casos de borde (edge cases: valores nulos, strings vacíos, tipos incorrectos)\n"
        "- Pruebas de manejo de excepciones y errores\n"
        "- Uso de fixtures de pytest y asserts informativos\n"
        "Devuelve exclusivamente el código Python listo para guardarse en un archivo test_*.py."
    )

    try:
        import alberth_foundation_models as models
        test_code, model_used = models.query_qwen_coder(prompt=prompt, max_tokens=600)
        return {
            "status": "success",
            "model_used": model_used,
            "generated_tests": test_code
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
