#!/bin/bash
# =============================================================================
# ALBERTH TUNNEL — Exposición remota temporal de Alberth
# Abre un túnel rápido de Cloudflare y muestra la URL pública.
# =============================================================================

WORKSPACE_DIR="/Users/digitalspace/.openclaw/workspace"
LOG_DIR="$WORKSPACE_DIR/logs"
mkdir -p "$LOG_DIR"
TUNNEL_LOG="$LOG_DIR/alberth_tunnel.log"

# Detener cualquier túnel previo
pkill -f "cloudflared tunnel"

echo "Iniciando túnel seguro de Cloudflare hacia http://localhost:8080..."
cloudflared tunnel --url http://localhost:8080 > "$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

echo "Esperando a que se genere la URL pública..."
sleep 6

# Buscar la URL en el archivo de log
for i in {1..10}; do
    URL=$(grep -a -oE "https://[a-zA-Z0-9-]+\.trycloudflare\.com" "$TUNNEL_LOG" | head -n 1)
    if [ ! -z "$URL" ]; then
        echo "======================================================="
        echo "🌍 ¡ALBERTH ESTÁ DISPONIBLE EN INTERNET!"
        echo "URL pública: $URL"
        echo "======================================================="
        # Guardar en un json para que el servidor web pueda leerla y mostrarla si es necesario
        echo "{\"url\": \"$URL\", \"pid\": $TUNNEL_PID, \"started_at\": \"$(date)\"}" > "$WORKSPACE_DIR/panel/tunnel_status.json"
        exit 0
    fi
    sleep 2
done

echo "Error: No se pudo generar la URL. Revisa los logs en $TUNNEL_LOG"
exit 1
