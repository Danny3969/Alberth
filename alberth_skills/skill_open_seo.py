#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
skill_open_seo.py — Auditoría Técnica y Posicionamiento SEO (Inspirado en Open-SEO)
===================================================================================
Skill modular que evalúa y optimiza cualquier página web o archivo HTML local:
- Diagnóstico técnico de Title, Meta Description, OpenGraph y Headings.
- Detección de imágenes sin alt y scripts bloqueantes de renderizado.
- Cálculo de SEO Health Score (0-100) y checklist de remediación prioritario.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

NAME = "open_seo"
DESCRIPTION = "Auditoría técnica de SEO on-page, análisis de metaetiquetas, jerarquía semántica y cálculo de SEO Health Score."
TRIGGER_KEYWORDS = [
    "seo", "auditoria seo", "auditoría seo", "posicionamiento web", "analizar web",
    "meta description", "meta tags", "mejorar seo", "open-seo", "auditar pagina",
    "auditar página"
]


def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """Punto de entrada de la skill."""
    import alberth_open_seo as ose

    query = args.get("query", "") or args.get("mission", "")
    target = args.get("target", "")

    if not target:
        words = query.split()
        for w in words:
            clean_w = w.strip(" '\"`")
            if clean_w.startswith(("http://", "https://")) or (clean_w.endswith((".html", ".htm", ".php")) and os.path.exists(clean_w)):
                target = clean_w
                break

    if not target:
        # Si no se pasó objetivo específico, auditar el panel local de Alberth
        target = str(ose.WORKSPACE_DIR / "panel" / "index.html")

    return ose.audit_url_or_file(target)
