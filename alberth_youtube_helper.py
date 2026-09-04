# /// script
# dependencies = []
# ///

import sys
import urllib.request
import urllib.parse
import re
import subprocess

def clean_query(query):
    # Remove trigger words
    q = query.lower()
    q = re.sub(r'\b(abre|busca|busca en youtube|pon el video|reproduce|video de|en youtube|de|el|la|youtube)\b', ' ', q)
    # Remove extra spaces
    q = " ".join(q.split())
    return q

def search_youtube(query):
    cleaned = clean_query(query)
    if not cleaned:
        cleaned = "musica para programar"
        
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(cleaned)}"
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            
        # Try to find videoIds in ytInitialData JSON
        video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html)
        if not video_ids:
            # Fallback to general href regex
            video_ids = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', html)
            
        if video_ids:
            # Return first video id
            return video_ids[0], cleaned, None
            
        return None, cleaned, "No se encontraron videos específicos."
    except Exception as e:
        return None, cleaned, f"Error de red/búsqueda: {str(e)}"

def main():
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    if not query:
        print("ERROR: No se especificó término de búsqueda.")
        sys.exit(1)
        
    video_id, cleaned_term, error = search_youtube(query)
    
    if video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"TERMINO_BUSQUEDA: {cleaned_term}")
        print(f"VIDEO_ID: {video_id}")
        print(f"URL: {video_url}")
        print(f"ACCION: Abriendo primer video coincidente...")
        
        # Open in default macOS browser
        subprocess.run(["open", video_url])
        sys.exit(0)
    else:
        # Fallback to opening search results
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(cleaned_term)}"
        print(f"TERMINO_BUSQUEDA: {cleaned_term}")
        print(f"ACCION: Abriendo página de resultados (fallback: {error})...")
        subprocess.run(["open", search_url])
        sys.exit(0)

if __name__ == "__main__":
    main()
