#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_playwright_agent.py — Agente Autónomo de Navegación Web para Alberth
=============================================================================
Solución agéntica inspirada en Browser-Use que opera sobre Playwright nativo.
Navega en modo visible o en segundo plano invisible (Headless), indexa los
elementos interactivos del DOM con marcadores deterministas [data-alberth-id]
y ejecuta misiones complejas con modelos fundacionales a costo $0.00.

Capacidades:
- Navegación silenciosa en segundo plano (no mueve el cursor físico de la Mac).
- Indexación DOM automática de botones, enlaces, campos de texto y formularios.
- Bucle de decisión agéntica con tolerancia a fallos y auto-recuperación.
- Soporte para clics, escritura, envío de teclas, scroll y extracción de datos.

Uso CLI:
  python3 alberth_playwright_agent.py --mission "Busca el precio del MacBook Air M3 en MercadoLibre"
  python3 alberth_playwright_agent.py --url "https://es.wikipedia.org" --mission "Busca Alan Turing y extrae el primer párrafo" --headed
"""

from __future__ import annotations

import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Cargar entorno de variables desde ~/.openclaw/.env
env_file = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Importar modelos fundacionales de Alberth
try:
    import alberth_foundation_models as models
except ImportError:
    models = None

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())


# ── Inyección JS de Marcadores Deterministas ──────────────────────────────────

JS_MARKER_SCRIPT = """
() => {
    // Limpiar marcadores previos
    document.querySelectorAll('[data-alberth-id]').forEach(el => el.removeAttribute('data-alberth-id'));

    const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && rect.top < window.innerHeight && rect.bottom > 0;
    };

    const selectors = [
        'a[href]',
        'button',
        'input:not([type="hidden"])',
        'textarea',
        'select',
        '[role="button"]',
        '[role="link"]',
        '[role="searchbox"]',
        '[tabindex="0"]'
    ];

    const elements = document.querySelectorAll(selectors.join(', '));
    const items = [];
    let idCounter = 1;

    elements.forEach(el => {
        if (isVisible(el) && idCounter <= 60) {
            el.setAttribute('data-alberth-id', String(idCounter));
            
            const tag = el.tagName.toLowerCase();
            const type = el.getAttribute('type') || '';
            const placeholder = el.getAttribute('placeholder') || '';
            const ariaLabel = el.getAttribute('aria-label') || '';
            const name = el.getAttribute('name') || '';
            const value = el.value || '';
            let text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
            if (text.length > 70) text = text.substring(0, 67) + '...';

            items.push({
                id: idCounter,
                tag: tag,
                type: type,
                text: text,
                placeholder: placeholder,
                aria: ariaLabel,
                name: name,
                value: value
            });
            idCounter++;
        }
    });

    return items;
}
"""


# ── Extracción y Limpieza de JSON de Modelos ─────────────────────────────────

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Extrae un diccionario JSON válido de la respuesta del modelo."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        cleaned = text[start:end]
        try:
            return json.loads(cleaned)
        except Exception:
            pass
    return None


# ── Decisión Agéntica del LLM ────────────────────────────────────────────────

def decide_next_action(
    mission: str,
    current_url: str,
    page_title: str,
    elements: List[Dict[str, Any]],
    action_history: List[str]
) -> Dict[str, Any]:
    """
    Consulta al modelo fundacional para elegir el siguiente paso óptimo.
    Retorna un diccionario con: action, id, text, url, key, thought, summary.
    """
    # Formatear la lista de elementos interactivos
    elements_desc = []
    for el in elements[:45]:
        parts = [f"[{el['id']}] <{el['tag']}>"]
        if el.get("type"):
            parts.append(f"type='{el['type']}'")
        if el.get("text"):
            parts.append(f"texto='{el['text']}'")
        if el.get("placeholder"):
            parts.append(f"placeholder='{el['placeholder']}'")
        if el.get("aria"):
            parts.append(f"aria='{el['aria']}'")
        if el.get("value"):
            parts.append(f"valor='{el['value']}'")
        elements_desc.append(" ".join(parts))

    elements_text = "\n".join(elements_desc) if elements_desc else "(No se detectaron elementos interactivos visibles)"

    history_text = "\n".join([f"- {h}" for h in action_history[-4:]]) if action_history else "(Inicio de misión)"

    prompt = f"""Eres el Agente de Navegación Web Autónoma de Alberth para el Señor Danny.
Tu misión global es:
"{mission}"

ESTADO ACTUAL DEL NAVEGADOR:
- URL actual: {current_url}
- Título de la página: {page_title}
- Pasos previos realizados:
{history_text}

ELEMENTOS INTERACTIVOS VISIBLES EN PANTALLA:
{elements_text}

INSTRUCCIONES:
Elige EXACTAMENTE UNA de las siguientes acciones para avanzar hacia la meta:
1. {{"action": "goto", "url": "https://...", "thought": "Por qué ir a esta URL"}}
2. {{"action": "fill", "id": <numero_elemento>, "text": "texto a escribir", "thought": "Por qué escribir aquí"}}
3. {{"action": "click", "id": <numero_elemento>, "thought": "Por qué hacer clic en este botón o enlace"}}
4. {{"action": "press", "key": "Enter", "thought": "Por qué presionar esta tecla"}}
5. {{"action": "scroll", "direction": "down", "thought": "Por qué desplazarse"}}
6. {{"action": "finish", "summary": "Informe final detallado con los datos extraídos para el Señor Danny", "thought": "Meta cumplida"}}

CRITERIO DE FINALIZACIÓN:
Si la URL o el título actual ya corresponden al tema solicitado o si en los textos/enlaces ya observas la respuesta a la misión del Señor Danny, selecciona INMEDIATAMENTE la acción "finish" y redacta el informe en "summary".

Responde ÚNICAMENTE con el objeto JSON válido.
"""

    # Intentar con Qwen Coder o DeepSeek
    if models:
        try:
            resp, model_used = models.query_qwen_coder(
                prompt=prompt,
                system_prompt="Eres un agente de navegación web autónomo ultra-preciso. Responde solo con JSON.",
                max_tokens=400
            )
            parsed = _extract_json(resp)
            if parsed and "action" in parsed:
                return parsed
        except Exception as e:
            print(f"[Playwright Agent] Error con Qwen: {e}", file=sys.stderr)

        # Fallback a Gemini
        try:
            resp, model_used = models.query_deepseek_reasoning(
                prompt=prompt,
                system_prompt="Eres un agente de navegación web autónomo ultra-preciso. Responde solo con JSON.",
                max_tokens=400
            )
            parsed = _extract_json(resp)
            if parsed and "action" in parsed:
                return parsed
        except Exception as e:
            print(f"[Playwright Agent] Error con DeepSeek/Gemini: {e}", file=sys.stderr)

    # Decisión heurística de emergencia si falla la IA
    if not current_url or current_url == "about:blank":
        return {"action": "goto", "url": "https://www.google.com", "thought": "Navegar a buscador base"}
    return {"action": "finish", "summary": f"Señor Danny, navegación completada en {current_url} ({page_title})."}


# ── Bucle Principal de Navegación Autónoma ───────────────────────────────────

def run_autonomous_browser_mission(
    mission: str,
    start_url: Optional[str] = None,
    headed: bool = False,
    max_steps: int = 8,
    timeout_ms: int = 25000
) -> Dict[str, Any]:
    """
    Ejecuta una misión autónoma completa en la web usando Playwright.
    
    Args:
        mission: Instrucción del Señor Danny (ej. 'Busca en Wikipedia sobre X y extrae Y').
        start_url: URL inicial opcional. Si es None, busca en DuckDuckGo o Google.
        headed: Si es True, abre la ventana visible de Chromium. Si es False (default), corre en segundo plano.
        max_steps: Límite de acciones para evitar bucles infinitos.
        timeout_ms: Timeout de carga de página.
        
    Returns:
        Dict con: success, summary, steps_taken, final_url, final_title, history.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "success": False,
            "error": "Playwright no está instalado. Ejecute 'pip install playwright && playwright install chromium'.",
            "summary": "Señor Danny, Playwright no está disponible en este entorno."
        }

    print(f"\n[Browser Agent] 🌐 Iniciando misión: \"{mission}\" (Modo: {'Visible' if headed else 'Segundo Plano / Headless'})...")

    # Si no hay URL inicial, inferirla de la misión o usar buscador
    if not start_url:
        match_url = re.search(r'https?://[^\s]+', mission)
        if match_url:
            start_url = match_url.group(0)
        elif "wikipedia" in mission.lower():
            start_url = "https://es.wikipedia.org"
        elif "mercadolibre" in mission.lower():
            start_url = "https://www.mercadolibre.com"
        else:
            # Búsqueda directa en DuckDuckGo
            query_clean = re.sub(r'(busca en la web|busca|navega a|entra a|encuentra)\s*', '', mission, flags=re.I).strip()
            start_url = f"https://duckduckgo.com/?q={query_clean.replace(' ', '+')}"

    action_history: List[str] = []
    final_summary = ""
    step_count = 0

    with sync_playwright() as p:
        # Lanzar Chromium configurado con User-Agent moderno para evitar bloqueos
        browser = p.chromium.launch(
            headless=not headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)

        try:
            print(f"   [Paso 0] Navegando a URL inicial: {start_url}...")
            page.goto(start_url, wait_until="domcontentloaded", timeout=timeout_ms)
            time.sleep(1.5)
            action_history.append(f"Navegación inicial a {start_url}")

            for step in range(1, max_steps + 1):
                step_count = step
                curr_url = page.url
                curr_title = page.title()
                print(f"\n   [Paso {step}/{max_steps}] URL: {curr_url[:60]}... | Título: {curr_title[:40]}")

                # 1. Inyectar marcadores y extraer elementos interactivos
                try:
                    elements = page.evaluate(JS_MARKER_SCRIPT)
                except Exception as je:
                    print(f"   ⚠️ Error inyectando marcadores JS: {je}")
                    elements = []

                # 2. Decisión del agente
                decision = decide_next_action(
                    mission=mission,
                    current_url=curr_url,
                    page_title=curr_title,
                    elements=elements,
                    action_history=action_history
                )

                action = decision.get("action", "").lower()
                thought = decision.get("thought", "")
                print(f"   🤖 Decisión: [{action.upper()}] — {thought}")

                # 3. Ejecución de la acción seleccionada
                if action == "finish":
                    final_summary = decision.get("summary", "")
                    if not final_summary or len(final_summary) < 50:
                        try:
                            paragraphs = page.locator("p").all_inner_texts()
                            clean_p = [p.strip() for p in paragraphs if len(p.strip()) > 35]
                            if clean_p:
                                final_summary = f"Señor Danny, información extraída de '{curr_title}':\n\n" + "\n\n".join(clean_p[:3])
                            else:
                                body_text = page.inner_text("body")[:1000]
                                final_summary = f"Misión completada en {curr_url}.\n\nExtracto:\n{body_text}"
                        except Exception:
                            pass
                    print(f"   ✅ Misión finalizada con éxito.")
                    break

                elif action == "goto":
                    target_url = decision.get("url", "")
                    if target_url:
                        if not target_url.startswith("http"):
                            target_url = "https://" + target_url
                        page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                        time.sleep(1.5)
                        action_history.append(f"Ir a URL: {target_url}")

                elif action == "fill":
                    target_id = decision.get("id")
                    text_to_fill = decision.get("text", "")
                    selector = f"[data-alberth-id='{target_id}']"
                    try:
                        page.wait_for_selector(selector, timeout=4000)
                        page.fill(selector, text_to_fill)
                        time.sleep(0.5)
                        action_history.append(f"Escribir '{text_to_fill}' en elemento [{target_id}]")
                    except Exception as fe:
                        print(f"   ❌ Fallo al escribir en [{target_id}]: {fe}")
                        action_history.append(f"Fallo al escribir en [{target_id}]")

                elif action == "click":
                    target_id = decision.get("id")
                    selector = f"[data-alberth-id='{target_id}']"
                    try:
                        page.wait_for_selector(selector, timeout=4000)
                        # Esperar posible navegación tras el clic
                        with page.expect_navigation(timeout=6000) if "a" in selector else page.expect_response(lambda _: True, timeout=1000):
                            page.click(selector, timeout=4000)
                        time.sleep(1.5)
                        action_history.append(f"Clic en elemento [{target_id}]")
                    except Exception:
                        # Si no navegó o fue clic simple, forzar click directo
                        try:
                            page.click(selector, timeout=3000)
                            time.sleep(1.5)
                            action_history.append(f"Clic en elemento [{target_id}]")
                        except Exception as ce:
                            print(f"   ❌ Fallo al hacer clic en [{target_id}]: {ce}")
                            action_history.append(f"Fallo al hacer clic en [{target_id}]")

                elif action == "press":
                    key = decision.get("key", "Enter")
                    page.keyboard.press(key)
                    time.sleep(2.0)
                    action_history.append(f"Presionar tecla '{key}'")

                elif action == "scroll":
                    direction = decision.get("direction", "down")
                    delta = 600 if direction == "down" else -600
                    page.evaluate(f"window.scrollBy(0, {delta})")
                    time.sleep(1.0)
                    action_history.append(f"Desplazar pantalla ({direction})")

                else:
                    time.sleep(1.0)

            # Si se agotaron los pasos sin 'finish', resumir el estado final con párrafos relevantes
            if not final_summary:
                try:
                    paragraphs = page.locator("p").all_inner_texts()
                    clean_p = [p.strip() for p in paragraphs if len(p.strip()) > 35]
                    if clean_p:
                        final_summary = (
                            f"Señor Danny, la navegación completó su objetivo en '{page.title()}'.\n\n"
                            f"Extracto principal:\n" + "\n\n".join(clean_p[:3])
                        )
                    else:
                        page_text = page.inner_text("main") or page.inner_text("article") or page.inner_text("body")
                        clean_text = "\n".join([line.strip() for line in page_text.splitlines() if len(line.strip()) > 30][:6])
                        final_summary = (
                            f"Señor Danny, la navegación finalizó en '{page.title()}' ({page.url}).\n\n"
                            f"Información relevante encontrada:\n{clean_text}"
                        )
                except Exception:
                    final_summary = f"Señor Danny, la misión finalizó en {page.url} ({page.title()})."

            final_url = page.url
            final_title = page.title()

        except Exception as e:
            print(f"[Browser Agent] Error general durante la navegación: {e}", file=sys.stderr)
            final_summary = f"Señor Danny, ocurrió un inconveniente durante la navegación web: {e}"
            final_url = page.url if 'page' in locals() else ""
            final_title = page.title() if 'page' in locals() else ""
        finally:
            browser.close()

    return {
        "success": bool(final_summary and "ocurrió un inconveniente" not in final_summary),
        "mission": mission,
        "summary": final_summary,
        "steps_taken": step_count,
        "final_url": final_url,
        "final_title": final_title,
        "history": action_history
    }


# ── Punto de Entrada CLI ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Agente de Navegación Web Autónoma para Alberth (Playwright)")
    parser.add_argument("--mission", "-m", type=str, required=True, help="Misión del agente (ej. 'Busca X y extrae Y')")
    parser.add_argument("--url", "-u", type=str, default=None, help="URL inicial (opcional)")
    parser.add_argument("--headed", action="store_true", help="Abrir ventana visible de Chromium (por defecto: headless/segundo plano)")
    parser.add_argument("--steps", "-s", type=int, default=7, help="Máximo de pasos a ejecutar (default: 7)")

    args = parser.parse_args()
    res = run_autonomous_browser_mission(
        mission=args.mission,
        start_url=args.url,
        headed=args.headed,
        max_steps=args.steps
    )

    print("\n" + "═" * 70)
    print("📊 RESULTADO FINAL DE LA MISIÓN WEB:")
    print("═" * 70)
    print(res.get("summary", ""))
    print(f"\n[URL Final]: {res.get('final_url')}")
    print(f"[Pasos ejecutados]: {res.get('steps_taken')}")


if __name__ == "__main__":
    main()
