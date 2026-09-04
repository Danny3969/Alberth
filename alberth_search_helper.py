#!/usr/bin/env python3
# =============================================================================
# ALBERTH SEARCH HELPER — Módulo de Búsqueda y Consultas en Internet
# Combina DuckDuckGo API, Wikipedia y wttr.in para clima/tiempo.
# Uso: python3 alberth_search_helper.py "<consulta>"
# =============================================================================

import sys
import json
import urllib.request
import urllib.parse
import re

def clean_query(query: str) -> str:
    """Elimina palabras vacías comunes para centrarse en la búsqueda."""
    query_lower = query.lower()
    # Eliminar activadores
    words_to_remove = [
        "busca en internet", "busca en la web", "busca", "search", "investiga",
        "quién es", "quien es", "qué es", "que es", "qué son", "que son",
        "dime sobre", "háblame de", "hablame de", "información de", "informacion de"
    ]
    cleaned = query_lower
    for word in words_to_remove:
        cleaned = cleaned.replace(word, "")
    return cleaned.strip()

def get_weather(city: str) -> str:
    """Obtiene el clima de wttr.in."""
    try:
        encoded_city = urllib.parse.quote_plus(city)
        url = f"https://wttr.in/{encoded_city}?format=3"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode("utf-8").strip()
    except Exception as e:
        return f"Error al consultar el clima: {e}"

def search_wikipedia(query: str) -> list:
    """Busca en Wikipedia en español."""
    results = []
    try:
        # 1. Buscar títulos de artículos
        encoded_query = urllib.parse.quote(query)
        search_url = f"https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_query}&format=json"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            search_list = data.get("query", {}).get("search", [])
            
        # 2. Obtener extracto del artículo más relevante
        if search_list:
            title = search_list[0]["title"]
            encoded_title = urllib.parse.quote(title)
            extract_url = f"https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={encoded_title}&format=json"
            
            req_extract = urllib.request.Request(extract_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_extract, timeout=5) as response_extract:
                data_extract = json.loads(response_extract.read().decode("utf-8"))
                pages = data_extract.get("query", {}).get("pages", {})
                for page_id in pages:
                    extract = pages[page_id].get("extract", "")
                    if extract:
                        results.append({
                            "title": title,
                            "snippet": extract[:400] + ("..." if len(extract) > 400 else ""),
                            "source": "Wikipedia"
                        })
    except Exception:
        pass
    return results

def search_duckduckgo(query: str) -> list:
    """Busca en DuckDuckGo Instant Answers API."""
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            
            # Abstract
            abstract = data.get("AbstractText", "")
            if abstract:
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": abstract,
                    "source": "DuckDuckGo (Abstract)"
                })
                
            # Related Topics
            related = data.get("RelatedTopics", [])
            for item in related[:3]:
                if "Text" in item and "FirstURL" in item:
                    results.append({
                        "title": item.get("Result", "").split("<a")[0] or query,
                        "snippet": item["Text"],
                        "source": "DuckDuckGo"
                    })
    except Exception:
        pass
    return results

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta la consulta de búsqueda"}, ensure_ascii=False))
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    query_lower = query.lower()
    
    # 1. Determinar si es consulta de clima
    if any(k in query_lower for k in ["clima", "tiempo", "temperatura", "frío", "calor", "llover", "lluvia"]):
        # Intentar extraer la ciudad
        match = re.search(r'\b(?:en|de|para|clima)\s+([a-zA-Z\s]+)', query, re.IGNORECASE)
        city = match.group(1).strip() if match else "Bogota"
        # Limpiar palabras extras
        city = city.replace("clima", "").replace("tiempo", "").strip()
        if not city:
            city = "Bogota"
        weather_info = get_weather(city)
        print(json.dumps({
            "tipo": "clima",
            "resultado": f"Información del clima en tiempo real:\n• {weather_info}",
            "exito": True
        }, ensure_ascii=False, indent=2))
        sys.exit(0)
        
    # 2. Consultas generales en Internet
    cleaned = clean_query(query)
    facts = []
    
    # Intentar Wikipedia
    wiki_res = search_wikipedia(cleaned)
    if wiki_res:
        facts.extend(wiki_res)
        
    # Intentar DuckDuckGo
    ddg_res = search_duckduckgo(cleaned)
    if ddg_res:
        facts.extend(ddg_res)
        
    if facts:
        # Filtrar duplicados o formatear en lista legible
        formatted_results = []
        seen_snippets = set()
        for f in facts:
            snippet_cleaned = f["snippet"].strip().lower()
            if snippet_cleaned not in seen_snippets:
                seen_snippets.add(snippet_cleaned)
                formatted_results.append(f)
                
        resultado_str = "Resultados de búsqueda en Internet:\n" + "\n".join(
            f"• [{f['source']}] {f['title']}: {f['snippet']}" for f in formatted_results[:3]
        )
        print(json.dumps({
            "tipo": "busqueda",
            "resultado": resultado_str,
            "exito": True
        }, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({
            "tipo": "busqueda",
            "resultado": f"No se encontraron resultados web relevantes para: '{cleaned}'.",
            "exito": False
        }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
