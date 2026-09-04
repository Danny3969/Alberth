#!/usr/bin/env python3
# =============================================================================
# ALBERTH FINANCE HELPER — Precios en Tiempo Real
#
# Fuentes gratuitas sin API key:
#   - CoinGecko API v3   → Criptomonedas
#   - Yahoo Finance      → Acciones y ETFs
#   - Frankfurter API    → Divisas / Forex
# =============================================================================

import sys
import json
import urllib.request
import urllib.parse
import urllib.error


HEADERS = {"User-Agent": "AlberthAssistant/1.0 (macOS; Python3)"}

# Mapa de alias comunes → IDs oficiales de CoinGecko
CRYPTO_ALIASES = {
    "bitcoin": "bitcoin",   "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana",     "sol": "solana",
    "cardano": "cardano",   "ada": "cardano",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "bnb": "binancecoin",   "binance": "binancecoin",
    "xrp": "ripple",        "ripple": "ripple",
    "litecoin": "litecoin", "ltc": "litecoin",
    "polkadot": "polkadot", "dot": "polkadot",
    "avalanche": "avalanche-2", "avax": "avalanche-2",
    "chainlink": "chainlink", "link": "chainlink",
    "polygon": "matic-network", "matic": "matic-network",
}

# Mapa de alias → tickers de acciones para Yahoo Finance
STOCK_ALIASES = {
    "apple": "AAPL", "aapl": "AAPL",
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
    "microsoft": "MSFT", "msft": "MSFT",
    "amazon": "AMZN", "amzn": "AMZN",
    "tesla": "TSLA", "tsla": "TSLA",
    "meta": "META", "facebook": "META",
    "nvidia": "NVDA", "nvda": "NVDA",
    "netflix": "NFLX", "nflx": "NFLX",
    "spotify": "SPOT", "spot": "SPOT",
}


def _fetch(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return None


def _fmt_price(price: float, decimals: int = 2) -> str:
    if price >= 1:
        return f"${price:,.{decimals}f}"
    # Para cryptos muy pequeñas, usar más decimales
    return f"${price:.8f}".rstrip('0')


def buscar_crypto(query: str) -> dict:
    """Consulta CoinGecko para criptomonedas."""
    q = query.lower().strip()
    coin_id = CRYPTO_ALIASES.get(q, q)

    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false&tickers=false&community_data=false&developer_data=false"
    data = _fetch(url)

    if not data or "market_data" not in data:
        return {"success": False, "message": f"No encontré cotización para: {query}"}

    md    = data["market_data"]
    name  = data.get("name", coin_id)
    usd   = md["current_price"].get("usd", 0)
    change_24h = md.get("price_change_percentage_24h", 0)
    market_cap = md["market_cap"].get("usd", 0)

    arrow = "📈" if change_24h >= 0 else "📉"
    sign  = "+" if change_24h >= 0 else ""

    msg = (
        f"{arrow} **{name}** (Crypto)\n"
        f"  Precio: {_fmt_price(usd)}\n"
        f"  Cambio 24h: {sign}{change_24h:.2f}%\n"
        f"  Market Cap: ${market_cap:,.0f}"
    )
    return {"success": True, "message": msg, "price_usd": usd, "change_24h": change_24h}


def buscar_accion(query: str) -> dict:
    """Consulta Yahoo Finance para acciones."""
    q = query.lower().strip()
    ticker = STOCK_ALIASES.get(q, q.upper())

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    data = _fetch(url)

    if not data:
        return {"success": False, "message": f"No pude obtener datos de Yahoo Finance para: {ticker}"}

    try:
        result  = data["chart"]["result"][0]
        meta    = result["meta"]
        price   = meta.get("regularMarketPrice", 0)
        prev    = meta.get("chartPreviousClose", price)
        change  = ((price - prev) / prev) * 100 if prev else 0
        name    = meta.get("shortName") or ticker
        currency= meta.get("currency", "USD")

        arrow = "📈" if change >= 0 else "📉"
        sign  = "+" if change >= 0 else ""

        msg = (
            f"{arrow} **{name}** ({ticker})\n"
            f"  Precio: ${price:,.2f} {currency}\n"
            f"  Cambio hoy: {sign}{change:.2f}%"
        )
        return {"success": True, "message": msg, "price": price, "change_pct": change, "ticker": ticker}
    except (KeyError, IndexError, TypeError) as e:
        return {"success": False, "message": f"Error procesando datos de {ticker}: {e}"}


def buscar_divisa(base: str, target: str = "USD") -> dict:
    """Consulta Frankfurter API para tasas de cambio."""
    base   = base.upper().strip()
    target = target.upper().strip()

    url = f"https://api.frankfurter.app/latest?from={base}&to={target}"
    data = _fetch(url)

    if not data or "rates" not in data:
        return {"success": False, "message": f"No encontré tasa de cambio para {base}/{target}"}

    rate = data["rates"].get(target, 0)
    msg  = f"💱 **{base} → {target}**: 1 {base} = {rate:.4f} {target}"
    return {"success": True, "message": msg, "rate": rate, "base": base, "target": target}


def detectar_y_buscar(query: str) -> dict:
    """Auto-detecta si es cripto, acción o divisa y llama al método correcto."""
    q_lower = query.lower()

    # Detección de divisas (palabras clave)
    forex_keywords = ["euro", "dólar", "peso", "yen", "libra", "yuan", "rublo",
                      "eur", "usd", "mxn", "gbp", "jpy", "cad", "aud", "chf"]
    if any(kw in q_lower for kw in forex_keywords):
        # Intentar extraer par de divisas
        if "euro" in q_lower or "eur" in q_lower:
            return buscar_divisa("EUR", "USD")
        if "peso" in q_lower or "mxn" in q_lower:
            return buscar_divisa("MXN", "USD")
        if "libra" in q_lower or "gbp" in q_lower:
            return buscar_divisa("GBP", "USD")
        if "yen" in q_lower or "jpy" in q_lower:
            return buscar_divisa("JPY", "USD")
        return buscar_divisa(q_lower.split()[0].upper(), "USD")

    # Detección de criptomonedas
    if any(kw in q_lower for kw in CRYPTO_ALIASES.keys()):
        # Extraer la moneda del query
        for alias in CRYPTO_ALIASES:
            if alias in q_lower:
                return buscar_crypto(alias)

    # Detección de acciones
    if any(kw in q_lower for kw in STOCK_ALIASES.keys()):
        for alias in STOCK_ALIASES:
            if alias in q_lower:
                return buscar_accion(alias)

    # Último recurso: intentar como crypto, luego como acción
    first_word = q_lower.split()[0]
    crypto_result = buscar_crypto(first_word)
    if crypto_result.get("success"):
        return crypto_result

    return buscar_accion(first_word)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
        query = payload.get("query", payload.get("prompt", ""))
    else:
        query = " ".join(sys.argv[1:])

    if not query:
        print(json.dumps({"success": False, "message": "No se especificó qué buscar."}))
        sys.exit(1)

    result = detectar_y_buscar(query)
    print(json.dumps(result, ensure_ascii=False))
