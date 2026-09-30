#!/usr/bin/env python3
# =============================================================================
# ALBERTH WEB SECURITY SCANNER — Escáner de Seguridad Web
# Inspirado en GOD-S-EYE (alisalive/GOD-S-EYE) — implementación propia
#
# Capacidades:
#   1. Fingerprinting de tecnologías (Server, X-Powered-By, CMS, frameworks)
#   2. Análisis de cabeceras de seguridad HTTP (HSTS, CSP, CORS, etc.)
#   3. Verificación de puertos comunes (TCP scan ligero)
#   4. Detección de URLs sensibles expuestas (admin, .env, phpinfo, etc.)
#   5. Verificación TLS/SSL (fecha de expiración, versión, algoritmo)
#   6. Reporte visual HTML
#
# Uso:
#   python3 alberth_websec_scanner.py scan    https://ejemplo.com
#   python3 alberth_websec_scanner.py headers https://ejemplo.com
#   python3 alberth_websec_scanner.py ports   ejemplo.com
#   python3 alberth_websec_scanner.py report  https://ejemplo.com
# =============================================================================

from __future__ import annotations
import sys, json, socket, ssl, time
import urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

WORKSPACE = Path(__file__).resolve().parent
WEBSEC_DIR = WORKSPACE / "memory" / "websec"
WEBSEC_DIR.mkdir(parents=True, exist_ok=True)

# ─── Cabeceras de seguridad HTTP esperadas ────────────────────────────────────
SECURITY_HEADERS = {
    "Strict-Transport-Security": {
        "info": "HSTS — Fuerza HTTPS en el navegador.",
        "severity": "HIGH"
    },
    "Content-Security-Policy": {
        "info": "CSP — Previene XSS y ataques de inyección.",
        "severity": "HIGH"
    },
    "X-Frame-Options": {
        "info": "Previene Clickjacking (iframe no autorizado).",
        "severity": "MEDIUM"
    },
    "X-Content-Type-Options": {
        "info": "Previene MIME-type sniffing.",
        "severity": "MEDIUM"
    },
    "Referrer-Policy": {
        "info": "Controla qué info del referrer se comparte.",
        "severity": "LOW"
    },
    "Permissions-Policy": {
        "info": "Controla el acceso a APIs del navegador (cámara, GPS...).",
        "severity": "LOW"
    },
    "X-XSS-Protection": {
        "info": "Filtro XSS legacy (IE/Edge antiguos).",
        "severity": "LOW"
    },
    "Cache-Control": {
        "info": "Controla el cacheo de respuestas sensibles.",
        "severity": "INFO"
    },
}

# ─── Rutas sensibles comunes a verificar ─────────────────────────────────────
SENSITIVE_PATHS = [
    "/.env", "/.env.local", "/.env.backup",
    "/admin", "/admin/", "/wp-admin/", "/administrator/",
    "/phpinfo.php", "/info.php", "/test.php",
    "/backup.zip", "/backup.sql", "/dump.sql",
    "/config.php", "/configuration.php",
    "/wp-config.php", "/config.yml", "/config.yaml",
    "/.git/HEAD", "/.git/config",
    "/robots.txt", "/sitemap.xml",
    "/server-status", "/server-info",
    "/.htaccess", "/.htpasswd",
    "/api/", "/api/v1/", "/api/v2/",
    "/swagger-ui.html", "/api-docs",
    "/debug", "/console", "/actuator",
    "/login", "/panel", "/cpanel",
]

# ─── Puertos comunes ──────────────────────────────────────────────────────────
COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 445, 3306, 3389, 5432, 6379, 8080, 8443, 8888, 27017]

UA = "Mozilla/5.0 (compatible; AlberthSecScanner/1.0)"

def _get(url: str, timeout: int = 8) -> tuple[int, dict, str]:
    """Realiza un GET y devuelve (status, headers_dict, body_snippet)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers)
            body = resp.read(8192).decode("utf-8", errors="ignore")
            return resp.status, headers, body
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), ""
    except Exception as e:
        return 0, {}, str(e)

def fingerprint_technologies(url: str) -> dict:
    """Detecta tecnologías usadas por el sitio a partir de cabeceras y cuerpo."""
    status, headers, body = _get(url)
    findings: list[str] = []

    header_map = {k.lower(): v for k, v in headers.items()}

    # Server header
    server = header_map.get("server", "")
    if server:
        findings.append(f"Servidor: {server}")

    # X-Powered-By
    xpb = header_map.get("x-powered-by", "")
    if xpb:
        findings.append(f"Powered-By: {xpb}")

    # CMS detection via body
    cms_signatures = {
        "WordPress": ["wp-content", "wp-includes", "wordpress"],
        "Joomla":    ["joomla", "/components/com_"],
        "Drupal":    ["drupal", "sites/default/files"],
        "Shopify":   ["cdn.shopify.com", "Shopify.theme"],
        "Wix":       ["wix.com", "wixstatic"],
        "Squarespace": ["squarespace.com", "static1.squarespace"],
        "Magento":   ["mage/", "Magento"],
        "Laravel":   ["laravel_session", "XSRF-TOKEN"],
        "Django":    ["csrfmiddlewaretoken", "__django"],
        "Rails":     ["X-Runtime", "Ruby on Rails"],
        "Next.js":   ["__NEXT_DATA__", "/_next/"],
        "React":     ["__REACT_APP", "react-root"],
        "Vue":       ["__vue_app__", "data-v-"],
        "Angular":   ["ng-version", "ng-app"],
    }
    body_lower = body.lower()
    for cms, signs in cms_signatures.items():
        if any(s.lower() in body_lower for s in signs):
            findings.append(f"CMS/Framework: {cms}")

    # Cookies
    for k, v in headers.items():
        if k.lower() == "set-cookie":
            if "HttpOnly" not in v:
                findings.append(f"⚠️ Cookie SIN HttpOnly: {v[:80]}")
            if "Secure" not in v:
                findings.append(f"⚠️ Cookie SIN flag Secure: {v[:80]}")
            if "SameSite" not in v:
                findings.append(f"⚠️ Cookie SIN SameSite: {v[:80]}")

    return {"url": url, "status": status, "technologies": findings}

def analyze_headers(url: str) -> dict:
    """Analiza las cabeceras de seguridad HTTP."""
    status, headers, _ = _get(url)
    headers_lower = {k.lower(): v for k, v in headers.items()}
    results = []

    for header, meta in SECURITY_HEADERS.items():
        present = header.lower() in headers_lower
        value = headers_lower.get(header.lower(), "")
        results.append({
            "header": header,
            "present": present,
            "value": value if present else None,
            "info": meta["info"],
            "severity": meta["severity"] if not present else "OK",
        })

    missing_high = [r for r in results if not r["present"] and r["severity"] == "HIGH"]
    missing_med = [r for r in results if not r["present"] and r["severity"] == "MEDIUM"]
    score = 100 - (len(missing_high) * 20) - (len(missing_med) * 10)
    score = max(0, score)

    return {
        "url": url,
        "http_status": status,
        "security_score": score,
        "headers_analysis": results,
        "server_header": headers_lower.get("server", "no revelado"),
        "x_powered_by": headers_lower.get("x-powered-by", "no revelado"),
    }

def check_sensitive_paths(base_url: str) -> list[dict]:
    """Verifica si existen rutas sensibles expuestas."""
    base = base_url.rstrip("/")
    exposed = []
    print(f"\n🔓 Verificando {len(SENSITIVE_PATHS)} rutas sensibles...")
    for path in SENSITIVE_PATHS:
        status, _, body = _get(base + path, timeout=5)
        is_exposed = status in (200, 301, 302, 403) and status != 404
        if is_exposed:
            risk = "CRÍTICO" if status == 200 else "AVISO"
            exposed.append({"path": base + path, "status": status, "risk": risk})
            print(f"   ⚠️  [{risk}] HTTP {status} → {path}")
    if not exposed:
        print("   ✅ Sin rutas sensibles expuestas detectadas.")
    return exposed

def scan_ports(host: str, ports: list[int] = None, timeout: float = 0.8) -> list[dict]:
    """Escaneo ligero de puertos TCP comunes."""
    if ports is None:
        ports = COMMON_PORTS
    # Limpiar host
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    print(f"\n🔌 Escaneando puertos en: {host}")
    results = []
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                status = "ABIERTO"
        except (socket.timeout, ConnectionRefusedError, OSError):
            status = "cerrado"
        if status == "ABIERTO":
            print(f"   🟢 {port:5} → {status}")
        results.append({"port": port, "status": status, "host": host})
    open_ports = [r for r in results if r["status"] == "ABIERTO"]
    print(f"   Puertos abiertos: {len(open_ports)}/{len(ports)}")
    return results

def check_ssl(host: str) -> dict:
    """Verifica el certificado TLS/SSL del sitio."""
    host = host.replace("https://", "").replace("http://", "").split("/")[0]
    print(f"\n🔒 Verificando TLS/SSL: {host}")
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as s:
            s.settimeout(8)
            s.connect((host, 443))
            cert = s.getpeercert()
            version = s.version()
            cipher = s.cipher()

        # Fecha expiración
        exp_str = cert.get("notAfter", "")
        if exp_str:
            exp_dt = datetime.strptime(exp_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
            days_left = (exp_dt - datetime.now(timezone.utc)).days
        else:
            days_left = -1

        result = {
            "host": host,
            "valid": True,
            "version": version,
            "cipher": cipher[0] if cipher else "unknown",
            "expires": exp_str,
            "days_until_expiry": days_left,
            "subject": dict(x[0] for x in cert.get("subject", [])),
            "issuer": dict(x[0] for x in cert.get("issuer", [])),
        }
        status_emoji = "✅" if days_left > 30 else ("⚠️" if days_left > 0 else "❌")
        print(f"   {status_emoji} Válido · Expira en {days_left} días · {version} · {cipher[0] if cipher else '?'}")
        return result
    except ssl.SSLError as e:
        print(f"   ❌ Error SSL: {e}")
        return {"host": host, "valid": False, "error": str(e)}
    except Exception as e:
        return {"host": host, "valid": False, "error": str(e)}

def full_scan(url: str) -> dict:
    """Ejecuta el análisis completo del sitio."""
    print(f"\n🛡️  ALBERTH SECURITY SCANNER — Objetivo: {url}")
    print("   " + "═" * 58)
    start = time.time()

    host = urllib.parse.urlparse(url).netloc or url

    report = {
        "target": url,
        "scan_date": datetime.now().isoformat(),
        "technologies": fingerprint_technologies(url),
        "headers": analyze_headers(url),
        "ssl": check_ssl(host) if url.startswith("https") else {"note": "No HTTPS"},
        "sensitive_paths": check_sensitive_paths(url),
        "ports": scan_ports(host),
    }

    elapsed = time.time() - start
    print(f"\n   ✅ Análisis completo en {elapsed:.1f}s")
    return report

def generate_html_report(url: str, report: dict) -> Path:
    """Genera un reporte HTML del análisis de seguridad."""
    headers_data = report.get("headers", {})
    headers_rows = ""
    for h in headers_data.get("headers_analysis", []):
        color = "#00f0ff" if h["present"] else ("#ff4444" if h["severity"] == "HIGH" else "#ffaa00")
        icon = "✅" if h["present"] else "❌"
        headers_rows += f'<tr><td>{icon}</td><td style="color:{color}">{h["header"]}</td><td>{h.get("value","—")[:60]}</td><td>{h["info"]}</td></tr>\n'

    paths_data = report.get("sensitive_paths", [])
    paths_rows = ""
    for p in paths_data:
        risk_color = "#ff4444" if p["risk"] == "CRÍTICO" else "#ffaa00"
        paths_rows += f'<tr><td style="color:{risk_color}">⚠️ {p["risk"]}</td><td>{p["path"]}</td><td>HTTP {p["status"]}</td></tr>\n'
    if not paths_rows:
        paths_rows = '<tr><td colspan="3" style="color:#00f0ff;text-align:center">✅ Sin exposiciones detectadas</td></tr>'

    ports_open = [p for p in report.get("ports", []) if p["status"] == "ABIERTO"]
    ports_rows = "".join(f'<tr><td>🟢 {p["port"]}</td><td>{p["host"]}</td></tr>' for p in ports_open) or \
                 '<tr><td colspan="2" style="color:#888">Sin puertos abiertos detectados</td></tr>'

    score = headers_data.get("security_score", 0)
    score_color = "#00f0ff" if score >= 80 else ("#ffaa00" if score >= 50 else "#ff4444")

    ssl_info = report.get("ssl", {})
    ssl_html = f"""
    <div><b>Versión:</b> {ssl_info.get('version','N/A')}</div>
    <div><b>Cifrado:</b> {ssl_info.get('cipher','N/A')}</div>
    <div><b>Días hasta expiración:</b> {ssl_info.get('days_until_expiry','N/A')}</div>
    """ if ssl_info.get("valid") else f"<div style='color:#ff4444'>❌ {ssl_info.get('error','Error TLS')}</div>"

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target = report.get("target", url)
    out_path = WEBSEC_DIR / f"scan_{urllib.parse.urlparse(target).netloc.replace('.','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">
<title>Alberth SecScan — {target}</title>
<style>
  body{{background:#0a0e1a;color:#c8d8e8;font-family:'Courier New',monospace;padding:24px;max-width:960px;margin:auto}}
  h1{{color:#ff6600;text-shadow:0 0 12px #ff660080}} h2{{color:#00f0ff;border-bottom:1px solid #00f0ff44;padding-bottom:4px}}
  table{{width:100%;border-collapse:collapse;margin:10px 0}} th{{background:#00f0ff22;color:#00f0ff;padding:8px;text-align:left}}
  td{{padding:7px 10px;border-bottom:1px solid #ffffff11}} tr:hover td{{background:#ffffff08}}
  .score{{font-size:3em;font-weight:bold}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:12px 0}}
  .card{{background:#ffffff08;border:1px solid #ffffff18;border-radius:8px;padding:14px}}
</style></head><body>
<h1>🛡️ Alberth Security Scanner</h1>
<p><b>Objetivo:</b> {target}<br><b>Fecha:</b> {ts}</p>
<div class="grid">
  <div class="card"><div>Puntuación de Seguridad</div>
    <div class="score" style="color:{score_color}">{score}/100</div></div>
  <div class="card"><b>TLS/SSL</b>{ssl_html}</div>
</div>
<h2>Cabeceras de Seguridad HTTP</h2>
<table><tr><th></th><th>Cabecera</th><th>Valor</th><th>Descripción</th></tr>{headers_rows}</table>
<h2>Rutas Sensibles</h2>
<table><tr><th>Riesgo</th><th>Ruta</th><th>HTTP</th></tr>{paths_rows}</table>
<h2>Puertos Abiertos</h2>
<table><tr><th>Puerto</th><th>Host</th></tr>{ports_rows}</table>
</body></html>"""

    out_path.write_text(html, encoding="utf-8")
    print(f"\n   📄 Reporte guardado: {out_path}")
    return out_path

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python3 alberth_websec_scanner.py [scan|headers|ports|report] <url/host>")
        sys.exit(1)

    mode = sys.argv[1].lower()
    target = sys.argv[2]

    if mode == "scan":
        r = full_scan(target)
        ts = int(time.time())
        host = urllib.parse.urlparse(target).netloc or target
        path = WEBSEC_DIR / f"scan_{host.replace('.','_')}_{ts}.json"
        path.write_text(json.dumps(r, indent=2, ensure_ascii=False))
        print(f"   💾 JSON guardado: {path}")

    elif mode == "headers":
        r = analyze_headers(target)
        print(json.dumps(r, indent=2))

    elif mode == "ports":
        r = scan_ports(target)
        open_p = [x for x in r if x["status"] == "ABIERTO"]
        print(f"\nResumen: {len(open_p)} puertos abiertos")

    elif mode == "report":
        r = full_scan(target)
        html_path = generate_html_report(target, r)
        import subprocess
        subprocess.run(["open", str(html_path)])

    else:
        print(f"Modo '{mode}' no reconocido.")
