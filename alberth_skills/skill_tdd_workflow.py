#!/usr/bin/env python3
# =============================================================================
# ALBERTH SKILL: TDD Workflow (Inspirado en ECC)
# =============================================================================
# Ejecuta y orquesta el ciclo Test-Driven Development (Red -> Green -> Refactor):
# 1. Detecta el tipo de proyecto (Python pytest/unittest, Flutter test, Node npm test)
# 2. Ejecuta la suite de pruebas o una prueba individual
# 3. Reporta pruebas pasadas, fallidas y cobertura con rigor de ingeniería.
# =============================================================================

from __future__ import annotations
import os
import subprocess
from typing import Dict, Any

NAME = "tdd_workflow"
DESCRIPTION = "Orquesta el ciclo TDD (Red-Green-Refactor) ejecutando tests en Python, Flutter/Dart o Node.js."
TRIGGER_KEYWORDS = [
    "tdd", "test", "pruebas", "unit test", "pytest", "flutter test", "npm test",
    "failing test", "cobertura", "coverage"
]

def execute(target_path: str = ".", test_command: str = "") -> Dict[str, Any]:
    """
    Ejecuta el runner de pruebas detectado para el proyecto o el comando especificado.
    """
    abs_path = os.path.abspath(target_path) if os.path.exists(target_path) else os.getcwd()

    cmd = test_command.strip()
    if not cmd:
        if os.path.exists(os.path.join(abs_path, "pubspec.yaml")):
            cmd = "flutter test"
        elif os.path.exists(os.path.join(abs_path, "package.json")):
            cmd = "npm test --if-present"
        elif os.path.exists(os.path.join(abs_path, "pytest.ini")) or os.path.exists(os.path.join(abs_path, "tests")):
            cmd = "python3 -m unittest discover -s tests"
        else:
            cmd = "echo 'No se detectó un framework de pruebas estándar (pubspec.yaml, package.json o tests/)'"

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=abs_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60
        )
        passed = proc.returncode == 0
        return {
            "status": "success" if passed else "failing",
            "passed": passed,
            "exit_code": proc.returncode,
            "command": cmd,
            "target_dir": abs_path,
            "output": proc.stdout[-1500:] if len(proc.stdout) > 1500 else proc.stdout,
            "tdd_phase": "GREEN" if passed else "RED"
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "passed": False,
            "error": "La ejecución de pruebas excedió el tiempo límite de 60 segundos.",
            "command": cmd
        }
    except Exception as e:
        return {
            "status": "error",
            "passed": False,
            "error": str(e),
            "command": cmd
        }

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    res = execute(path)
    print(f"[TDD Skill] Fase: {res.get('tdd_phase')} | Exitoso: {res.get('passed')}")
    print(res.get("output", ""))
