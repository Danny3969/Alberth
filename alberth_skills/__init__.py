#!/usr/bin/env python3
# =============================================================================
# ALBERTH SKILLS — Sistema de Habilidades Modulares Auto-Descubribles
# =============================================================================
# Cómo funciona:
#   1. Al importar este módulo, escanea alberth_skills/*.py
#   2. Cada skill expone: NAME, DESCRIPTION, TRIGGER_KEYWORDS[], execute(args) -> dict
#   3. El Tálamo y el Investigador consultan REGISTRY para seleccionar la skill correcta
#
# Agregar una nueva skill = solo agregar un archivo skill_*.py aquí.
# =============================================================================

from __future__ import annotations
import os
import importlib
from typing import Dict, Any, List, Optional

# Registro global: { "nombre_skill": module }
REGISTRY: Dict[str, Any] = {}

def _discover_skills():
    """Escanea y carga todas las skills disponibles en este directorio."""
    skills_dir = os.path.dirname(__file__)
    for fname in sorted(os.listdir(skills_dir)):
        if not fname.startswith("skill_") or not fname.endswith(".py"):
            continue
        module_name = fname[:-3]  # quitar .py
        try:
            mod = importlib.import_module(f"alberth_skills.{module_name}")
            name = getattr(mod, "NAME", module_name)
            REGISTRY[name] = mod
        except Exception as e:
            print(f"[Skills] ⚠️ No se pudo cargar {fname}: {e}", flush=True)

def get_skill(name: str):
    """Retorna el módulo de una skill por nombre exacto."""
    return REGISTRY.get(name)

def find_skill_for(query: str) -> Optional[Any]:
    """
    Busca la skill más adecuada comparando el query contra TRIGGER_KEYWORDS.
    Retorna el módulo de la primera skill que haga match, o None.
    """
    q = query.lower()
    for name, mod in REGISTRY.items():
        keywords = getattr(mod, "TRIGGER_KEYWORDS", [])
        if any(k.lower() in q for k in keywords):
            return mod
    return None

def list_skills() -> List[Dict[str, str]]:
    """Lista todas las skills disponibles con nombre y descripción."""
    return [
        {
            "name": getattr(mod, "NAME", name),
            "description": getattr(mod, "DESCRIPTION", "Sin descripción"),
            "keywords": getattr(mod, "TRIGGER_KEYWORDS", []),
        }
        for name, mod in REGISTRY.items()
    ]

# Auto-descubrimiento al importar
_discover_skills()
