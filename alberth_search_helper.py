#!/usr/bin/env python3
# =============================================================================
# ALBERTH SEARCH HELPER — Búsqueda Web Avanzada en Vivo (Deep Web Search)
#
# Capas integradas (100% Gratuitas, sin API Key):
# 1. DuckDuckGo Deep Web & News Search (vía duckduckgo_search / HTML)
# 2. Wikipedia API en Español (artículos y definiciones académicas)
# 3. Wttr.in (clima y pronóstico en tiempo real)
# 4. DuckDuckGo Instant Answers (respuestas directas)
#
# Uso: python3 alberth_search_helper.py "<consulta>"
# =============================================================================

from __future__ import annotations
import sys
import json
import urllib.request
import urllib.parse
import re
from typing import List, Dict, Any

def clean_query(query: str) -> str:
    """Elimina palabras activadoras para obtener una consulta limpia y directa."""
    q = query.lower()
    words = [
        "busca en internet", "busca en la web", "busca en google", "busca", "search",
        "investiga sobre", "investiga", "quién es", "quien es", "qué es", "que es",
        "qué son", "que son", "dime sobre", "háblame de", "hablame de", "noticias de",
        "información de", "informacion de", "últimas noticias sobre", "ultimas noticias de"
    ]
    for w in words:
        q = q.replace(w, "")
    return q.strip()


def get_weather(city: str) -> str:
    """Obtiene el clima en tiempo real desde wttr.in."""
    try:
        encoded_city = urllib.parse.quote_plus(city)
        url = f"https://wttr.in/{encoded_city}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "AlberthAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            return response.read().decode("utf-8").strip()
    except Exception as e:
        return f"Clima no disponible temporalmente ({e})."


def search_wikipedia(query: str) -> List[Dict[str, str]]:
    """Busca en Wikipedia en español para conceptos, biografías o definiciones."""
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
        req = urllib.request.Request(search_url, headers={"User-Agent": "AlberthAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            search_list = data.get("query", {}).get("search", [])

        if search_list:
            title = search_list[0]["title"]
            encoded_title = urllib.parse.quote(title)
            extract_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={encoded_title}&format=json"
            req_extract = urllib.request.Request(extract_url, headers={"User-Agent": "AlberthAssistant/1.0"})
            with urllib.request.urlopen(req_extract, timeout=4) as response_extract:
                data_extract = json.loads(response_extract.read().decode("utf-8"))
                pages = data_extract.get("query", {}).get("pages", {})
                for page_id in pages:
                    extract = pages[page_id].get("extract", "")
                    if extract:
                        results.append({
                            "title": title,
                            "snippet": extract[:350] + ("..." if len(extract) > 350 else ""),
                            "url": f"https://es.wikipedia.org/wiki/{encoded_title}",
                            "source": "Wikipedia"
                        })
    except Exception:
        pass
    return results


def search_duckduckgo_live(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Búsqueda web en vivo usando la librería duckduckgo_search (100% gratuita)."""
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, region="wt-wt", max_results=max_results))
            for item in raw_results:
                title = item.get("title", "")
                body = item.get("body", "")
                href = item.get("href", "")
                if body:
                    results.append({
                        "title": title,
                        "snippet": body,
                        "url": href,
                        "source": "DuckDuckGo Web"
                    })
    except Exception as e:
        # Fallback a DuckDuckGo Instant Answers API
        try:
            encoded = urllib.parse.quote(query)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "")
                if abstract:
                    results.append({
                        "title": data.get("Heading", query),
                        "snippet": abstract,
                        "url": data.get("AbstractURL", ""),
                        "source": "DuckDuckGo Instant"
                    })
        except Exception:
            pass
    return results


def deep_search(query: str) -> Dict[str, Any]:
    """Orquesta la búsqueda en múltiples fuentes y genera un informe estructurado."""
    query_lower = query.lower()

    # 1. Caso especial: Clima / Tiempo
    if any(k in query_lower for k in ["clima", "tiempo", "temperatura", "frío", "calor", "llover", "lluvia"]):
        match = re.search(r'\b(?:en|de|para|clima)\s+([a-zA-Z\s]+)', query, re.IGNORECASE)
        city = match.group(1).strip() if match else "Madrid"
        for word in ["clima", "tiempo", "hoy", "temperatura"]:
            city = city.replace(word, "").strip()
        if not city:
            city = "Madrid"
        weather_info = get_weather(city)
        return {
            "tipo": "clima",
            "exito": True,
            "resultado": f"Pronóstico del clima en {city.title()}: {weather_info}",
            "fuente": "wttr.in"
        }

    # 2. Búsqueda web general
    cleaned = clean_query(query)
    if not cleaned:
        cleaned = query

    all_results: List[Dict[str, str]] = []

    # A. Búsqueda en vivo DuckDuckGo
    live_results = search_duckduckgo_live(cleaned, max_results=3)
    if live_results:
        all_results.extend(live_results)

    # B. Si hay pocos resultados o es conceptual, consultar Wikipedia
    if len(all_results) < 2:
        wiki_res = search_wikipedia(cleaned)
        if wiki_res:
            all_results.extend(wiki_res)

    if not all_results:
        return {
            "tipo": "busqueda",
            "exito": False,
            "resultado": f"No se encontraron resultados recientes en internet para: '{cleaned}'.",
            "fuentes": []
        }

    # Formatear salida estructurada para el prompt de Alberth
    lines = [f"Resultados web actualizados para '{cleaned}':"]
    for idx, r in enumerate(all_results[:3], 1):
        lines.append(f"{idx}. [{r['source']}] {r['title']}: {r['snippet']}")
        if r.get("url"):
            lines.append(f"   Enlace: {r['url']}")

    return {
        "tipo": "busqueda",
        "exito": True,
        "query": cleaned,
        "resultado": "\n".join(lines),
        "fuentes": all_results[:3]
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta consulta de búsqueda"}))
        sys.exit(1)

    q = " ".join(sys.argv[1:])
    res = deep_search(q)
    print(json.dumps(res, ensure_ascii=False, indent=2))
