#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_opendesign.py — Módulo de Integración OpenDesign para Alberth NEXUS
===========================================================================
Permite a Alberth y a sus agentes autónomos consultar y aplicar:
1. El Brand Contract oficial (`DESIGN.md`) con tokens de diseño, paleta y tipografía.
2. Las reglas de artesanía visual (`craft/`) de OpenDesign (accesibilidad, animación, anti-slop).
3. La suite de habilidades de diseño (`.agents/skills/`) para generación de interfaces.
"""

from __future__ import annotations

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
DESIGN_MD_PATH = WORKSPACE_DIR / "DESIGN.md"
CRAFT_DIR = WORKSPACE_DIR / ".agents" / "craft"
SKILLS_DIR = WORKSPACE_DIR / ".agents" / "skills"

def get_design_contract() -> Dict[str, Any]:
    """Lee y analiza el archivo DESIGN.md del proyecto para extraer tokens y directrices."""
    if not DESIGN_MD_PATH.exists():
        return {"error": "DESIGN.md no encontrado en la raíz del proyecto."}

    content = DESIGN_MD_PATH.read_text(encoding="utf-8")
    
    # Extraer tokens CSS (--token: valor)
    tokens: Dict[str, str] = {}
    for match in re.finditer(r'`(--[a-zA-Z0-9\-_]+)`\s*\|\s*`?([^\|\n`]+)`?', content):
        k, v = match.group(1).strip(), match.group(2).strip()
        tokens[k] = v

    return {
        "ok": True,
        "title": "Alberth Quantum Cockpit Brand Contract",
        "tokens": tokens,
        "raw_markdown": content
    }

def list_craft_rules() -> List[Dict[str, str]]:
    """Lista las reglas de artesanía visual de OpenDesign disponibles."""
    if not CRAFT_DIR.exists():
        return []

    rules: List[Dict[str, str]] = []
    for md_file in sorted(CRAFT_DIR.glob("*.md")):
        if md_file.name in ["README.md", "FUTURE_SECTIONS.md"]:
            continue
        try:
            lines = md_file.read_text(encoding="utf-8").splitlines()
            title = lines[0].replace("#", "").strip() if lines else md_file.stem
            rules.append({
                "id": md_file.stem,
                "title": title,
                "file": md_file.name
            })
        except Exception:
            continue
    return rules

def get_craft_rule(rule_id: str) -> Optional[str]:
    """Obtiene el texto de una regla específica de OpenDesign."""
    target = CRAFT_DIR / f"{rule_id}.md"
    if target.exists():
        return target.read_text(encoding="utf-8")
    return None

def list_design_skills() -> List[str]:
    """Lista las habilidades de diseño de OpenDesign instaladas en Alberth."""
    if not SKILLS_DIR.exists():
        return []
    return [d.name for d in sorted(SKILLS_DIR.iterdir()) if d.is_dir() and (d / "SKILL.md").exists()]

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Alberth OpenDesign CLI")
    parser.add_argument("--tokens", action="store_true", help="Mostrar tokens de diseño extraídos")
    parser.add_argument("--craft", action="store_true", help="Listar reglas de artesanía de OpenDesign")
    parser.add_argument("--skills", action="store_true", help="Listar skills de diseño instalados")
    args = parser.parse_args()

    if args.tokens:
        print(json.dumps(get_design_contract().get("tokens", {}), indent=2))
    elif args.craft:
        print(json.dumps(list_craft_rules(), indent=2))
    elif args.skills:
        print("Skills de diseño activos en Alberth:")
        for s in list_design_skills():
            print(f"  • {s}")
    else:
        contract = get_design_contract()
        print(f"🎨 OpenDesign activo en Alberth. Tokens registrados: {len(contract.get('tokens', {}))}")
        print(f"📐 Reglas de artesanía: {len(list_craft_rules())} | 🛠️ Skills de diseño: {len(list_design_skills())}")
