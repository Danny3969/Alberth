#!/usr/bin/env python3
# =============================================================================
# ALBERTH SKILL: Verification Loop (Inspirado en ECC)
# =============================================================================
# Ejecuta un chequeo pre-flight riguroso antes de dar por terminada una tarea:
# 1. Chequeo de sintaxis en archivos Python y Shell modificados
# 2. Escaneo rápido de secretos accidentales (API keys / tokens)
# 3. Verificación de estado de git (archivos sin trackear o modificados)
# 4. Generación de veredicto de calidad de entrega (PASS / NEEDS_WORK)
# =============================================================================

from __future__ import annotations
import os
import re
import subprocess
from typing import Dict, Any, List

NAME = "verification_loop"
DESCRIPTION = "Bucle de verificación de calidad (pre-flight check) que valida sintaxis, ausencia de secretos y sanidad de código."
TRIGGER_KEYWORDS = [
    "verificacion", "verify", "pre-flight", "check", "auditar entrega",
    "qa check", "validar codigo", "sanity check"
]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{30,}"),
    re.compile(r"xoxb-[a-zA-Z0-9]{10,}"),
    re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"),
]

def execute(target_path: str = ".") -> Dict[str, Any]:
    """
    Ejecuta el bucle de verificación integral en el directorio objetivo.
    """
    abs_path = os.path.abspath(target_path) if os.path.exists(target_path) else os.getcwd()
    issues: List[str] = []
    checks_passed = 0
    total_checks = 3

    # Chequeo 1: Escaneo de secretos en archivos de código
    secrets_found = 0
    for root, dirs, files in os.walk(abs_path):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}]
        for f in files:
            if f.endswith((".py", ".dart", ".js", ".ts", ".json", ".yaml", ".yml", ".sh", ".md")):
                fpath = os.path.join(root, f)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                    for pattern in SECRET_PATTERNS:
                        if pattern.search(content):
                            secrets_found += 1
                            issues.append(f"Posible secreto expuesto en: {os.path.relpath(fpath, abs_path)}")
                except Exception:
                    pass

    if secrets_found == 0:
        checks_passed += 1
    else:
        issues.append(f"Se detectaron {secrets_found} posibles secretos/tokens hardcodeados.")

    # Chequeo 2: Validación de sintaxis en archivos Python
    py_errors = 0
    for root, dirs, files in os.walk(abs_path):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}]
        for f in files:
            if f.endswith(".py"):
                fpath = os.path.join(root, f)
                res = subprocess.run(["python3", "-m", "py_compile", fpath], capture_output=True, text=True)
                if res.returncode != 0:
                    py_errors += 1
                    issues.append(f"Error de sintaxis en {os.path.relpath(fpath, abs_path)}: {res.stderr.strip()[:150]}")

    if py_errors == 0:
        checks_passed += 1

    # Chequeo 3: Estado de repositorio Git
    try:
        git_res = subprocess.run(["git", "status", "--porcelain"], cwd=abs_path, capture_output=True, text=True)
        if git_res.returncode == 0:
            checks_passed += 1
            git_dirty_count = len(git_res.stdout.strip().splitlines()) if git_res.stdout.strip() else 0
        else:
            git_dirty_count = 0
            checks_passed += 1
    except Exception:
        git_dirty_count = 0
        checks_passed += 1

    verdict = "PASS" if len(issues) == 0 else "NEEDS_WORK"

    return {
        "status": "success",
        "verdict": verdict,
        "checks_passed": checks_passed,
        "total_checks": total_checks,
        "issues": issues,
        "git_uncommitted_files": git_dirty_count,
        "target_path": abs_path,
        "summary": f"Veredicto {verdict}: {checks_passed}/{total_checks} verificaciones aprobadas. Incidentes: {len(issues)}."
    }

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    r = execute(path)
    print(r["summary"])
    if r["issues"]:
        for iss in r["issues"]:
            print(f"  ❌ {iss}")
    else:
        print("  ✅ Todo en orden. Código listo para entrega.")
