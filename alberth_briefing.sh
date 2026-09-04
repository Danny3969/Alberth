#!/bin/bash
# =============================================================================
# ALBERTH BRIEFING — Orquestador de Briefing Matutino
# Versión: 1.0
# Recopila contexto de: GCal, Gmail, Memoria y Tareas Activas.
# Envía al agente OpenClaw, reproduce respuesta en audio y notifica via macOS.
# =============================================================================

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

# --- Cargar API Keys desde archivo protegido ---
# shellcheck source=/dev/null
[[ -f "$HOME/.openclaw/.env" ]] && source "$HOME/.openclaw/.env"

# --- Rutas ---
WORKSPACE_DIR="$HOME/.openclaw/workspace"
VOICE_DIR="$WORKSPACE_DIR/voice_exchange"
OUTPUT_DIR="$VOICE_DIR/output"
LOG_DIR="$VOICE_DIR/logs"
MEMORY_FILE="$WORKSPACE_DIR/MEMORY.md"

mkdir -p "$OUTPUT_DIR" "$LOG_DIR"
LOGFILE="$LOG_DIR/alberth_briefing_$(date +%Y%m%d).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

# --- Verificar dependencias críticas ---
if ! command -v openclaw &>/dev/null; then
    log "ERROR CRÍTICO: openclaw no encontrado en PATH. Abortando briefing."
    osascript -e 'display notification "openclaw no disponible" with title "Alberth Briefing" subtitle "Error Crítico"'
    exit 1
fi

log "============================================"
log "Alberth Briefing v1.0 iniciado"
log "============================================"

# =============================================================================
# BLOQUE 1: Recopilación de datos de Google Calendar
# =============================================================================
log "BLOQUE 1: Obteniendo eventos del día desde Google Calendar..."
CALENDAR_DATA=""

GOG_BIN=$(command -v gog 2>/dev/null)

if [[ -n "$GOG_BIN" ]]; then
    TODAY_START="$(date +%Y-%m-%dT00:00:00%:z)"
    TODAY_END="$(date +%Y-%m-%dT23:59:59%:z)"

    RAW_CAL=$(gog calendar events primary \
        --from "$TODAY_START" \
        --to "$TODAY_END" \
        --json --no-input 2>/dev/null)

    if [[ -n "$RAW_CAL" ]]; then
        # Extraer resumen legible de los eventos
        CALENDAR_DATA=$(echo "$RAW_CAL" | python3 -c "
import json, sys
data = json.load(sys.stdin)
items = data.get('items', [])
if not items:
    print('Sin eventos agendados para hoy.')
else:
    for ev in items:
        summary = ev.get('summary', 'Sin título')
        start = ev.get('start', {})
        time_str = start.get('dateTime', start.get('date', 'Hora no definida'))
        # Limpiar offset timezone para lectura
        time_str = time_str.replace('T', ' ').split('+')[0].split('-05')[0]
        print(f'- {time_str}: {summary}')
" 2>/dev/null)
        log "GCal OK → $(echo "$CALENDAR_DATA" | wc -l | tr -d ' ') eventos encontrados."
    else
        CALENDAR_DATA="No fue posible obtener eventos del calendario (sin respuesta de gog)."
        log "WARN: gog calendar no devolvió datos."
    fi
else
    CALENDAR_DATA="Integración de Google Calendar no disponible (gog CLI no instalado)."
    log "WARN: gog CLI no encontrado. Saltando GCal."
fi

# =============================================================================
# BLOQUE 2: Recopilación de correos importantes de Gmail
# =============================================================================
log "BLOQUE 2: Obteniendo correos no leídos recientes de Gmail..."
GMAIL_DATA=""

if [[ -n "$GOG_BIN" ]]; then
    RAW_GMAIL=$(gog gmail search "is:unread newer_than:1d" \
        --max 5 \
        --json --no-input 2>/dev/null)

    if [[ -n "$RAW_GMAIL" ]]; then
        GMAIL_DATA=$(echo "$RAW_GMAIL" | python3 -c "
import json, sys
data = json.load(sys.stdin)
messages = data.get('messages', [])
if not messages:
    print('Sin correos importantes no leídos.')
else:
    for msg in messages[:5]:
        subject = msg.get('subject', 'Sin asunto')
        sender  = msg.get('from', 'Remitente desconocido')
        print(f'- De: {sender} | Asunto: {subject}')
" 2>/dev/null)
        log "Gmail OK → $(echo "$GMAIL_DATA" | wc -l | tr -d ' ') correos encontrados."
    else
        GMAIL_DATA="No hay correos no leídos importantes en las últimas 24 horas."
        log "WARN: gog gmail no devolvió datos o no hay correos."
    fi
else
    GMAIL_DATA="Integración de Gmail no disponible (gog CLI no instalado)."
    log "WARN: gog CLI no encontrado. Saltando Gmail."
fi

# =============================================================================
# BLOQUE 3: Leer memoria activa y tareas pendientes
# =============================================================================
log "BLOQUE 3: Leyendo estado de memoria desde SQLite y archivo..."
MEMORY_DATA=""

# Cargar desde SQLite
SQLITE_MEM=$(python3 "$WORKSPACE_DIR/alberth_memory.py" --context "briefing matutino" 2>/dev/null)
if [[ -n "$SQLITE_MEM" ]]; then
    MEMORY_DATA="$SQLITE_MEM"
    log "Memoria SQLite OK."
fi

# Fallback / Complemento de MEMORY.md
if [[ -f "$MEMORY_FILE" ]]; then
    MEMORY_DATA="${MEMORY_DATA}

=== MEMORIA ADICIONAL (MEMORY.md) ===
$(tail -30 "$MEMORY_FILE" 2>/dev/null)"
    log "Memoria MEMORY.md OK."
fi

if [[ -z "$MEMORY_DATA" ]]; then
    MEMORY_DATA="Sin archivo de memoria ni base de datos disponible."
    log "WARN: Sin memoria disponible."
fi

# =============================================================================
# BLOQUE 4: Construir prompt y enviar al Agente
# =============================================================================
log "BLOQUE 4: Construyendo prompt y enviando al Agente Alberth..."

FECHA_HOY=$(date '+%A, %d de %B de %Y, %H:%M' 2>/dev/null || date)

PROMPT="[BRIEFING MATUTINO AUTOMATIZADO - $FECHA_HOY]

Eres Alberth, el asistente personal del Señor Danny. Debes generar el briefing matutino completo. Habla en primera persona como si fueras Alberth saludando al Señor al inicio de su jornada. Sé conciso, profesional y cálido. Máximo 4-5 oraciones.

=== AGENDA DEL DÍA (Google Calendar) ===
$CALENDAR_DATA

=== CORREOS IMPORTANTES (Gmail - Últimas 24h) ===
$GMAIL_DATA

=== CONTEXTO Y MEMORIA ACTIVA ===
$MEMORY_DATA

Sintetiza todo lo anterior en un briefing hablado natural. Comienza con un saludo, menciona brevemente los eventos del día si los hay, alerta sobre correos relevantes si existen, y cierra con una nota motivacional o el punto más crítico del día. No uses listas ni markdown, habla de forma fluida como si estuvieras en una conversación."

# Archivo temporal para respuesta del agente
TEMP_AGENT_JSON="/tmp/alberth_briefing_agent_$$.json"
RESPONSE_MP3="$OUTPUT_DIR/briefing_$(date +%Y%m%d_%H%M%S)_response.mp3"

if openclaw agent \
    --agent main \
    --message "$PROMPT" \
    --json > "$TEMP_AGENT_JSON" 2>&1; then

    RESPONSE=$(jq -r '.result.payloads[0].text // ""' "$TEMP_AGENT_JSON" 2>/dev/null)
    rm -f "$TEMP_AGENT_JSON"

    if [[ -z "$RESPONSE" || "$RESPONSE" == "null" ]]; then
        log "WARN: Respuesta vacía del agente. Usando mensaje de respaldo."
        RESPONSE="Buenos días, Señor. Hubo un inconveniente al generar el briefing completo. Revise los logs para más detalles. Que tenga un excelente día."
    else
        log "Agente OK → Respuesta generada (${#RESPONSE} chars)."
    fi
else
    log "ERROR: Falló la llamada al agente. Usando mensaje de respaldo."
    RESPONSE="Buenos días, Señor. El agente no pudo generar el briefing en este momento. Verifique la conexión con el gateway de OpenClaw."
    rm -f "$TEMP_AGENT_JSON"
fi

# =============================================================================
# BLOQUE 5: TTS — Síntesis de voz
# =============================================================================
log "BLOQUE 5: Sintetizando respuesta en audio (edge-tts)..."

if python3 "$WORKSPACE_DIR/alberth_tts_premium.py" "$RESPONSE" "$RESPONSE_MP3" >> "$LOGFILE" 2>&1; then
    log "TTS Premium OK → Audio: $RESPONSE_MP3 (edge-tts)"
else
    log "WARN: TTS Premium falló. Intentando OpenClaw TTS Cloud..."
    if openclaw infer tts convert \
        --text "$RESPONSE" \
        --output "$RESPONSE_MP3" >> "$LOGFILE" 2>&1; then
        log "TTS Cloud OK → Audio: $RESPONSE_MP3"
    else
        log "WARN: TTS Cloud falló. Usando fallback 'say' de macOS."
        say -v Diego -o "$RESPONSE_MP3" -- "$RESPONSE" 2>/dev/null || {
            log "ERROR: Ambos métodos TTS fallaron. Intentando decirlo directamente con 'say'."
            say -v Diego "$RESPONSE" 2>/dev/null
            osascript -e "display notification \"$RESPONSE\" with title \"Alberth - Briefing Matutino\" sound name \"Glass\""
            exit 0
        }
        log "TTS Fallback OK → Audio generado con 'say'."
    fi
fi

# =============================================================================
# BLOQUE 6: Reproducción y Notificación
# =============================================================================
log "BLOQUE 6: Reproduciendo briefing y enviando notificación..."

# Notificación nativa macOS
osascript -e "display notification \"Briefing del día listo. Reproduciendo ahora...\" with title \"Alberth\" subtitle \"Buenos días, Señor\" sound name \"Glass\""

# Reproducir audio
if [[ -f "$RESPONSE_MP3" ]]; then
    afplay "$RESPONSE_MP3" 2>/dev/null
    log "Reproducción completada."
else
    log "ERROR: Archivo de audio no encontrado para reproducir."
fi

log "============================================"
log "Briefing matutino completado exitosamente."
log "============================================"
exit 0
