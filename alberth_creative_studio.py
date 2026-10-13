#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_creative_studio.py — Motor Integral de Branding, Neuromarketing, Color y Diseño Gráfico
================================================================================================
Orquesta la suite de habilidades profesionales de diseño y marketing en Alberth:
1. `brandkit` & `brand`: Creación de identidad corporativa, conceptos de logotipos vectoriales,
   arquetipos de marca y manuales de identidad.
2. `marketing-psychology`: Principios de ciencias del comportamiento y sesgos cognitivos para conversión.
3. `color-expert`: Paletas científicas, psicología del color y contrastes accesibles WCAG.
4. `ui-ux-pro-max`: Emparejamientos tipográficos profesionales (Google Fonts) y jerarquías visuales.
5. `banner-design` & `ad-creative`: Generación de piezas publicitarias multi-formato (Instagram, LinkedIn, X, Web).
6. `photo-lab`: Retoque inteligente, simulación de remoción de fondos y transformaciones.
"""

from __future__ import annotations

import os
import sys
import json
import time
import html
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
CREATIVE_EXPORTS_DIR = WORKSPACE_DIR / "panel" / "creative_exports"
CREATIVE_EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── 1. Base Científica de Psicología del Color y Paletas Curadas ─────────────
NEURO_PALETTES = [
    {
        "id": "fintech_cyber",
        "name": "Fintech & Cyber Security",
        "archetype": "Gobernante / Sabio",
        "emotion": "Solidez matemática, precisión algorítmica y blindaje financiero.",
        "colors": [
            {"hex": "#040c1a", "name": "Deep Obsidian", "role": "Fondo principal"},
            {"hex": "#00f0ff", "name": "Quantum Cyan", "role": "Acento de innovación"},
            {"hex": "#0077ff", "name": "Electric Trust", "role": "Seguridad y estabilidad"},
            {"hex": "#8ba2b8", "name": "Steel Gray", "role": "Tipografía y datos"}
        ]
    },
    {
        "id": "luxury_haute",
        "name": "Luxury & Haute Couture",
        "archetype": "Mago / Amante",
        "emotion": "Exclusividad, sofisticación, estatus de alta gama y aspiracionalidad.",
        "colors": [
            {"hex": "#0a0a0d", "name": "Carbon Jet", "role": "Fondo mate oscuro"},
            {"hex": "#e2b774", "name": "Imperial Gold", "role": "Acento de prestigio"},
            {"hex": "#ff2a5f", "name": "Velvet Rose", "role": "Toque seductor"},
            {"hex": "#f5f3ee", "name": "Pure Silk", "role": "Tipografía editorial"}
        ]
    },
    {
        "id": "health_longevity",
        "name": "BioTech & Longevity Health",
        "archetype": "Cuidador / Inocente",
        "emotion": "Regeneración celular, pureza médica, vitalidad y frescura biológica.",
        "colors": [
            {"hex": "#03140e", "name": "Forest Shadow", "role": "Fondo calmado"},
            {"hex": "#00ff88", "name": "Vital Mint", "role": "Acento de salud"},
            {"hex": "#38f9d7", "name": "Clinical Cyan", "role": "Precisión diagnóstica"},
            {"hex": "#ffffff", "name": "Sterile White", "role": "Claridad y confianza"}
        ]
    },
    {
        "id": "neuro_ecommerce",
        "name": "High-Conversion E-Commerce",
        "archetype": "Héroe / Rebelde",
        "emotion": "Impulso de compra, urgencia controlada y contraste focalizado en el CTA.",
        "colors": [
            {"hex": "#0d131f", "name": "Dark Navy", "role": "Fondo neutro de enfoque"},
            {"hex": "#ff5722", "name": "Urgency Ember", "role": "Botón de acción (CTA)"},
            {"hex": "#ffb703", "name": "Reward Amber", "role": "Ofertas y descuentos"},
            {"hex": "#f8fafc", "name": "Crisp White", "role": "Lectura de precios"}
        ]
    },
    {
        "id": "artisan_gourmet",
        "name": "Artisanal & Specialty Coffee",
        "archetype": "Creador / Explorador",
        "emotion": "Calidez sensorial, autenticidad de origen, apego artesanal y confort.",
        "colors": [
            {"hex": "#1a120c", "name": "Espresso Roast", "role": "Fondo tostado"},
            {"hex": "#d97736", "name": "Terracotta", "role": "Acento de origen"},
            {"hex": "#e8d5be", "name": "Warm Froth", "role": "Contraste de papel"},
            {"hex": "#5c6b4b", "name": "Olive Leaf", "role": "Equilibrio botánico"}
        ]
    }
]

# ─── 2. Combinaciones Tipográficas Profesionales (Font Pairings) ──────────────
FONT_PAIRINGS = [
    {
        "id": "tech_avionics",
        "name": "Quantum Tech & Avionics",
        "category": "Futurista / Cyberpunk",
        "header_font": "Orbitron",
        "body_font": "Chakra Petch",
        "google_url": "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600&family=Orbitron:wght@700;900&display=swap",
        "ideal_for": "IA, cripto, robótica, defensa y dashboards tácticos"
    },
    {
        "id": "luxury_editorial",
        "name": "Luxury Haute Editorial",
        "category": "Elegancia Clásica / Lujo",
        "header_font": "Cinzel",
        "body_font": "Inter",
        "google_url": "https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;600&display=swap",
        "ideal_for": "Moda, perfumes, joyería, arquitectura y bienes raíces premium"
    },
    {
        "id": "corporate_saas",
        "name": "Modern Corporate SaaS",
        "category": "Autoridad Limpia",
        "header_font": "Plus Jakarta Sans",
        "body_font": "Inter",
        "google_url": "https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Plus+Jakarta+Sans:wght@700;800&display=swap",
        "ideal_for": "Fintech, startups B2B, consultoría y software empresarial"
    },
    {
        "id": "brutalist_impact",
        "name": "Brutalist Bold Impact",
        "category": "Alta Energía / Disruptivo",
        "header_font": "Space Grotesk",
        "body_font": "JetBrains Mono",
        "google_url": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@700&display=swap",
        "ideal_for": "Eventos, campañas de guerrilla, cultura urbana y gaming"
    },
    {
        "id": "humanist_craft",
        "name": "Warm Humanist Artisan",
        "category": "Sensorial / Orgánico",
        "header_font": "Playfair Display",
        "body_font": "DM Sans",
        "google_url": "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500&family=Playfair+Display:ital,wght@0,700;1,600&display=swap",
        "ideal_for": "Gastronomía, café de especialidad, bienestar y cosmética natural"
    }
]

# ─── 3. Generador de Identidad de Marca y Concepto de Logo ──────────────────
def generate_brand_identity_kit(
    brand_name: str,
    industry: str,
    audience: str,
    tone: str = "innovador",
    palette_id: str = "fintech_cyber",
    font_id: str = "tech_avionics"
) -> Dict[str, Any]:
    """
    Sintetiza un Brand Identity Kit completo:
    - Arquetipo de marca y gancho de neuromarketing
    - Descripción geométrica del logotipo
    - Vector SVG interactivo generado para previsualizar el logo en vivo
    - Paleta cromática con justificación psicológica
    - Familia tipográfica asignada
    """
    clean_name = brand_name.strip() or "MARCA NOVA"
    palette = next((p for p in NEURO_PALETTES if p["id"] == palette_id), NEURO_PALETTES[0])
    font = next((f for f in FONT_PAIRINGS if f["id"] == font_id), FONT_PAIRINGS[0])

    # Generación de arquetipo e insight de neuromarketing
    archetype_map = {
        "fintech_cyber": {
            "name": "El Sabio Protector (The Sage & Ruler)",
            "neuro_trigger": "Aversión al riesgo y necesidad de control algorítmico.",
            "tagline": "PRECISIÓN IMPERMEABLE · INTELIGENCIA AUTÓNOMA",
            "logo_concept": "Monograma geométrico angular con núcleo concéntrico y corte de ángulo a 45 grados, simbolizando escudo y aceleración."
        },
        "luxury_haute": {
            "name": "El Mago Soberano (The Magician)",
            "neuro_trigger": "Deseo de distinción, exclusividad tribal y estatus social.",
            "tagline": "LA SUTILEZA DEL PRESTIGIO ATEMPORAL",
            "logo_concept": "Emblema heráldico minimalista con líneas hiper-finas y remate serif dorado, evocando distinción artesanal."
        },
        "health_longevity": {
            "name": "El Cuidador Regenerativo (The Caregiver)",
            "neuro_trigger": "Búsqueda de vitalidad biológica y alivio subconsciente de la fatiga.",
            "tagline": "CIENCIA CELULAR AL SERVICIO DE LA VIDA",
            "logo_concept": "Estructura espiral continua inspirada en el flujo de Fibonacci y la clorofila vegetal, transmitiendo evolución constante."
        },
        "neuro_ecommerce": {
            "name": "El Héroe Dinámico (The Hero)",
            "neuro_trigger": "Dopamina inmediata, gratificación instantánea y sesgo de escasez.",
            "tagline": "VELOCIDAD SUPREMA · RESULTADOS EN TIEMPO REAL",
            "logo_concept": "Flecha cinética de doble trazo en negativo con vértice hacia el cuadrante superior derecho, denotando progreso y acción."
        },
        "artisan_gourmet": {
            "name": "El Creador de Origen (The Creator)",
            "neuro_trigger": "Nostalgia sensorial, apego por lo auténtico y oxitocina comunitaria.",
            "tagline": "PASIÓN POR EL DETALLE · DESDE LA RAÍZ",
            "logo_concept": "Sello circular grabado con iconografía botánica sobria y textura orgánica de presión en relieve."
        }
    }

    arch = archetype_map.get(palette_id, archetype_map["fintech_cyber"])

    # Vector SVG del logotipo generado de forma algorítmica
    primary_col = palette["colors"][1]["hex"]
    accent_col = palette["colors"][2]["hex"]
    bg_col = palette["colors"][0]["hex"]
    text_col = palette["colors"][3]["hex"]

    initials = "".join([w[0].upper() for w in clean_name.split()[:2]]) or "N"

    logo_svg = f"""<svg viewBox="0 0 500 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:360px;height:auto;background:{bg_col};border-radius:12px;padding:20px;border:1px solid rgba(255,255,255,0.12);">
    <defs>
        <linearGradient id="brandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="{primary_col}" />
            <stop offset="100%" stop-color="{accent_col}" />
        </linearGradient>
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
    </defs>
    <!-- Isotipo Vectorial Geométrico -->
    <g transform="translate(60, 100)">
        <polygon points="0,-45 38,-22 38,22 0,45 -38,22 -38,-22" fill="none" stroke="url(#brandGrad)" stroke-width="4" filter="url(#glow)"/>
        <circle cx="0" cy="0" r="14" fill="{primary_col}" opacity="0.85"/>
        <text x="0" y="6" font-family="{font['header_font']}, sans-serif" font-size="14" font-weight="900" fill="#ffffff" text-anchor="middle">{initials}</text>
    </g>
    <!-- Logotipo Tipográfico -->
    <text x="135" y="92" font-family="{font['header_font']}, sans-serif" font-size="28" font-weight="900" letter-spacing="3" fill="#ffffff">{clean_name.upper()}</text>
    <text x="137" y="118" font-family="{font['body_font']}, sans-serif" font-size="10" font-weight="600" letter-spacing="4" fill="{primary_col}">{arch['tagline'].split('·')[0].strip()}</text>
</svg>"""

    kit_id = f"brand_{int(time.time())}"
    
    return {
        "ok": True,
        "kit_id": kit_id,
        "brand_name": clean_name,
        "industry": industry,
        "audience": audience,
        "archetype": arch["name"],
        "neuro_trigger": arch["neuro_trigger"],
        "tagline": arch["tagline"],
        "logo_concept": arch["logo_concept"],
        "logo_svg": logo_svg,
        "palette": palette,
        "font_pairing": font,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

# ─── 4. Generador de Banners Publicitarios Multi-Plataforma ───────────────────
BANNER_SPECS = {
    "instagram_post": {"w": 1080, "h": 1080, "ratio": "1:1", "name": "Instagram / LinkedIn Post"},
    "instagram_story": {"w": 1080, "h": 1920, "ratio": "9:16", "name": "Story / Reel / TikTok"},
    "linkedin_header": {"w": 1200, "h": 628, "ratio": "1.91:1", "name": "LinkedIn / FB Ad Link"},
    "web_hero": {"w": 1920, "h": 800, "ratio": "2.4:1", "name": "Cabecera Web / Hero"}
}

def generate_banner_artwork(
    headline: str,
    subtext: str,
    cta_text: str = "DESCUBRIR AHORA",
    format_id: str = "instagram_post",
    palette_id: str = "fintech_cyber",
    font_id: str = "tech_avionics"
) -> Dict[str, Any]:
    """
    Genera un banner publicitario en HTML/CSS autónomo, optimizado para conversión
    con jerarquía tipográfica, safe zones y estética de alto impacto.
    """
    spec = BANNER_SPECS.get(format_id, BANNER_SPECS["instagram_post"])
    palette = next((p for p in NEURO_PALETTES if p["id"] == palette_id), NEURO_PALETTES[0])
    font = next((f for f in FONT_PAIRINGS if f["id"] == font_id), FONT_PAIRINGS[0])

    w, h = spec["w"], spec["h"]
    is_vertical = (format_id == "instagram_story")
    is_wide = (format_id == "web_hero" or format_id == "linkedin_header")

    banner_id = f"banner_{int(time.time())}_{format_id}"
    out_file = CREATIVE_EXPORTS_DIR / f"{banner_id}.html"

    primary = palette["colors"][1]["hex"]
    accent = palette["colors"][2]["hex"]
    bg = palette["colors"][0]["hex"]
    text_col = palette["colors"][3]["hex"]

    banner_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={w}, height={h}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{font['google_url']}" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: {w}px;
            height: {h}px;
            background: {bg};
            font-family: '{font['body_font']}', sans-serif;
            color: #ffffff;
            overflow: hidden;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .banner-art {{
            position: absolute;
            inset: 0;
            background: 
                radial-gradient(circle at 80% 20%, {primary}22 0%, transparent 60%),
                radial-gradient(circle at 20% 80%, {accent}18 0%, transparent 60%),
                {bg};
        }}
        .grid-texture {{
            position: absolute;
            inset: 0;
            background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            pointer-events: none;
        }}
        .safe-zone {{
            position: relative;
            z-index: 10;
            width: 86%;
            height: 86%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .brand-pill {{
            align-self: flex-start;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.18);
            padding: 8px 18px;
            border-radius: 30px;
            font-family: '{font['header_font']}', sans-serif;
            font-size: {'16px' if is_vertical else '14px'};
            letter-spacing: 2px;
            color: {primary};
        }}
        .dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {primary};
            box-shadow: 0 0 10px {primary};
        }}
        .content-body {{
            display: flex;
            flex-direction: column;
            gap: {'28px' if is_vertical else '20px'};
            max-width: {'880px' if is_wide else '95%'};
        }}
        .headline {{
            font-family: '{font['header_font']}', sans-serif;
            font-size: {'64px' if is_vertical else '54px'};
            font-weight: 900;
            line-height: 1.1;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: #ffffff;
            text-shadow: 0 4px 30px rgba(0,0,0,0.8);
        }}
        .headline span {{
            color: {primary};
            background: linear-gradient(90deg, {primary}, {accent});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtext {{
            font-size: {'26px' if is_vertical else '22px'};
            line-height: 1.4;
            color: rgba(255,255,255,0.82);
            font-weight: 400;
        }}
        .cta-btn {{
            align-self: flex-start;
            background: linear-gradient(135deg, {primary}, {accent});
            color: #030814;
            font-family: '{font['header_font']}', sans-serif;
            font-size: {'20px' if is_vertical else '17px'};
            font-weight: 800;
            letter-spacing: 2px;
            padding: 16px 36px;
            border-radius: 8px;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 0 35px {primary}66;
            margin-top: 10px;
        }}
        .footer-tag {{
            font-size: 13px;
            color: rgba(255,255,255,0.45);
            letter-spacing: 1.5px;
            font-family: '{font['header_font']}', sans-serif;
        }}
    </style>
</head>
<body>
    <div class="banner-art"></div>
    <div class="grid-texture"></div>
    <div class="safe-zone">
        <div class="brand-pill">
            <span class="dot"></span>
            <span>ALBERTH CREATIVE // NOVASYSCOM</span>
        </div>
        <div class="content-body">
            <h1 class="headline">{html.escape(headline)}</h1>
            <p class="subtext">{html.escape(subtext)}</p>
            <a href="#" class="cta-btn">
                <span>{html.escape(cta_text)}</span>
                <span>➔</span>
            </a>
        </div>
        <div class="footer-tag">AUTONOMOUS MARKETING SUITE · VERIFIED CONVERSION SPEC</div>
    </div>
</body>
</html>"""

    out_file.write_text(banner_html, encoding="utf-8")

    return {
        "ok": True,
        "banner_id": banner_id,
        "format": format_id,
        "dimensions": f"{w}x{h}",
        "url": f"/panel/creative_exports/{out_file.name}",
        "local_path": str(out_file)
    }

if __name__ == "__main__":
    print("🎨 Probando Alberth Creative Studio...")
    brand_res = generate_brand_identity_kit("Novasyscom AI", "Tecnología de Inteligencia Artificial", "Directores y Empresarios")
    print(f"✅ Brand Kit generado: {brand_res['brand_name']} | Arquetipo: {brand_res['archetype']}")
    banner_res = generate_banner_artwork("Lanza tu Empresa al Futuro con Alberth", "La primera inteligencia autónoma con visión táctica y voz ultrarrápida.")
    print(f"✅ Banner generado: {banner_res['url']} ({banner_res['dimensions']})")
