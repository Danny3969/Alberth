#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_cloudflare_security.py — Auditoría de Seguridad de Código (Cloudflare Style)
===================================================================================
Skill modular que implementa el protocolo de 6 fases de cloudflare/security-audit-skill
con validación adversarial para eliminar falsos positivos.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

NAME = "cloudflare_security"
DESCRIPTION = "Auditoría de seguridad profunda de código en 6 fases con validación adversarial y esquema findings.json."
TRIGGER_KEYWORDS = [
    "cloudflare audit", "auditoria cloudflare", "auditoría cloudflare",
    "auditoria de seguridad profunda", "auditoría de seguridad profunda",
    "analisis de vulnerabilidades en repositorio", "analizar seguridad del proyecto",
    "findings.json", "caza de vulnerabilidades"
]


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    import alberth_cloudflare_security as cfs

    query = args.get("query", "") or args.get("mission", "")
    target = args.get("target_path", "")

    if not target:
        words = query.split()
        for w in words:
            clean_w = w.strip(" '\"`")
            if os.path.exists(clean_w):
                target = clean_w
                break

    if not target:
        # Por defecto, auditar el workspace actual de Alberth
        target = str(cfs.WORKSPACE_DIR)

    return cfs.run_cloudflare_security_audit(target)
