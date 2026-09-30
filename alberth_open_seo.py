#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_open_seo.py — Suite de Auditoría SEO y Optimización Web (Inspirado en Open-SEO)
========================================================================================
Herramienta de grado profesional para auditoría técnica on-page y posicionamiento orgánico:
  1. Metadatos & Indexación: Title, Meta Description, Robots, Canonical.
  2. Redes Sociales & Rich Snippets: OpenGraph (og:title, og:image) y Twitter Cards.
  3. Jerarquía Semántica: Validación estricta de H1 único, H2 y subencabezados.
  4. Multimedia & Performance: Detección de imágenes sin alt, scripts bloqueantes.
  5. Enlaces & Rastreabilidad: Proporción de enlaces internos/externos.
  6. Cálculo de SEO Health Score (0-100) y checklist de remediación prioritario.
"""

from __future__ import annotations

import os
import sys
import json
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional
from html.parser import HTMLParser


class SEOHTMLParser(HTMLParser):
    """Parser liviano y sin dependencias externas para auditoría profunda de HTML."""
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.metas: List[Dict[str, str]] = []
        self.h1_tags: List[str] = []
        self.h2_tags: List[str] = []
        self.h3_tags: List[str] = []
        self.current_header = ""
        self.images: List[Dict[str, Any]] = []
        self.links: List[Dict[str, str]] = []
        self.scripts: List[Dict[str, Any]] = []
        self.has_viewport = False
        self.canonical = ""

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)

        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.metas.append(attr_dict)
            if attr_dict.get("name", "").lower() == "viewport":
                self.has_viewport = True
        elif tag == "link":
            if attr_dict.get("rel", "").lower() == "canonical":
                self.canonical = attr_dict.get("href", "")
        elif tag in ("h1", "h2", "h3"):
            self.current_header = tag
        elif tag == "img":
            self.images.append({
                "src": attr_dict.get("src", ""),
                "alt": attr_dict.get("alt", None),
                "has_alt": "alt" in attr_dict and bool(attr_dict.get("alt", "").strip())
            })
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href:
                self.links.append({
                    "href": href,
                    "rel": attr_dict.get("rel", ""),
                    "is_external": href.startswith(("http://", "https://"))
                })
        elif tag == "script":
            src = attr_dict.get("src", "")
            if src:
                self.scripts.append({
                    "src": src,
                    "is_async": "async" in attr_dict,
                    "is_defer": "defer" in attr_dict
                })

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3"):
            self.current_header = ""

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif self.current_header == "h1":
            self.h1_tags.append(data.strip())
        elif self.current_header == "h2":
            self.h2_tags.append(data.strip())
        elif self.current_header == "h3":
            self.h3_tags.append(data.strip())


def audit_html_content(html_str: str, source_name: str = "documento") -> Dict[str, Any]:
    """Ejecuta una auditoría técnica completa sobre el código HTML."""
    parser = SEOHTMLParser()
    try:
        parser.feed(html_str)
    except Exception:
        pass

    issues = []
    passed = []

    # 1. Title Audit
    title = parser.title.strip()
    if not title:
        issues.append({"type": "CRITICAL", "category": "Title", "msg": "Falta la etiqueta <title> fundamental para Google."})
    elif len(title) < 30:
        issues.append({"type": "WARNING", "category": "Title", "msg": f"El <title> es muy corto ({len(title)} caracteres). Recomendado: 40-60 caracteres."})
    elif len(title) > 65:
        issues.append({"type": "WARNING", "category": "Title", "msg": f"El <title> es demasiado largo ({len(title)} caracteres) y será recortado en SERP."})
    else:
        passed.append({"category": "Title", "msg": f"Título optimizado: '{title}' ({len(title)} caracteres)."})

    # 2. Meta Description Audit
    meta_desc = ""
    og_title = ""
    og_image = ""
    for m in parser.metas:
        if m.get("name", "").lower() == "description":
            meta_desc = m.get("content", "").strip()
        elif m.get("property", "").lower() == "og:title":
            og_title = m.get("content", "").strip()
        elif m.get("property", "").lower() == "og:image":
            og_image = m.get("content", "").strip()

    if not meta_desc:
        issues.append({"type": "CRITICAL", "category": "Meta Description", "msg": "Falta la metaetiqueta <meta name='description'>."})
    elif len(meta_desc) < 70:
        issues.append({"type": "WARNING", "category": "Meta Description", "msg": f"Meta description muy corta ({len(meta_desc)} caracteres). Recomendado: 120-160."})
    elif len(meta_desc) > 165:
        issues.append({"type": "WARNING", "category": "Meta Description", "msg": f"Meta description excede 165 caracteres ({len(meta_desc)})." })
    else:
        passed.append({"category": "Meta Description", "msg": f"Meta description óptima ({len(meta_desc)} caracteres)."})

    # 3. OpenGraph Social Cards
    if not og_title or not og_image:
        issues.append({"type": "WARNING", "category": "Social / OpenGraph", "msg": "Faltan etiquetas OpenGraph (og:title u og:image) para previsualizaciones en WhatsApp/Twitter/LinkedIn."})
    else:
        passed.append({"category": "Social / OpenGraph", "msg": "Etiquetas OpenGraph configuradas correctamente."})

    # 4. Heading Hierarchy Audit
    h1s = [h for h in parser.h1_tags if h]
    if len(h1s) == 0:
        issues.append({"type": "CRITICAL", "category": "Headings", "msg": "No se encontró ninguna etiqueta <h1>. Es obligatorio para la jerarquía del buscador."})
    elif len(h1s) > 1:
        issues.append({"type": "WARNING", "category": "Headings", "msg": f"Se encontraron {len(h1s)} etiquetas <h1>. Buenas prácticas recomiendan exactamente un H1 por página."})
    else:
        passed.append({"category": "Headings", "msg": f"H1 único y bien definido: '{h1s[0][:60]}...'"})

    # 5. Image Alt Attributes
    images_without_alt = [img for img in parser.images if not img["has_alt"]]
    if images_without_alt:
        issues.append({
            "type": "WARNING",
            "category": "Images",
            "msg": f"{len(images_without_alt)} de {len(parser.images)} imágenes no tienen atributo 'alt' (impacta Google Images y accesibilidad)."
        })
    elif parser.images:
        passed.append({"category": "Images", "msg": f"Todas las imágenes ({len(parser.images)}) tienen atributos alt definidos."})

    # 6. Mobile Viewport
    if not parser.has_viewport:
        issues.append({"type": "CRITICAL", "category": "Mobile", "msg": "Falta metaetiqueta viewport. Google penaliza severamente sitios no adaptables a móviles."})
    else:
        passed.append({"category": "Mobile", "msg": "Viewport móvil configurado correctamente."})

    # 7. Render-blocking scripts
    blocking_scripts = [s for s in parser.scripts if not s["is_async"] and not s["is_defer"]]
    if blocking_scripts:
        issues.append({
            "type": "WARNING",
            "category": "Performance",
            "msg": f"{len(blocking_scripts)} script(s) externos bloquean el renderizado inicial (sin 'defer' ni 'async')."
        })

    # 8. Score Calculation
    crit_penalty = sum(25 for i in issues if i["type"] == "CRITICAL")
    warn_penalty = sum(10 for i in issues if i["type"] == "WARNING")
    score = max(0, 100 - (crit_penalty + warn_penalty))

    return {
        "source": source_name,
        "seo_health_score": score,
        "metrics": {
            "title_length": len(title),
            "meta_description_length": len(meta_desc),
            "h1_count": len(h1s),
            "h2_count": len(parser.h2_tags),
            "total_images": len(parser.images),
            "images_missing_alt": len(images_without_alt),
            "total_links": len(parser.links),
            "canonical_url": parser.canonical or "No definida"
        },
        "issues_to_fix": issues,
        "optimizations_passed": passed
    }


def audit_url_or_file(target: str) -> Dict[str, Any]:
    """Audita una URL remota o un archivo HTML local."""
    target_clean = target.strip()
    if target_clean.startswith(("http://", "https://")):
        try:
            req = urllib.request.Request(
                target_clean,
                headers={"User-Agent": "Alberth-OpenSEO-Auditor/4.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
                return audit_html_content(content, source_name=target_clean)
        except Exception as e:
            return {"error": f"No se pudo conectar a la URL '{target_clean}': {e}", "status": "failed"}

    # Es archivo local
    f_path = Path(target_clean)
    if f_path.exists() and f_path.is_file():
        try:
            content = f_path.read_text(encoding="utf-8", errors="ignore")
            return audit_html_content(content, source_name=str(f_path.name))
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    return {"error": f"El objetivo '{target_clean}' no es una URL válida ni un archivo existente.", "status": "failed"}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(WORKSPACE_DIR / "panel" / "index.html")
    print(f"🔍 Ejecutando OpenSEO Auditor en: {target}...")
    res = audit_url_or_file(target)
    print(f"\n📈 SEO Health Score: {res.get('seo_health_score')}/100")
    print("\n⚠️ Problemas Detectados:")
    for iss in res.get("issues_to_fix", []):
        print(f"  [{iss['type']}] ({iss['category']}): {iss['msg']}")
    print("\n✅ Validaciones Aprobadas:")
    for pas in res.get("optimizations_passed", []):
        print(f"  • {pas['category']}: {pas['msg']}")
