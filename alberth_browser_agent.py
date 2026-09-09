#!/usr/bin/env python3
# =============================================================================
# ALBERTH BROWSER AGENT — Lector y Extractor Web Limpio (Web Reader)
#
# 100% Gratuito y sin dependencias cloud:
#   - Descarga cualquier URL web superando bloqueos básicos de User-Agent.
#   - Limpia anuncios, trackers, menús y popups con BeautifulSoup.
#   - Extrae el cuerpo del artículo y texto legible formateado en Markdown.
#   - Permite a Alberth "leer" y resumir páginas web completas al usuario.
#
# Uso: python3 alberth_browser_agent.py "<url>" [--max-chars 2500]
# =============================================================================

from __future__ import annotations
import sys
import os
import json
import urllib.request
import urllib.error
import re
from bs4 import BeautifulSoup
from typing import Dict, Any


USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]


def extract_web_content(url: str, max_chars: int = 3000) -> Dict[str, Any]:
    """Descarga una URL y extrae su texto limpio y metadatos."""
    # Asegurar esquema https si no está presente
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENTS[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as e:
        return {
            "exito": False,
            "url": url,
            "error": f"No se pudo acceder a la página ({e})"
        }

    # Procesar con BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Extraer título
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("h1"):
        title = soup.find("h1").get_text().strip()

    # Extraer meta descripción si existe
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    # Eliminar elementos no informativos (scripts, estilos, banners, footer, nav)
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form"]):
        element.decompose()

    # Buscar el contenedor principal del artículo
    article_body = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r'(content|article|entry|post)', re.I)) or soup.body

    if not article_body:
        article_body = soup

    # Extraer párrafos y encabezados estructurados
    paragraphs = []
    for p in article_body.find_all(["h1", "h2", "h3", "p", "li"]):
        txt = p.get_text().strip()
        # Filtrar textos vacíos o frases de cookies
        if len(txt) > 20 and not re.search(r'(cookie|privacidad|términos|todos los derechos reservados|iniciar sesión)', txt, re.I):
            paragraphs.append(txt)

    full_text = "\n\n".join(paragraphs)
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + f"\n\n[... Contenido truncado a {max_chars} caracteres para mayor agilidad ...]"

    return {
        "exito": True,
        "url": url,
        "titulo": title or "Sin título",
        "descripcion": meta_desc,
        "contenido": full_text,
        "caracteres": len(full_text)
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta URL para leer"}))
        sys.exit(1)

    target_url = sys.argv[1]
    res = extract_web_content(target_url)
    print(json.dumps(res, ensure_ascii=False, indent=2))
