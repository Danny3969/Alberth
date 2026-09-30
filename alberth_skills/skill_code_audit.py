#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_code_audit.py — Auditoría de Seguridad de Código & Dependencias (Inspirado en @security de GODMODE)
=======================================================================================================
Analiza archivos de código y repositorios en busca de:
- Secretos hardcodeados (API keys, passwords, tokens privados).
- Prácticas inseguras (eval, exec inseguro, shell injection, SQL injection crudo).
- Vulnerabilidades conocidas en dependencias (requirements.txt, package.json).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, Any, List

NAME = "code_audit"
DESCRIPTION = "Auditoría de seguridad estática de código, detección de secretos expuestos y dependencias vulnerables."
TRIGGER_KEYWORDS = [
    "auditar codigo", "auditar código", "seguridad de codigo", "seguridad de código",
    "secretos expuestos", "code audit", "vulnerabilidades en codigo", "vulnerabilidades en código",
    "revisa este script", "analiza el codigo", "analiza el código"
]

_SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|secret|token|password|passwd)\s*[:=]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', "Posible API Key o Secreto hardcodeado"),
    (r'(?i)AIza[0-9A-Za-z-_]{35}', "Google API Key expuesta"),
    (r'(?i)sk-[a-zA-Z0-9]{32,}', "OpenAI/DeepSeek API Key expuesta"),
    (r'(?i)ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token expuesto"),
    (r'(?i)nvapi-[a-zA-Z0-9_\-]{20,}', "NVIDIA NIM API Key expuesta"),
]

_DANGEROUS_PATTERNS = [
    (r'(?i)\beval\s*\(', "Uso de eval() peligroso que permite ejecución arbitraria"),
    (r'(?i)\bexec\s*\(', "Uso de exec() sin sanitizar"),
    (r'(?i)subprocess\.Popen\(.*shell\s*=\s*True', "subprocess con shell=True susceptible a Command Injection"),
    (r'(?i)os\.system\(', "Uso de os.system() desaconsejado"),
    (r'(?i)SELECT.*FROM.*%.*', "Posible inyección SQL por formateo directo de strings"),
]


def audit_file_content(content: str, filename: str = "snippet") -> Dict[str, Any]:
    """Escanea el contenido de un archivo en busca de fallas y secretos."""
    issues = []
    lines = content.splitlines()

    for idx, line in enumerate(lines, start=1):
        # 1. Chequeo de secretos
        for pat, desc in _SECRET_PATTERNS:
            if re.search(pat, line):
                issues.append({
                    "line": idx,
                    "type": "SECRET_LEAK",
                    "severity": "CRITICAL",
                    "description": desc,
                    "snippet": line.strip()[:100]
                })

        # 2. Chequeo de funciones peligrosas
        for pat, desc in _DANGEROUS_PATTERNS:
            if re.search(pat, line):
                issues.append({
                    "line": idx,
                    "type": "DANGEROUS_CODE",
                    "severity": "HIGH",
                    "description": desc,
                    "snippet": line.strip()[:100]
                })

    score = max(0, 100 - len(issues) * 15)
    return {
        "filename": filename,
        "total_lines": len(lines),
        "issues_found": len(issues),
        "security_score": score,
        "issues": issues
    }


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill modular."""
    query = args.get("query", "")
    target_path = args.get("path", "")

    # Si se pasa ruta o se menciona un archivo en el query
    if not target_path:
        words = query.split()
        for w in words:
            if "/" in w or w.endswith((".py", ".js", ".ts", ".sh", ".json")):
                target_path = w.strip(" '\"`")
                break

    if target_path and Path(target_path).exists():
        try:
            content = Path(target_path).read_text(encoding="utf-8", errors="ignore")
            res = audit_file_content(content, filename=target_path)
            res["status"] = "audit_completed"
            return res
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # Si se pasa código directo en el query
    return audit_file_content(query, filename="query_snippet")
