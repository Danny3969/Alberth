#!/usr/bin/env python3
# =============================================================================
# ALBERTH OPENPAGE ENGINE — Motor de UI Declarativa Basada en Esquemas JSON
# Filosofía OpenPage / A2UI: El Agente y el Usuario modifican un esquema JSON
# como única fuente de verdad. El motor lo compila de forma determinista
# e inmune a alucinaciones de sintaxis o código roto, aplicando DESIGN.md.
# =============================================================================

from __future__ import annotations
import json
import time
import sys
import html
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

# ─── Modelos Declarativos de Componentes (OpenPage AST) ────────────────────────

class ComponentProps(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: Optional[str] = None
    subtitle: Optional[str] = None
    value: Optional[Union[str, int, float]] = None
    unit: Optional[str] = None
    trend: Optional[str] = None         # e.g., "+12%", "-4%"
    trend_type: Optional[str] = None    # "positive", "negative", "neutral", "warn"
    level: Optional[str] = None         # "info", "success", "warning", "critical"
    columns: Optional[List[str]] = None
    rows: Optional[List[List[Any]]] = None
    items: Optional[List[Dict[str, Any]]] = None # For task lists, bar charts
    label: Optional[str] = None
    action: Optional[str] = None        # e.g., "sys_cmd", "navigate", "open_url"
    action_arg: Optional[str] = None
    columns_count: Optional[int] = None # For grids
    variant: Optional[str] = None       # "primary", "secondary", "ghost", "danger"
    extra_css: Optional[str] = None

class OpenPageNode(BaseModel):
    id: Optional[str] = None
    type: str = Field(..., description="Tipo de componente registrado en el catálogo")
    props: Dict[str, Any] = Field(default_factory=dict)
    children: Optional[List[OpenPageNode]] = None

class OpenPageSchema(BaseModel):
    version: str = "1.0.0"
    title: str = "Alberth Live Canvas"
    subtitle: Optional[str] = "Proyección declarativa de interfaz cuántica"
    theme: str = "quantum-cockpit"
    updated_at: float = Field(default_factory=time.time)
    root: OpenPageNode


# ─── Catálogo y Compilador Determinista (JSON -> HTML/CSS Seguro) ─────────────

class OpenPageCompiler:
    """
    Compila el esquema JSON de forma completamente segura y determinista,
    sin permitir inyecciones arbitrarias de script no validadas y usando los
    tokens del contrato canónico DESIGN.md.
    """

    @staticmethod
    def _escape(val: Any) -> str:
        if val is None:
            return ""
        return html.escape(str(val))

    @classmethod
    def render_node(cls, node: OpenPageNode) -> str:
        ntype = node.type.lower()
        props = node.props or {}
        children_html = "".join(cls.render_node(c) for c in (node.children or []))
        node_id = f'id="op-{cls._escape(node.id)}"' if node.id else ""

        if ntype in ("container", "root"):
            return f"""<div {node_id} class="op-container">{children_html}</div>"""

        elif ntype == "stack":
            gap = props.get("gap", "12px")
            align = props.get("align", "stretch")
            return f"""<div {node_id} class="op-stack" style="gap:{cls._escape(gap)};align-items:{cls._escape(align)};">{children_html}</div>"""

        elif ntype == "grid":
            cols = props.get("columns", 2)
            gap = props.get("gap", "12px")
            return f"""<div {node_id} class="op-grid" style="grid-template-columns:repeat({int(cols)}, minmax(0, 1fr));gap:{cls._escape(gap)};">{children_html}</div>"""

        elif ntype == "card":
            title = props.get("title")
            sub = props.get("subtitle")
            badge = props.get("badge")
            header_html = ""
            if title or badge:
                badge_html = f"""<span class="op-badge op-badge-cyan">{cls._escape(badge)}</span>""" if badge else ""
                sub_html = f"""<div class="op-card-sub">{cls._escape(sub)}</div>""" if sub else ""
                header_html = f"""
                <div class="op-card-header">
                    <div>
                        <h4 class="op-card-title">{cls._escape(title)}</h4>
                        {sub_html}
                    </div>
                    {badge_html}
                </div>"""
            return f"""
            <div {node_id} class="op-card">
                {header_html}
                <div class="op-card-body">{children_html}</div>
            </div>"""

        elif ntype == "metrics_row":
            return f"""<div {node_id} class="op-metrics-row">{children_html}</div>"""

        elif ntype == "metric":
            label = cls._escape(props.get("label", "Métrica"))
            val = cls._escape(props.get("value", "--"))
            unit = cls._escape(props.get("unit", ""))
            trend = props.get("trend")
            trend_type = props.get("trend_type", "neutral")
            
            trend_class = {
                "positive": "op-trend-pos",
                "negative": "op-trend-neg",
                "warn": "op-trend-warn",
                "neutral": "op-trend-neu"
            }.get(trend_type, "op-trend-neu")

            trend_html = f"""<span class="op-metric-trend {trend_class}">{cls._escape(trend)}</span>""" if trend else ""

            return f"""
            <div {node_id} class="op-metric-box">
                <span class="op-metric-label">{label}</span>
                <div class="op-metric-val-wrap">
                    <span class="op-metric-value">{val}</span>
                    <span class="op-metric-unit">{unit}</span>
                    {trend_html}
                </div>
            </div>"""

        elif ntype == "alert_banner":
            level = props.get("level", "info") # info, success, warning, critical
            title = props.get("title")
            text = props.get("text", "")
            icon_map = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "critical": "🚨"
            }
            icon = icon_map.get(level, "🔹")
            title_html = f"""<strong>{cls._escape(title)}: </strong>""" if title else ""
            return f"""
            <div {node_id} class="op-alert op-alert-{cls._escape(level)}">
                <span class="op-alert-icon">{icon}</span>
                <div class="op-alert-content">
                    {title_html}{cls._escape(text)}
                </div>
            </div>"""

        elif ntype == "chart_bars":
            title = props.get("title")
            items = props.get("items", []) # [{"label": "CPU", "value": 75, "color": "cyan", "sub": "75%"}]
            items_html = []
            for item in items:
                lbl = cls._escape(item.get("label", ""))
                val = max(0, min(100, float(item.get("value", 0))))
                color = item.get("color", "cyan")
                sub = cls._escape(item.get("sub", f"{int(val)}%"))
                bar_color = {
                    "cyan": "var(--cyan-core, #00f0ff)",
                    "green": "var(--emerald-live, #00ff88)",
                    "amber": "var(--amber-warn, #ffb703)",
                    "crimson": "var(--crimson-crit, #ff0055)",
                    "gold": "#f0c060"
                }.get(color, "var(--cyan-core, #00f0ff)")

                items_html.append(f"""
                <div class="op-bar-item">
                    <div class="op-bar-header">
                        <span class="op-bar-label">{lbl}</span>
                        <span class="op-bar-val">{sub}</span>
                    </div>
                    <div class="op-bar-track">
                        <div class="op-bar-fill" style="width:{val}%; background:{bar_color};"></div>
                    </div>
                </div>""")
            
            title_html = f"""<h5 class="op-chart-title">{cls._escape(title)}</h5>""" if title else ""
            return f"""
            <div {node_id} class="op-chart-bars">
                {title_html}
                <div class="op-bar-list">{"".join(items_html)}</div>
            </div>"""

        elif ntype == "data_table":
            cols = props.get("columns", [])
            rows = props.get("rows", [])
            th_html = "".join(f"<th>{cls._escape(c)}</th>" for c in cols)
            tr_html = []
            for r in rows:
                tds = "".join(f"<td>{cls._escape(cell)}</td>" for cell in r)
                tr_html.append(f"<tr>{tds}</tr>")
            
            return f"""
            <div {node_id} class="op-table-wrap">
                <table class="op-table">
                    <thead><tr>{th_html}</tr></thead>
                    <tbody>{"".join(tr_html)}</tbody>
                </table>
            </div>"""

        elif ntype == "task_list":
            title = props.get("title")
            tasks = props.get("items", []) # [{"text": "...", "done": true/false, "tag": "ALTA"}]
            t_items = []
            for t in tasks:
                done = bool(t.get("done", False))
                tag = t.get("tag")
                txt = cls._escape(t.get("text", ""))
                done_class = "op-task-done" if done else ""
                tag_html = f"""<span class="op-task-tag">{cls._escape(tag)}</span>""" if tag else ""
                icon = "☑" if done else "☐"
                t_items.append(f"""
                <div class="op-task-item {done_class}">
                    <span class="op-task-check">{icon}</span>
                    <span class="op-task-txt">{txt}</span>
                    {tag_html}
                </div>""")
            
            title_html = f"""<h5 class="op-chart-title">{cls._escape(title)}</h5>""" if title else ""
            return f"""
            <div {node_id} class="op-task-container">
                {title_html}
                <div class="op-tasks-list">{"".join(t_items)}</div>
            </div>"""

        elif ntype == "action_group":
            return f"""<div {node_id} class="op-actions-wrap">{children_html}</div>"""

        elif ntype == "button":
            lbl = cls._escape(props.get("label", "Ejecutar"))
            action = cls._escape(props.get("action", "client_trigger"))
            arg = cls._escape(props.get("action_arg", ""))
            variant = props.get("variant", "primary")
            var_class = f"op-btn-{variant}"
            return f"""
            <button {node_id} class="op-btn {var_class}" onclick="handleOpenPageAction('{action}', '{arg}')">
                {lbl}
            </button>"""

        elif ntype == "text":
            content = cls._escape(props.get("text", ""))
            style = props.get("style", "body")
            tag = "p" if style == "body" else ("h3" if style == "header" else "span")
            return f"""<{tag} {node_id} class="op-text-{cls._escape(style)}">{content}</{tag}>"""

        elif ntype == "divider":
            return f"""<div {node_id} class="op-divider"></div>"""

        # Fallback genérico para componentes no reconocidos
        return f"""<div {node_id} class="op-generic-node">{children_html}</div>"""

    @classmethod
    def compile(cls, schema: OpenPageSchema) -> str:
        body_html = cls.render_node(schema.root)
        header_html = f"""
        <div class="op-canvas-banner">
            <div class="op-banner-left">
                <span class="op-banner-dot"></span>
                <h3 class="op-banner-title">{cls._escape(schema.title)}</h3>
            </div>
            <div class="op-banner-right">
                <span class="op-banner-sub">{cls._escape(schema.subtitle or '')}</span>
                <span class="op-banner-badge">OPENPAGE · CANONICAL</span>
            </div>
        </div>"""
        
        return f"""
        <div class="openpage-canvas-wrapper" data-theme="{cls._escape(schema.theme)}">
            {header_html}
            <div class="op-canvas-content">
                {body_html}
            </div>
        </div>
        """

    @staticmethod
    def get_canonical_css() -> str:
        """Devuelve los estilos nativos basados en los tokens de DESIGN.md"""
        return """
        /* ─── Alberth OpenPage / A2UI Canonical Component System ─── */
        .openpage-canvas-wrapper {
            font-family: var(--font-data, 'Rajdhani', sans-serif);
            color: var(--text-main, #f0f6fc);
            display: flex;
            flex-direction: column;
            gap: 16px;
            width: 100%;
            animation: opFadeIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes opFadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .op-canvas-banner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 14px;
            background: rgba(4, 7, 17, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5), inset 0 0 10px rgba(0, 240, 255, 0.08);
        }
        .op-banner-left { display: flex; align-items: center; gap: 8px; }
        .op-banner-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--cyan-core, #00f0ff);
            box-shadow: 0 0 8px var(--cyan-core, #00f0ff);
            animation: opPulse 1.8s infinite alternate;
        }
        @keyframes opPulse {
            from { transform: scale(0.9); opacity: 0.7; }
            to { transform: scale(1.2); opacity: 1; }
        }
        .op-banner-title {
            font-family: var(--font-hud, 'Orbitron', sans-serif);
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #ffffff;
            margin: 0;
        }
        .op-banner-right { display: flex; align-items: center; gap: 10px; }
        .op-banner-sub { font-size: 11px; color: var(--text-dim, #8b9bb4); }
        .op-banner-badge {
            font-family: var(--font-hud, 'Orbitron', monospace);
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(0, 240, 255, 0.15);
            border: 1px solid rgba(0, 240, 255, 0.4);
            color: var(--cyan-core, #00f0ff);
            letter-spacing: 0.05em;
        }
        .op-canvas-content {
            display: flex;
            flex-direction: column;
            gap: 14px;
        }
        .op-container { display: flex; flex-direction: column; gap: 12px; }
        .op-stack { display: flex; flex-direction: column; }
        .op-grid { display: grid; }
        @media(max-width: 680px) { .op-grid { grid-template-columns: 1fr !important; } }
        
        /* Tarjetas Cuánticas */
        .op-card {
            background: rgba(6, 14, 28, 0.72);
            border: 1px solid rgba(0, 240, 255, 0.22);
            border-radius: 10px;
            padding: 14px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.55), inset 0 0 14px rgba(0, 240, 255, 0.05);
            backdrop-filter: blur(14px);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .op-card:hover {
            border-color: rgba(0, 240, 255, 0.5);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.65), inset 0 0 18px rgba(0, 240, 255, 0.12);
        }
        .op-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid rgba(0, 240, 255, 0.12);
        }
        .op-card-title {
            font-family: var(--font-hud, 'Orbitron', sans-serif);
            font-size: 12px;
            font-weight: 600;
            color: var(--cyan-core, #00f0ff);
            letter-spacing: 0.06em;
            margin: 0;
            text-transform: uppercase;
        }
        .op-card-sub { font-size: 11px; color: var(--text-dim, #8b9bb4); margin-top: 2px; }
        .op-badge {
            font-family: var(--font-hud, monospace);
            font-size: 9px;
            padding: 2px 7px;
            border-radius: 4px;
            letter-spacing: 0.05em;
        }
        .op-badge-cyan {
            background: rgba(0, 240, 255, 0.15);
            border: 1px solid rgba(0, 240, 255, 0.5);
            color: #00f0ff;
        }

        /* Métricas */
        .op-metrics-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
            gap: 10px;
        }
        .op-metric-box {
            background: rgba(4, 8, 18, 0.85);
            border: 1px solid rgba(0, 240, 255, 0.18);
            border-radius: 8px;
            padding: 10px 12px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .op-metric-label {
            font-size: 10px;
            font-weight: 600;
            color: var(--text-dim, #8b9bb4);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .op-metric-val-wrap {
            display: flex;
            align-items: baseline;
            gap: 5px;
            flex-wrap: wrap;
        }
        .op-metric-value {
            font-family: var(--font-hud, 'Orbitron', monospace);
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
        }
        .op-metric-unit { font-size: 10px; color: var(--cyan-core, #00f0ff); }
        .op-metric-trend {
            font-size: 10px;
            font-weight: 600;
            padding: 1px 5px;
            border-radius: 3px;
        }
        .op-trend-pos { background: rgba(0, 255, 136, 0.15); color: #00ff88; }
        .op-trend-neg { background: rgba(255, 0, 85, 0.15); color: #ff0055; }
        .op-trend-warn { background: rgba(255, 183, 3, 0.15); color: #ffb703; }
        .op-trend-neu { background: rgba(255, 255, 255, 0.1); color: #cbd5e1; }

        /* Banners de Alerta */
        .op-alert {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 12px;
        }
        .op-alert-info {
            background: rgba(0, 119, 255, 0.12);
            border: 1px solid rgba(0, 119, 255, 0.4);
            color: #93c5fd;
        }
        .op-alert-success {
            background: rgba(0, 255, 136, 0.12);
            border: 1px solid rgba(0, 255, 136, 0.4);
            color: #86efac;
        }
        .op-alert-warning {
            background: rgba(255, 183, 3, 0.12);
            border: 1px solid rgba(255, 183, 3, 0.4);
            color: #fde047;
        }
        .op-alert-critical {
            background: rgba(255, 0, 85, 0.15);
            border: 1px solid rgba(255, 0, 85, 0.5);
            color: #fda4af;
        }
        .op-alert-icon { font-size: 14px; }
        .op-alert-content { flex: 1; line-height: 1.4; }

        /* Gráfico de Barras */
        .op-chart-bars { display: flex; flex-direction: column; gap: 8px; }
        .op-chart-title {
            font-family: var(--font-hud, sans-serif);
            font-size: 11px;
            color: var(--text-dim, #8b9bb4);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0 0 4px 0;
        }
        .op-bar-list { display: flex; flex-direction: column; gap: 8px; }
        .op-bar-item { display: flex; flex-direction: column; gap: 3px; }
        .op-bar-header { display: flex; justify-content: space-between; font-size: 11px; }
        .op-bar-label { color: #e2e8f0; }
        .op-bar-val { font-family: var(--font-hud, monospace); color: var(--cyan-core, #00f0ff); font-size: 10px; }
        .op-bar-track {
            height: 6px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 3px;
            overflow: hidden;
        }
        .op-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease-out; }

        /* Tablas */
        .op-table-wrap { width: 100%; overflow-x: auto; border-radius: 6px; border: 1px solid rgba(0, 240, 255, 0.15); }
        .op-table { width: 100%; border-collapse: collapse; text-align: left; font-size: 11px; }
        .op-table th {
            background: rgba(0, 240, 255, 0.08);
            color: var(--cyan-core, #00f0ff);
            padding: 7px 10px;
            font-family: var(--font-hud, sans-serif);
            font-size: 9px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
        }
        .op-table td {
            padding: 8px 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: #cbd5e1;
        }
        .op-table tr:hover td { background: rgba(0, 240, 255, 0.04); color: #fff; }

        /* Lista de Tareas */
        .op-tasks-list { display: flex; flex-direction: column; gap: 6px; }
        .op-task-item {
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(4, 8, 18, 0.6);
            border: 1px solid rgba(0, 240, 255, 0.12);
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 12px;
        }
        .op-task-check { font-size: 14px; color: var(--cyan-core, #00f0ff); }
        .op-task-txt { flex: 1; color: #f1f5f9; }
        .op-task-done .op-task-txt { text-decoration: line-through; color: var(--text-dim, #64748b); }
        .op-task-tag {
            font-size: 9px;
            padding: 1px 6px;
            border-radius: 3px;
            background: rgba(255, 183, 3, 0.15);
            color: #ffb703;
            font-family: var(--font-hud, monospace);
        }

        /* Botones de Acción */
        .op-actions-wrap { display: flex; gap: 8px; flex-wrap: wrap; }
        .op-btn {
            font-family: var(--font-hud, sans-serif);
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.06em;
            padding: 6px 14px;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            text-transform: uppercase;
            border: 1px solid transparent;
        }
        .op-btn-primary {
            background: var(--cyan-core, #00f0ff);
            color: #040711;
            box-shadow: 0 0 10px rgba(0, 240, 255, 0.4);
        }
        .op-btn-primary:hover {
            background: #38f9d7;
            box-shadow: 0 0 16px rgba(0, 240, 255, 0.7);
            transform: translateY(-1px);
        }
        .op-btn-secondary {
            background: rgba(0, 240, 255, 0.1);
            border-color: rgba(0, 240, 255, 0.3);
            color: #00f0ff;
        }
        .op-btn-secondary:hover {
            background: rgba(0, 240, 255, 0.2);
            border-color: rgba(0, 240, 255, 0.7);
        }
        .op-btn-danger {
            background: rgba(255, 0, 85, 0.15);
            border-color: rgba(255, 0, 85, 0.4);
            color: #ff0055;
        }
        .op-btn-danger:hover {
            background: rgba(255, 0, 85, 0.3);
            box-shadow: 0 0 12px rgba(255, 0, 85, 0.5);
        }
        .op-divider { height: 1px; background: rgba(0, 240, 255, 0.15); margin: 6px 0; }
        """


# ─── Presets Estructurados Canónicos de OpenPage ──────────────────────────────

def get_openpage_preset(name: str) -> OpenPageSchema:
    """Devuelve un esquema canónico preconfigurado según el caso de uso"""
    now = time.time()
    
    if name in ("system", "telemetria", "sistema"):
        return OpenPageSchema(
            title="Telemetría de Sistema y Daemons",
            subtitle="Estado de hardware y servicios autónomos de Alberth",
            updated_at=now,
            root=OpenPageNode(
                type="stack",
                props={"gap": "14px"},
                children=[
                    OpenPageNode(
                        type="metrics_row",
                        children=[
                            OpenPageNode(type="metric", props={"label": "Servicios PM2", "value": "4/4", "unit": "ONLINE", "trend": "ESTABLE", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "Latencia Live", "value": "18", "unit": "ms", "trend": "ULTRA-LIVE", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "RAM Servidor", "value": "9.3", "unit": "MB", "trend": "-2%", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "Voz Charon", "value": "24", "unit": "kHz", "trend": "ACTIVA", "trend_type": "neutral"}),
                        ]
                    ),
                    OpenPageNode(
                        type="grid",
                        props={"columns": 2, "gap": "12px"},
                        children=[
                            OpenPageNode(
                                type="card",
                                props={"title": "Carga de Recursos", "badge": "ACTIVO"},
                                children=[
                                    OpenPageNode(
                                        type="chart_bars",
                                        props={
                                            "items": [
                                                {"label": "CPU Host (iMac)", "value": 12, "color": "cyan", "sub": "12%"},
                                                {"label": "Uso de RAM Global", "value": 26, "color": "green", "sub": "26%"},
                                                {"label": "Disco Principal (SSD)", "value": 64, "color": "amber", "sub": "64% Ocupado"},
                                                {"label": "Caché de Audio Echo", "value": 8, "color": "cyan", "sub": "8 MB"}
                                            ]
                                        }
                                    )
                                ]
                            ),
                            OpenPageNode(
                                type="card",
                                props={"title": "Procesos PM2 en iMac", "badge": "4 PROCESOS"},
                                children=[
                                    OpenPageNode(
                                        type="data_table",
                                        props={
                                            "columns": ["ID", "Servicio", "Estado", "RAM"],
                                            "rows": [
                                                ["0", "alberth-web", "ONLINE", "9.3 MB"],
                                                ["1", "alberth-voice", "ONLINE", "25.5 MB"],
                                                ["2", "alberth-reminders", "ONLINE", "4.7 MB"],
                                                ["3", "alberth-qa-watcher", "ONLINE", "3.1 MB"]
                                            ]
                                        }
                                    )
                                ]
                            )
                        ]
                    ),
                    OpenPageNode(
                        type="alert_banner",
                        props={"level": "success", "title": "SISTEMA SEGURO", "text": "Todos los daemons autónomos se encuentran en parámetros nominales y sincronizados con GitHub main."}
                    )
                ]
            )
        )

    elif name in ("finanzas", "gastos", "finance"):
        return OpenPageSchema(
            title="Tablero Contable & Proyección de Gastos",
            subtitle="Resumen de flujos, partidas presupuestarias y alertas",
            updated_at=now,
            root=OpenPageNode(
                type="stack",
                props={"gap": "14px"},
                children=[
                    OpenPageNode(
                        type="metrics_row",
                        children=[
                            OpenPageNode(type="metric", props={"label": "Presupuesto Mensual", "value": "$4,500", "unit": "USD", "trend": "TOTAL", "trend_type": "neutral"}),
                            OpenPageNode(type="metric", props={"label": "Ejecutado al Momento", "value": "$1,820", "unit": "USD", "trend": "40.4%", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "Remanente Disponible", "value": "$2,680", "unit": "USD", "trend": "FAVORABLE", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "Desviación Prevista", "value": "+1.8%", "unit": "ESTIMADA", "trend": "BAJO CONTROL", "trend_type": "warn"}),
                        ]
                    ),
                    OpenPageNode(
                        type="card",
                        props={"title": "Distribución por Categorías", "badge": "SEPTIEMBRE 2026"},
                        children=[
                            OpenPageNode(
                                type="chart_bars",
                                props={
                                    "items": [
                                        {"label": "Infraestructura & Servidores Cloud", "value": 45, "color": "cyan", "sub": "$820 (45%)"},
                                        {"label": "Licencias de Software & Modelos IA", "value": 30, "color": "green", "sub": "$540 (30%)"},
                                        {"label": "Servicios de Oficina & Conectividad", "value": 15, "color": "amber", "sub": "$270 (15%)"},
                                        {"label": "Fondo Imprevistos / Contingencia", "value": 10, "color": "gold", "sub": "$190 (10%)"}
                                    ]
                                }
                            )
                        ]
                    ),
                    OpenPageNode(
                        type="card",
                        props={"title": "Últimas Partidas Registradas", "badge": "VERIFICADO"},
                        children=[
                            OpenPageNode(
                                type="data_table",
                                props={
                                    "columns": ["Fecha", "Concepto", "Categoría", "Monto"],
                                    "rows": [
                                        ["15/09/2026", "Google Cloud / Gemini API", "IA Models", "$14.20"],
                                        ["14/09/2026", "Respaldo y Almacenamiento S3", "Infraestructura", "$35.00"],
                                        ["12/09/2026", "Conexión Fibra Simétrica", "Conectividad", "$85.00"],
                                        ["10/09/2026", "Licencia Cursor & Copilot", "Herramientas", "$40.00"]
                                    ]
                                }
                            )
                        ]
                    )
                ]
            )
        )

    elif name in ("tareas", "tactical", "tasks"):
        return OpenPageSchema(
            title="Matriz de Operaciones & Tareas Tácticas",
            subtitle="Plan de acción y objetivos prioritarios de Alberth",
            updated_at=now,
            root=OpenPageNode(
                type="stack",
                props={"gap": "14px"},
                children=[
                    OpenPageNode(
                        type="metrics_row",
                        children=[
                            OpenPageNode(type="metric", props={"label": "Tareas Totales", "value": "6", "unit": "ITEMS", "trend_type": "neutral"}),
                            OpenPageNode(type="metric", props={"label": "Completadas", "value": "4", "unit": "HECHAS", "trend": "66.7%", "trend_type": "positive"}),
                            OpenPageNode(type="metric", props={"label": "En Progreso", "value": "2", "unit": "ACTIVAS", "trend": "PRIORITARIO", "trend_type": "warn"}),
                        ]
                    ),
                    OpenPageNode(
                        type="card",
                        props={"title": "Lista de Verificación de Alberth", "badge": "HOY"},
                        children=[
                            OpenPageNode(
                                type="task_list",
                                props={
                                    "items": [
                                        {"text": "Integrar Gemini Multimodal Live API en tiempo real", "done": True, "tag": "COMPLETO"},
                                        {"text": "Conectar Echo Music y gestión multi-playlist de YouTube", "done": True, "tag": "COMPLETO"},
                                        {"text": "Instalar OpenDesign suite y contrato DESIGN.md", "done": True, "tag": "COMPLETO"},
                                        {"text": "Implementar motor declarativo OpenPage / A2UI", "done": True, "tag": "EN PROCESO"},
                                        {"text": "Migración de servidor maestro centralizado a MacBook Pro", "done": False, "tag": "PLANIFICADO"},
                                        {"text": "Auditoría de consistencia de tratos y memoria en Android", "done": False, "tag": "PRÓXIMO"}
                                    ]
                                }
                            )
                        ]
                    )
                ]
            )
        )

    # Preset por defecto (Dashboard de Bienvenida al Live Canvas)
    return OpenPageSchema(
        title="Alberth Quantum Live Canvas",
        subtitle="Entorno de visualización declarativo A2UI (OpenPage Protocol)",
        updated_at=now,
        root=OpenPageNode(
            type="stack",
            props={"gap": "12px"},
            children=[
                OpenPageNode(
                    type="alert_banner",
                    props={"level": "info", "title": "CANVAS CUÁNTICO ACTIVO", "text": "Este lienzo se actualiza de forma determinista mediante esquemas JSON sin riesgo de código roto."}
                ),
                OpenPageNode(
                    type="card",
                    props={"title": "Comandos de Demostración Visual", "badge": "INTERACTIVO"},
                    children=[
                        OpenPageNode(
                            type="text",
                            props={"text": "Puede pedirle a Alberth por voz o texto proyectar dashboards de telemetría, contabilidad o tareas tácticas.", "style": "body"}
                        ),
                        OpenPageNode(type="divider"),
                        OpenPageNode(
                            type="action_group",
                            children=[
                                OpenPageNode(type="button", props={"label": "📊 Telemetría de Sistema", "action": "load_preset", "action_arg": "system", "variant": "primary"}),
                                OpenPageNode(type="button", props={"label": "💰 Tablero Financiero", "action": "load_preset", "action_arg": "finance", "variant": "secondary"}),
                                OpenPageNode(type="button", props={"label": "📋 Tareas Tácticas", "action": "load_preset", "action_arg": "tasks", "variant": "secondary"}),
                            ]
                        )
                    ]
                )
            ]
        )
    )


# ─── Ejecución CLI para pruebas y exportación ─────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Alberth OpenPage Declarative Engine CLI")
    parser.add_argument("--preset", type=str, default="default", help="Nombre del preset: system, finance, tasks, default")
    parser.add_argument("--html", action="store_true", help="Imprimir el HTML compilado")
    parser.add_argument("--json", action="store_true", help="Imprimir el esquema JSON puro")
    args = parser.parse_args()

    preset_schema = get_openpage_preset(args.preset)
    
    if args.json:
        print(preset_schema.model_dump_json(indent=2))
    elif args.html:
        compiled = OpenPageCompiler.compile(preset_schema)
        print(compiled)
    else:
        print(f"✅ OpenPage Schema '{preset_schema.title}' generado correctamente.")
        print(f"   Nodos: {preset_schema.root.type} (Actualizado: {time.ctime(preset_schema.updated_at)})")
        print("   Use --json para ver el esquema o --html para ver la compilación.")
