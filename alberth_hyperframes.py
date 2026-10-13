#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_hyperframes.py — Motor de Generación y Renderizado de Video Hyperframes para Alberth
============================================================================================
Implementa la metodología de código abierto de HeyGen (Code-as-Video) en Alberth:
1. Convierte briefings, datos del sistema, noticias o prompts en composiciones cinemáticas
   deterministas basadas en HTML5 + CSS3 + animaciones temporizadas en GSAP.
2. Soporta formatos 16:9 (Horizontal / 1920×1080) y 9:16 (Vertical / 1080×1920).
3. Incluye plantillas especializadas: Quantum Cockpit HUD, Dark Luxury Editorial, 
   8-Bit Orbit y Cyber Radar.
4. Exporta metadatos JSON e indicadores de frames compatibles con Remotion y el CLI de Hyperframes.
"""

from __future__ import annotations

import os
import sys
import json
import time
import html
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
HYPERFRAMES_DIR = WORKSPACE_DIR / "panel" / "hyperframes"
HYPERFRAMES_DIR.mkdir(parents=True, exist_ok=True)

# ─── Catálogo de Plantillas Disponibles ───────────────────────────────────────
TEMPLATES = {
    "quantum_hud": {
        "id": "quantum_hud",
        "name": "Quantum Cockpit HUD",
        "tagline": "Estética FUI cibernética de alta gama, reactores y telemetría holográfica",
        "category": "Sci-Fi / Cyberpunk",
        "bg": "#030814",
        "primary": "#00f0ff",
        "accent": "#38f9d7",
        "font_display": "'Orbitron', 'Chakra Petch', sans-serif",
        "font_body": "'Chakra Petch', monospace",
        "google_fonts": "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Orbitron:wght@700;900&display=swap",
        "overlay": "scanlines"
    },
    "dark_editorial": {
        "id": "dark_editorial",
        "name": "Dark Luxury Editorial",
        "tagline": "Tipografía serif cinemática de alta costura, grano fílmico y minimalismo oscuro",
        "category": "Haute Couture",
        "bg": "#0a0a0d",
        "primary": "#e2b774",
        "accent": "#ff3366",
        "font_display": "'Cinzel', 'Playfair Display', serif",
        "font_body": "'Inter', sans-serif",
        "google_fonts": "https://fonts.googleapis.com/css2?family=Cinzel:wght@700;900&family=Inter:wght@300;400;600&display=swap",
        "overlay": "grain"
    },
    "retro_8bit": {
        "id": "retro_8bit",
        "name": "8-Bit Orbit Arcade",
        "tagline": "Rejilla espacial retro, estética de consola arcade de los 80s y colores neón",
        "category": "Retro Gaming",
        "bg": "#07133e",
        "primary": "#ffe75c",
        "accent": "#5ad9f8",
        "font_display": "'Press Start 2P', cursive",
        "font_body": "'Chakra Petch', monospace",
        "google_fonts": "https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600&family=Press+Start+2P&display=swap",
        "overlay": "arcade"
    },
    "cyber_radar": {
        "id": "cyber_radar",
        "name": "Declassified Cyber Radar",
        "tagline": "Terminal militar táctica, cuadrículas de radar verde fósforo y datos clasificados",
        "category": "Military Intel",
        "bg": "#031109",
        "primary": "#00ff88",
        "accent": "#ffb700",
        "font_display": "'Share Tech Mono', monospace",
        "font_body": "'JetBrains Mono', monospace",
        "google_fonts": "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Share+Tech+Mono&display=swap",
        "overlay": "radar"
    }
}

# ─── Presets Narrativos de Ejemplo ───────────────────────────────────────────
PRESETS = {
    "morning_briefing": {
        "title": "ALBERTH QUANTUM BRIEFING",
        "subtitle": "REPORTE EJECUTIVO MATUTINO // SEÑOR DANNY",
        "scenes": [
            {
                "hook": "SISTEMA OPERATIVO AL 100%",
                "sub": "Todos los subsistemas cuánticos de Alberth están sincronizados y activos.",
                "badge": "STATUS: ONLINE",
                "metrics": [{"label": "CORES ACTIVOS", "val": "8 CORES"}, {"label": "LATENCIA", "val": "12ms"}, {"label": "RAM SEGURA", "val": "6.8 GB"}]
            },
            {
                "hook": "PRIORIDADES DE HOY",
                "sub": "Revisión de proyectos activos, consolidación de arquitectura y supervisión de red.",
                "badge": "AGENDA TÁCTICA",
                "metrics": [{"label": "PROYECTOS", "val": "4 ACTIVOS"}, {"label": "AUDITORÍA", "val": "EN CURSO"}, {"label": "OBJETIVO", "val": "100% LISTO"}]
            },
            {
                "hook": "INTELIGENCIA Y RADAR",
                "sub": "Sentinel y QA Watcher mantienen el perímetro protegido sin anomalías detectadas.",
                "badge": "DEFENSA ACTIVA",
                "metrics": [{"label": "ALERTAS", "val": "0 CRÍTICAS"}, {"label": "SECSCAN", "val": "VERIFICADO"}, {"label": "TÚNEL", "val": "ENCRIPTADO"}]
            },
            {
                "hook": "A SU DISPOSICIÓN, SEÑOR",
                "sub": "Alberth permanece en guardia esperando sus instrucciones de voz o consola.",
                "badge": "NOVASYSCOM AI",
                "metrics": [{"label": "COMANDO", "val": "ACTIVO"}, {"label": "VOZ", "val": "LISTA"}]
            }
        ]
    },
    "security_radar": {
        "title": "RADAR DE CIBERSEGURIDAD // OSINT",
        "subtitle": "INFORME DE VULNERABILIDADES Y PERÍMETRO",
        "scenes": [
            {
                "hook": "PERÍMETRO DIGITAL MONITOREADO",
                "sub": "Escaneo continuo de activos de red, certificados SSL y telemetría de túneles.",
                "badge": "DEFENSA CLOUD",
                "metrics": [{"label": "PUERTOS SEGUROS", "val": "OK"}, {"label": "FIREWALL", "val": "ACTIVO"}, {"label": "ENCRIPTACIÓN", "val": "AES-256"}]
            },
            {
                "hook": "OSINT DIGITAL FOOTPRINT",
                "sub": "Vigilancia de exposición de credenciales y reputación de infraestructura.",
                "badge": "RADAR GLOBAL",
                "metrics": [{"label": "HUELLA", "val": "BAJO RIESGO"}, {"label": "FILTRACIONES", "val": "0 DETECTADAS"}]
            },
            {
                "hook": "PROTOCOLO BÚNKER DISPONIBLE",
                "sub": "En caso de intrusión, aislamiento hermético de servicios en 1 segundo.",
                "badge": "CONTENCIÓN",
                "metrics": [{"label": "TIEMPO REACCIÓN", "val": "< 1s"}, {"label": "RESPALDO", "val": "ENCRIPTO"}]
            }
        ]
    },
    "tech_showcase": {
        "title": "ECOSISTEMA ALBERTH V4",
        "subtitle": "ARQUITECTURA DE IA MULTI-AGENTE Y VISIÓN",
        "scenes": [
            {
                "hook": "LA NUEVA ERA DE ASISTENCIA TÁCTICA",
                "sub": "Orquestación multi-modelo impulsada por Gemini 2.5 Pro, Flash y agentes locales.",
                "badge": "REVOLUCIÓN IA",
                "metrics": [{"label": "MOTOR", "val": "GEMINI 2.5"}, {"label": "INTERFAZ", "val": "3D HUD"}, {"label": "MODOS", "val": "4 TONOS"}]
            },
            {
                "hook": "OJO DE DIOS & MULTI-AGENTE",
                "sub": "Inteligencia geoespacial satelital con debate adversarial entre agentes autónomos.",
                "badge": "CAPACIDAD SUPREMA",
                "metrics": [{"label": "SATÉLITES", "val": "EN VIVO"}, {"label": "DEBATES", "val": "TIEMPO REAL"}]
            },
            {
                "hook": "DESARROLLADO PARA EL SEÑOR DANNY",
                "sub": "Construido a medida bajo estándares de alto rendimiento y cero latencia.",
                "badge": "NOVASYSCOM CORP",
                "metrics": [{"label": "ESTADO", "val": "DESPLEGADO"}, {"label": "VERSIÓN", "val": "v4.6 QUANTUM"}]
            }
        ]
    }
}

# ─── Compilador Determinista de Hyperframes ──────────────────────────────────
def compile_hyperframe_composition(
    title: str,
    subtitle: str,
    scenes: List[Dict[str, Any]],
    template_id: str = "quantum_hud",
    aspect_ratio: str = "16:9",
    duration_per_scene: float = 3.2
) -> Dict[str, Any]:
    """
    Genera un archivo HTML de Hyperframes autosuficiente y determinista con GSAP 3.
    """
    tpl = TEMPLATES.get(template_id, TEMPLATES["quantum_hud"])
    is_vertical = (aspect_ratio == "9:16")
    
    # Dimensiones
    width = 1080 if is_vertical else 1920
    height = 1920 if is_vertical else 1080
    
    scenes_count = len(scenes)
    total_duration = scenes_count * duration_per_scene
    video_id = f"hf_{int(time.time())}_{template_id}_{'vert' if is_vertical else 'horiz'}"
    out_file = HYPERFRAMES_DIR / f"{video_id}.html"

    # Preparar el HTML de las escenas
    scenes_html = []
    metadata_scenes = []

    for idx, sc in enumerate(scenes):
        scene_num = idx + 1
        hook = html.escape(sc.get("hook", f"ESCENA {scene_num}"))
        sub = html.escape(sc.get("sub", ""))
        badge = html.escape(sc.get("badge", f"FRAME {scene_num:02d}"))
        metrics = sc.get("metrics", [])
        
        metrics_html = ""
        if metrics:
            metrics_items = []
            for m in metrics:
                mlabel = html.escape(str(m.get("label", "")))
                mval = html.escape(str(m.get("val", "")))
                metrics_items.append(f"""
                <div class="metric-box">
                    <span class="metric-lbl">{mlabel}</span>
                    <span class="metric-val">{mval}</span>
                </div>
                """)
            metrics_html = f"""<div class="metrics-grid">{''.join(metrics_items)}</div>"""

        scenes_html.append(f"""
        <!-- frame:{scene_num} duration:{int(duration_per_scene*1000)} transition:zoom-fade -->
        <section class="scene" id="scene-{scene_num}" data-scene="{idx}">
            <div class="scene-inner">
                <div class="scene-badge-row">
                    <span class="scene-badge">{badge}</span>
                    <span class="scene-index">{scene_num:02d} / {scenes_count:02d}</span>
                </div>
                <h1 class="scene-title">{hook}</h1>
                <p class="scene-sub">{sub}</p>
                {metrics_html}
            </div>
        </section>
        """)

        metadata_scenes.append({
            "index": scene_num,
            "durationMs": int(duration_per_scene * 1000),
            "hook": hook,
            "badge": badge
        })

    # Overlay específico
    overlay_html = ""
    if tpl["overlay"] == "scanlines":
        overlay_html = '<div class="scanlines-overlay"></div>'
    elif tpl["overlay"] == "grain":
        overlay_html = '<div class="grain-overlay"></div>'
    elif tpl["overlay"] == "radar":
        overlay_html = '<div class="radar-grid-overlay"><div class="radar-sweep"></div></div>'
    elif tpl["overlay"] == "arcade":
        overlay_html = '<div class="arcade-grid-overlay"></div>'

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width={width}, height={height}, initial-scale=1.0">
    <title>{html.escape(title)} · Hyperframes Video</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="{tpl['google_fonts']}" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
    <style>
        :root {{
            --bg-base: {tpl['bg']};
            --col-primary: {tpl['primary']};
            --col-accent: {tpl['accent']};
            --font-display: {tpl['font_display']};
            --font-body: {tpl['font_body']};
            --stage-w: {width}px;
            --stage-h: {height}px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%;
            height: 100%;
            background: #000000;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--font-body);
        }}
        
        /* ─── Stage Contenedor 1:1 Determinista ─── */
        #hyperframe-stage {{
            position: relative;
            width: var(--stage-w);
            height: var(--stage-h);
            background: var(--bg-base);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 0 80px rgba(0,0,0,0.9);
        }}

        /* ─── Encabezado Táctico de Composición ─── */
        .stage-header {{
            position: absolute;
            top: 40px;
            left: 50px;
            right: 50px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            z-index: 40;
            border-bottom: 1px solid rgba(255,255,255,0.12);
            padding-bottom: 18px;
        }}
        .stage-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .brand-core-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--col-primary);
            box-shadow: 0 0 16px var(--col-primary);
            animation: pulseDot 2s infinite;
        }}
        @keyframes pulseDot {{
            0%, 100% {{ transform: scale(1); opacity: 0.9; }}
            50% {{ transform: scale(1.3); opacity: 1; }}
        }}
        .brand-titles {{
            display: flex;
            flex-direction: column;
        }}
        .brand-main {{
            font-family: var(--font-display);
            font-size: {'24px' if is_vertical else '20px'};
            font-weight: 900;
            letter-spacing: 2.5px;
            color: var(--col-primary);
            text-shadow: 0 0 15px rgba(0, 240, 255, 0.4);
        }}
        .brand-sub {{
            font-size: {'13px' if is_vertical else '11px'};
            color: rgba(255, 255, 255, 0.6);
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }}
        .telemetry-tag {{
            font-size: {'14px' if is_vertical else '12px'};
            font-family: var(--font-display);
            color: var(--col-accent);
            border: 1px solid rgba(56, 249, 215, 0.3);
            background: rgba(56, 249, 215, 0.08);
            padding: 4px 12px;
            border-radius: 6px;
            letter-spacing: 1px;
        }}

        /* ─── Escenas ─── */
        .scene {{
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: {'60px 40px' if is_vertical else '80px 100px'};
            opacity: 0;
            pointer-events: none;
            z-index: 10;
        }}
        .scene.active {{
            opacity: 1;
            pointer-events: auto;
        }}
        .scene-inner {{
            width: 100%;
            max-width: {'920px' if is_vertical else '1400px'};
            display: flex;
            flex-direction: column;
            gap: {'24px' if is_vertical else '28px'};
        }}
        .scene-badge-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .scene-badge {{
            display: inline-block;
            font-size: {'15px' if is_vertical else '13px'};
            font-weight: 700;
            letter-spacing: 2px;
            color: var(--col-accent);
            background: rgba(0, 240, 255, 0.1);
            border: 1px solid var(--col-accent);
            padding: 4px 14px;
            border-radius: 4px;
            text-transform: uppercase;
        }}
        .scene-index {{
            font-size: {'16px' if is_vertical else '14px'};
            color: rgba(255, 255, 255, 0.4);
            letter-spacing: 2px;
            font-family: var(--font-display);
        }}
        .scene-title {{
            font-family: var(--font-display);
            font-size: {'46px' if is_vertical else '64px'};
            font-weight: 900;
            line-height: 1.12;
            color: #ffffff;
            letter-spacing: {'1.5px' if is_vertical else '2.5px'};
            text-transform: uppercase;
            text-shadow: 0 4px 30px rgba(0,0,0,0.8);
        }}
        .scene-sub {{
            font-size: {'22px' if is_vertical else '26px'};
            line-height: 1.45;
            color: rgba(255, 255, 255, 0.82);
            font-weight: 400;
            max-width: 90%;
        }}
        
        /* ─── Métricas e Infografía de Escena ─── */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 10px;
        }}
        .metric-box {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-left: 3px solid var(--col-primary);
            padding: 16px 20px;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            backdrop-filter: blur(10px);
        }}
        .metric-lbl {{
            font-size: 11px;
            font-family: var(--font-display);
            color: rgba(255, 255, 255, 0.5);
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }}
        .metric-val {{
            font-size: {'28px' if is_vertical else '32px'};
            font-family: var(--font-display);
            font-weight: 800;
            color: var(--col-primary);
            text-shadow: 0 0 15px rgba(0, 240, 255, 0.5);
        }}

        /* ─── Barra de Progreso y Timeline Inferior ─── */
        .stage-footer {{
            position: absolute;
            bottom: 35px;
            left: 50px;
            right: 50px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 40;
        }}
        .timeline-bar-bg {{
            width: 100%;
            height: 4px;
            background: rgba(255, 255, 255, 0.12);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
        }}
        .timeline-bar-fill {{
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 0%;
            background: linear-gradient(90deg, var(--col-primary), var(--col-accent));
            box-shadow: 0 0 10px var(--col-primary);
        }}
        .timeline-info-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 12px;
            color: rgba(255, 255, 255, 0.5);
            font-family: var(--font-display);
            letter-spacing: 1px;
        }}

        /* ─── Controles Flotantes Intercativos ─── */
        .interactive-dock {{
            position: absolute;
            bottom: 80px;
            right: 50px;
            z-index: 50;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(0, 0, 0, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 30px;
            padding: 6px 12px;
            backdrop-filter: blur(14px);
        }}
        .dock-btn {{
            background: transparent;
            border: none;
            color: #ffffff;
            cursor: pointer;
            padding: 6px 10px;
            font-size: 14px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.2s;
        }}
        .dock-btn:hover {{
            color: var(--col-primary);
            background: rgba(255, 255, 255, 0.1);
        }}

        /* ─── Efectos de Grano / Scanlines ─── */
        .scanlines-overlay {{
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 30;
            background: repeating-linear-gradient(180deg, transparent 0 2px, rgba(0, 240, 255, 0.03) 2px 4px);
            mix-blend-mode: overlay;
        }}
        .grain-overlay {{
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 30;
            opacity: 0.12;
            background-image: radial-gradient(#ffffff 0.8px, transparent 0.8px);
            background-size: 4px 4px;
        }}
        .radar-grid-overlay {{
            position: absolute;
            inset: 0;
            pointer-events: none;
            z-index: 25;
            background: radial-gradient(circle at center, transparent 40%, rgba(0,255,136,0.06) 95%),
                        linear-gradient(rgba(0,255,136,0.05) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(0,255,136,0.05) 1px, transparent 1px);
            background-size: 100% 100%, 40px 40px, 40px 40px;
        }}
    </style>
</head>
<body>

    <div id="hyperframe-stage">
        {overlay_html}

        <!-- Header -->
        <header class="stage-header">
            <div class="stage-brand">
                <div class="brand-core-dot"></div>
                <div class="brand-titles">
                    <span class="brand-main">{html.escape(title)}</span>
                    <span class="brand-sub">{html.escape(subtitle)}</span>
                </div>
            </div>
            <div class="telemetry-tag">HYPERFRAMES // 60 FPS</div>
        </header>

        <!-- Escenas -->
        {''.join(scenes_html)}

        <!-- Footer Timeline -->
        <footer class="stage-footer">
            <div class="timeline-bar-bg">
                <div class="timeline-bar-fill" id="timeline-fill"></div>
            </div>
            <div class="timeline-info-row">
                <span id="time-readout">00.0s / {total_duration:04.1f}s</span>
                <span id="frame-readout">FRAME 01 / {scenes_count:02d}</span>
                <span>TECLAS: ESPACIO (PAUSA) · 1-{scenes_count} · R (REINICIAR)</span>
            </div>
        </footer>

        <!-- Dock Interactivo -->
        <div class="interactive-dock">
            <button class="dock-btn" id="btn-play-pause" onclick="togglePlayPause()" title="Reproducir / Pausar">⏸ Pausa</button>
            <button class="dock-btn" onclick="prevFrame()" title="Cuadro Anterior">⏮</button>
            <button class="dock-btn" onclick="nextFrame()" title="Siguiente Cuadro">⏭</button>
            <button class="dock-btn" onclick="restartVideo()" title="Reiniciar">🔄</button>
        </div>
    </div>

    <!-- ── GSAP Deterministic Animation Script ── -->
    <script>
        const SCENES_COUNT = {scenes_count};
        const DURATION_PER_SCENE = {duration_per_scene};
        const TOTAL_DURATION = {total_duration};
        let currentSceneIndex = 0;
        let isPlaying = true;

        const scenes = document.querySelectorAll('.scene');
        const fillBar = document.getElementById('timeline-fill');
        const timeReadout = document.getElementById('time-readout');
        const frameReadout = document.getElementById('frame-readout');
        const btnPlay = document.getElementById('btn-play-pause');

        // Master Timeline GSAP
        const masterTl = gsap.timeline({{
            paused: false,
            repeat: -1,
            onUpdate: onTimelineUpdate
        }});

        // Construir secuencias de cada escena
        scenes.forEach((sceneEl, i) => {{
            const tStart = i * DURATION_PER_SCENE;
            const tEnd = (i + 1) * DURATION_PER_SCENE;
            const title = sceneEl.querySelector('.scene-title');
            const sub = sceneEl.querySelector('.scene-sub');
            const badge = sceneEl.querySelector('.scene-badge');
            const metrics = sceneEl.querySelectorAll('.metric-box');

            // Entrada
            masterTl.add(() => {{
                activateScene(i);
            }}, tStart);

            masterTl.fromTo(sceneEl, 
                {{ opacity: 0 }}, 
                {{ opacity: 1, duration: 0.35, ease: 'power2.out' }}, 
                tStart
            );

            masterTl.fromTo(title, 
                {{ y: 35, opacity: 0, scale: 0.94 }}, 
                {{ y: 0, opacity: 1, scale: 1, duration: 0.6, ease: 'back.out(1.4)' }}, 
                tStart + 0.1
            );

            if (sub) {{
                masterTl.fromTo(sub, 
                    {{ y: 25, opacity: 0 }}, 
                    {{ y: 0, opacity: 1, duration: 0.5, ease: 'power2.out' }}, 
                    tStart + 0.25
                );
            }}

            if (metrics.length) {{
                masterTl.fromTo(metrics, 
                    {{ y: 20, opacity: 0, scale: 0.92 }}, 
                    {{ y: 0, opacity: 1, scale: 1, stagger: 0.08, duration: 0.45, ease: 'back.out(1.6)' }}, 
                    tStart + 0.35
                );
            }}

            // Salida antes del siguiente corte (excepto última antes de loop)
            masterTl.to(sceneEl, 
                {{ opacity: 0, y: -15, duration: 0.3, ease: 'power2.in' }}, 
                tEnd - 0.3
            );
        }});

        function activateScene(index) {{
            currentSceneIndex = index;
            scenes.forEach((el, idx) => {{
                el.classList.toggle('active', idx === index);
            }});
            frameReadout.textContent = `FRAME ${{String(index + 1).padStart(2, '0')}} / ${{String(SCENES_COUNT).padStart(2, '0')}}`;
        }}

        function onTimelineUpdate() {{
            const curTime = masterTl.time() % TOTAL_DURATION;
            const pct = (curTime / TOTAL_DURATION) * 100;
            fillBar.style.width = pct + '%';
            timeReadout.textContent = `${{curTime.toFixed(1).padStart(4, '0')}}s / ${{TOTAL_DURATION.toFixed(1)}}s`;
        }}

        function togglePlayPause() {{
            if (masterTl.paused()) {{
                masterTl.play();
                btnPlay.textContent = "⏸ Pausa";
            }} else {{
                masterTl.pause();
                btnPlay.textContent = "▶ Reanudar";
            }}
        }}

        function jumpToScene(idx) {{
            if (idx >= 0 && idx < SCENES_COUNT) {{
                masterTl.seek(idx * DURATION_PER_SCENE);
                activateScene(idx);
            }}
        }}

        function nextFrame() {{
            jumpToScene((currentSceneIndex + 1) % SCENES_COUNT);
        }}

        function prevFrame() {{
            jumpToScene((currentSceneIndex - 1 + SCENES_COUNT) % SCENES_COUNT);
        }}

        function restartVideo() {{
            masterTl.restart();
            activateScene(0);
        }}

        // Atajos de teclado
        window.addEventListener('keydown', (e) => {{
            if (e.code === 'Space') {{
                e.preventDefault();
                togglePlayPause();
            }} else if (e.key >= '1' && e.key <= String(SCENES_COUNT)) {{
                jumpToScene(parseInt(e.key) - 1);
            }} else if (e.key.toLowerCase() === 'r') {{
                restartVideo();
            }} else if (e.key === 'ArrowRight') {{
                nextFrame();
            }} else if (e.key === 'ArrowLeft') {{
                prevFrame();
            }}
        }});

        // Inicializar escena 0
        activateScene(0);
    </script>

    <!-- 
    HYPERFRAMES_META:
    {json.dumps({
        "version": "1.0.0",
        "title": title,
        "template": template_id,
        "aspectRatio": aspect_ratio,
        "fps": 60,
        "totalDurationSec": total_duration,
        "scenes": metadata_scenes
    }, indent=2)}
    -->
</body>
</html>
"""

    out_file.write_text(html_content, encoding="utf-8")

    return {
        "ok": True,
        "id": video_id,
        "filename": out_file.name,
        "url": f"/panel/hyperframes/{out_file.name}",
        "template": template_id,
        "aspect_ratio": aspect_ratio,
        "scenes_count": scenes_count,
        "total_duration": total_duration,
        "local_path": str(out_file)
    }

# ─── Generación Inteligente desde Prompt Libre ────────────────────────────────
def generate_hyperframe_from_prompt(
    prompt: str,
    template_id: str = "quantum_hud",
    aspect_ratio: str = "16:9"
) -> Dict[str, Any]:
    """
    Toma un prompt o tema y sintetiza una historia de 3-4 escenas visuales,
    o utiliza un preset si coincide.
    """
    clean_prompt = prompt.strip().lower()
    
    # 1. Chequeo de Presets directos
    if "briefing" in clean_prompt or "matutino" in clean_prompt:
        p = PRESETS["morning_briefing"]
        return compile_hyperframe_composition(p["title"], p["subtitle"], p["scenes"], template_id, aspect_ratio)
    elif "seguridad" in clean_prompt or "osint" in clean_prompt or "radar" in clean_prompt:
        p = PRESETS["security_radar"]
        return compile_hyperframe_composition(p["title"], p["subtitle"], p["scenes"], template_id, aspect_ratio)
    elif "showcase" in clean_prompt or "ecosistema" in clean_prompt or "novasyscom" in clean_prompt:
        p = PRESETS["tech_showcase"]
        return compile_hyperframe_composition(p["title"], p["subtitle"], p["scenes"], template_id, aspect_ratio)

    # 2. Síntesis estructurada adaptativa para cualquier tema
    title = prompt.upper() if len(prompt) < 30 else prompt[:30].upper() + "..."
    subtitle = "SÍNTESIS CINEMÁTICA // ALBERTH HYPERFRAMES"
    
    scenes = [
        {
            "hook": prompt.upper()[:45],
            "sub": "Análisis automatizado generado por el motor de código de video de Alberth.",
            "badge": "INICIO // HOOK",
            "metrics": [{"label": "MOTOR", "val": "HYPERFRAMES"}, {"label": "ESTADO", "val": "OPTIMIZADO"}]
        },
        {
            "hook": "EVIDENCIA Y ARQUITECTURA",
            "sub": "Transformación de datos en tiempo real a fotogramas interactivos de 60 cuadros por segundo.",
            "badge": "NÚCLEO DE DATOS",
            "metrics": [{"label": "RESOLUCIÓN", "val": "1080p FULL HD"}, {"label": "VELOCIDAD", "val": "60 FPS"}]
        },
        {
            "hook": "SISTEMA LISTO PARA PRODUCCIÓN",
            "sub": "Composición determinista apta para exportación a MP4 y distribución ejecutiva.",
            "badge": "CONCLUSIÓN // CTA",
            "metrics": [{"label": "PRECISIÓN", "val": "100%"}, {"label": "AUDITORÍA", "val": "APROBADA"}]
        }
    ]

    return compile_hyperframe_composition(title, subtitle, scenes, template_id, aspect_ratio)

def list_generated_hyperframes() -> List[Dict[str, Any]]:
    """Lista todos los videos Hyperframes generados localmente."""
    if not HYPERFRAMES_DIR.exists():
        return []
    
    results = []
    for f in sorted(HYPERFRAMES_DIR.glob("*.html"), key=os.path.getmtime, reverse=True):
        stat = f.stat()
        results.append({
            "id": f.stem,
            "filename": f.name,
            "url": f"/panel/hyperframes/{f.name}",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "size_bytes": stat.st_size
        })
    return results

if __name__ == "__main__":
    print("🎬 Probando Alberth Hyperframes Generator...")
    res = generate_hyperframe_from_prompt("Briefing Matutino Alberth", "quantum_hud", "16:9")
    print(f"✅ Generado: {res['url']} ({res['total_duration']}s)")
