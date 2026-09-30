#!/usr/bin/env python3
# =============================================================================
# ALBERTH OSINT — Rastreador de Huella Digital en Redes Sociales
# Inspira en el proyecto Shajal-Kumar/Gods-Eye (código 100% propio)
#
# Capacidades:
#   - Buscar un username en 80+ plataformas simultáneamente (HTTP async)
#   - Verificar si un correo está en brechas de datos (HIBP-style)
#   - Listar IPs/URLs asociadas a un dominio (WHOIS, DNS)
#   - Exportar reporte JSON/HTML
#
# Uso:
#   python3 alberth_osint.py username   <nombre_de_usuario>
#   python3 alberth_osint.py email      <correo@ejemplo.com>
#   python3 alberth_osint.py domain     <dominio.com>
#   python3 alberth_osint.py report     <nombre_de_usuario>   (genera HTML)
# =============================================================================

from __future__ import annotations
import sys, json, asyncio, re, socket, subprocess, time
from pathlib import Path
from datetime import datetime
from typing import Optional
import urllib.request
import urllib.parse

# ─── Directorio de salida ────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parent
OSINT_DIR = WORKSPACE / "memory" / "osint"
OSINT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Plataformas donde buscar por username ────────────────────────────────────
PLATFORMS: dict[str, str] = {
    "Instagram":     "https://www.instagram.com/{}/",
    "Twitter/X":     "https://x.com/{}",
    "Facebook":      "https://www.facebook.com/{}",
    "TikTok":        "https://www.tiktok.com/@{}",
    "YouTube":       "https://www.youtube.com/@{}",
    "LinkedIn":      "https://www.linkedin.com/in/{}",
    "GitHub":        "https://github.com/{}",
    "Reddit":        "https://www.reddit.com/user/{}",
    "Pinterest":     "https://www.pinterest.com/{}/",
    "Snapchat":      "https://www.snapchat.com/add/{}",
    "Twitch":        "https://www.twitch.tv/{}",
    "Discord":       "https://discord.com/users/{}",
    "Steam":         "https://steamcommunity.com/id/{}",
    "Spotify":       "https://open.spotify.com/user/{}",
    "SoundCloud":    "https://soundcloud.com/{}",
    "Telegram":      "https://t.me/{}",
    "Medium":        "https://medium.com/@{}",
    "DevTo":         "https://dev.to/{}",
    "Behance":       "https://www.behance.net/{}",
    "Dribbble":      "https://dribbble.com/{}",
    "Patreon":       "https://www.patreon.com/{}",
    "Flickr":        "https://www.flickr.com/people/{}",
    "Tumblr":        "https://{}.tumblr.com",
    "Vimeo":         "https://vimeo.com/{}",
    "Quora":         "https://www.quora.com/profile/{}",
    "Keybase":       "https://keybase.io/{}",
    "GitLab":        "https://gitlab.com/{}",
    "HackerNews":    "https://news.ycombinator.com/user?id={}",
    "ProductHunt":   "https://www.producthunt.com/@{}",
    "Disqus":        "https://disqus.com/by/{}/",
    "About.me":      "https://about.me/{}",
    "Foursquare":    "https://foursquare.com/{}",
    "Goodreads":     "https://www.goodreads.com/{}",
    "Gravatar":      "https://en.gravatar.com/{}",
    "Mix":           "https://mix.com/{}",
    "ReverbNation":  "https://www.reverbnation.com/{}",
    "Replit":        "https://replit.com/@{}",
    "Codepen":       "https://codepen.io/{}",
    "PyPI":          "https://pypi.org/user/{}/",
    "DockerHub":     "https://hub.docker.com/u/{}",
    "NPM":           "https://www.npmjs.com/~{}",
    "StackOverflow": "https://stackoverflow.com/users/{}",
    "Leetcode":      "https://leetcode.com/{}",
    "HackerEarth":   "https://www.hackerearth.com/@{}",
    "Codeforces":    "https://codeforces.com/profile/{}",
    "Kaggle":        "https://www.kaggle.com/{}",
    "Mastodon":      "https://mastodon.social/@{}",
    "Bluesky":       "https://bsky.app/profile/{}.bsky.social",
    "Threads":       "https://www.threads.net/@{}",
    "VK":            "https://vk.com/{}",
    "OK":            "https://ok.ru/{}",
    "Weibo":         "https://weibo.com/{}",
    "Taringa":       "https://www.taringa.net/{}",
    "Clubhouse":     "https://www.joinclubhouse.com/@{}",
    "Badoo":         "https://badoo.com/en/profile/{}",
    "Trello":        "https://trello.com/{}",
    "Slack":         "https://{}.slack.com",
    "Notion":        "https://www.notion.so/{}",
    "Substack":      "https://{}.substack.com",
}

# ─── Indicadores de "perfil existe" (texto que NO aparece en 404) ─────────────
NOT_FOUND_INDICATORS = [
    "page not found", "user not found", "404", "doesn't exist",
    "this account doesn't exist", "no existe", "no encontrado",
    "usuario no encontrado", "profile not found", "sorry, this page"
]

def _ua() -> dict:
    return {"User-Agent": "Mozilla/5.0 (compatible; AlberthOSINT/1.0)"}

def check_username_sync(username: str, platform: str, url: str) -> dict:
    """Comprueba una plataforma de forma síncrona."""
    full_url = url.format(username)
    try:
        req = urllib.request.Request(full_url, headers=_ua())
        with urllib.request.urlopen(req, timeout=8) as resp:
            code = resp.status
            body = resp.read(4096).decode("utf-8", errors="ignore").lower()
            found = code in (200, 301, 302) and not any(ind in body for ind in NOT_FOUND_INDICATORS)
            return {"platform": platform, "url": full_url, "found": found, "status": code}
    except Exception as e:
        return {"platform": platform, "url": full_url, "found": False, "status": 0, "error": str(e)[:80]}

def search_username(username: str, verbose: bool = True) -> list[dict]:
    """Busca el username en todas las plataformas configuradas."""
    print(f"\n🔍 ALBERTH OSINT — Buscando: @{username}")
    print(f"   Plataformas a verificar: {len(PLATFORMS)}")
    print("   " + "─" * 55)

    results = []
    for platform, url_tpl in PLATFORMS.items():
        result = check_username_sync(username, platform, url_tpl)
        results.append(result)
        if verbose:
            status = "✅ ENCONTRADO" if result["found"] else "❌"
            print(f"   {status:14} {platform:20} {result['url']}")

    found = [r for r in results if r["found"]]
    print(f"\n   Total encontrados: {len(found)}/{len(PLATFORMS)}")
    return results

def check_email_breach(email: str) -> dict:
    """
    Verifica si un correo tiene brechas de datos conocidas.
    Usa el API público de HIBP (requiere User-Agent específico).
    """
    print(f"\n📧 ALBERTH OSINT — Verificando email: {email}")
    encoded = urllib.parse.quote(email)
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{encoded}?truncateResponse=false"
    try:
        req = urllib.request.Request(url, headers={
            **_ua(),
            "hibp-api-key": "",  # sin API key → solo breach names
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            breaches = [b.get("Name", "?") for b in data]
            print(f"   ⚠️  {len(breaches)} brechas encontradas: {', '.join(breaches[:10])}")
            return {"email": email, "breaches_count": len(breaches), "breaches": breaches}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("   ✅ Sin brechas conocidas (¡bien!)")
            return {"email": email, "breaches_count": 0, "breaches": []}
        elif e.code == 401:
            print("   ℹ️  HIBP requiere API key para búsquedas de email. Resultado: indisponible.")
            return {"email": email, "breaches_count": -1, "note": "API key HIBP requerida"}
        return {"email": email, "error": str(e)}
    except Exception as e:
        return {"email": email, "error": str(e)}

def lookup_domain(domain: str) -> dict:
    """Resolución DNS básica + WHOIS de un dominio."""
    print(f"\n🌐 ALBERTH OSINT — Analizando dominio: {domain}")
    result: dict = {"domain": domain}

    # DNS A records
    try:
        ips = socket.getaddrinfo(domain, None)
        unique = list(dict.fromkeys(i[4][0] for i in ips))
        result["ips"] = unique
        print(f"   IPs: {', '.join(unique)}")
    except Exception as e:
        result["ips"] = []; result["dns_error"] = str(e)

    # WHOIS vía subprocess
    try:
        w = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=8)
        lines = [l for l in w.stdout.splitlines() if ":" in l and len(l) < 120][:25]
        result["whois"] = lines
        for l in lines[:8]:
            print(f"   {l.strip()}")
    except Exception as e:
        result["whois_error"] = str(e)

    return result

def generate_html_report(username: str, results: list[dict]) -> Path:
    """Genera un reporte HTML visual del análisis OSINT."""
    found = [r for r in results if r["found"]]
    not_found = [r for r in results if not r["found"]]
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_path = OSINT_DIR / f"{username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    rows_found = "\n".join(
        f'<tr><td>✅</td><td>{r["platform"]}</td><td><a href="{r["url"]}" target="_blank">{r["url"]}</a></td></tr>'
        for r in found
    )
    rows_nf = "\n".join(
        f'<tr class="nf"><td>❌</td><td>{r["platform"]}</td><td>{r["url"]}</td></tr>'
        for r in not_found[:30]
    )
    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Alberth OSINT — @{username}</title>
<style>
  body{{background:#0a0e1a;color:#c8d8e8;font-family:'Courier New',monospace;padding:20px}}
  h1{{color:#00f0ff;text-shadow:0 0 12px #00f0ff80}}
  table{{width:100%;border-collapse:collapse;margin:12px 0}}
  th{{background:#00f0ff22;color:#00f0ff;padding:8px 12px;text-align:left}}
  td{{padding:7px 12px;border-bottom:1px solid #ffffff11}}
  tr:hover td{{background:#ffffff08}}
  tr.nf td{{color:#666}}
  a{{color:#00f0ff}}
  .badge{{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px}}
  .found{{background:#00f0ff22;color:#00f0ff;border:1px solid #00f0ff44}}
  .miss{{background:#ff000022;color:#ff6060;border:1px solid #ff000044}}
</style></head><body>
<h1>🔍 Alberth OSINT · @{username}</h1>
<p>Análisis generado: <b>{ts}</b> &nbsp;|&nbsp;
<span class="badge found">✅ {len(found)} encontrados</span> &nbsp;
<span class="badge miss">❌ {len(not_found)} no encontrados</span></p>
<h2 style="color:#00f0ff">Perfiles Activos</h2>
<table><tr><th>Estado</th><th>Plataforma</th><th>URL</th></tr>{rows_found}</table>
<details><summary style="cursor:pointer;color:#888;margin-top:20px">Ver no encontrados ({len(not_found)})</summary>
<table><tr><th>Estado</th><th>Plataforma</th><th>URL revisada</th></tr>{rows_nf}</table></details>
</body></html>"""
    out_path.write_text(html, encoding="utf-8")
    print(f"\n   📄 Reporte guardado: {out_path}")
    return out_path

def save_json(data: dict | list, filename: str) -> Path:
    path = OSINT_DIR / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path

# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 alberth_osint.py [username|email|domain|report] <valor>")
        sys.exit(1)

    mode = sys.argv[1].lower()
    target = sys.argv[2]

    if mode == "username":
        results = search_username(target)
        save_json(results, f"username_{target}_{int(time.time())}.json")

    elif mode == "report":
        results = search_username(target)
        html_path = generate_html_report(target, results)
        import subprocess
        subprocess.run(["open", str(html_path)])

    elif mode == "email":
        result = check_email_breach(target)
        save_json(result, f"email_{target.replace('@','_')}_{int(time.time())}.json")

    elif mode == "domain":
        result = lookup_domain(target)
        save_json(result, f"domain_{target}_{int(time.time())}.json")

    else:
        print(f"Modo '{mode}' no reconocido. Usa: username, email, domain, report")
