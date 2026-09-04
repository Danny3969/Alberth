#!/bin/bash
# =============================================================================
# ALBERTH SPEAK — Grabación directa de voz para Alberth
# Uso:
#   ./alberth_speak.sh          → Graba hasta que presiones ENTER (max 30s)
#   ./alberth_speak.sh -t 60    → Graba hasta 60 segundos
#   ./alberth_speak.sh -m       → Graba en modo manual (ENTER para parar)
# =============================================================================

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

# --- Cargar API Keys desde archivo protegido ---
# shellcheck source=/dev/null
[[ -f "$HOME/.openclaw/.env" ]] && source "$HOME/.openclaw/.env"

INPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/input"
DURATION=30
MANUAL=false

# --- Argumentos ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        -t|--time) DURATION="$2"; shift 2 ;;
        -m|--manual) MANUAL=true; shift ;;
        *) shift ;;
    esac
done

# --- Verificar dependencias ---
if ! command -v rec &>/dev/null && ! command -v sox &>/dev/null; then
    echo ""
    echo "⚠️  SoX no está instalado. Instalando..."
    brew install sox 2>/dev/null
fi

mkdir -p "$INPUT_DIR"

# Nombre del archivo con timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$INPUT_DIR/alberth_voice_${TIMESTAMP}.wav"

echo ""
echo "🎙️  ALBERTH — Grabación de voz"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if $MANUAL; then
    echo "▶  Grabando... (presiona ENTER para detener)"
    echo ""
    # Grabar en background, matar al presionar ENTER
    rec -q -r 16000 -c 1 -e signed-integer -b 16 "$OUTPUT_FILE" &
    REC_PID=$!
    read -r  # Esperar ENTER
    kill "$REC_PID" 2>/dev/null
    wait "$REC_PID" 2>/dev/null
else
    echo "▶  Grabando por ${DURATION} segundos..."
    echo "   (Presiona CTRL+C para detener antes)"
    echo ""
    # Countdown visual
    rec -q -r 16000 -c 1 -e signed-integer -b 16 "$OUTPUT_FILE" trim 0 "$DURATION" &
    REC_PID=$!
    
    for ((i=DURATION; i>0; i--)); do
        printf "\r   ⏱  Tiempo restante: %2ds  " "$i"
        sleep 1
        # Verificar si el proceso terminó
        if ! kill -0 "$REC_PID" 2>/dev/null; then
            break
        fi
    done
    kill "$REC_PID" 2>/dev/null
    printf "\r   ✅ Grabación completada.           \n"
fi

# --- Verificar que el archivo existe y tiene contenido ---
if [[ ! -s "$OUTPUT_FILE" ]]; then
    echo ""
    echo "❌ Error: No se capturó audio. Verifique el micrófono."
    exit 1
fi

FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Audio capturado: $(basename "$OUTPUT_FILE") ($FILE_SIZE)"
echo "🔄 Procesando..."
echo ""

WORKSPACE_DIR="$HOME/.openclaw/workspace"

# Verificar si el daemon master está corriendo
# El grep excluye el proceso del comando grep y la propia sesión de speak si tuviese un nombre similar
if ! pgrep -f "alberth_master.sh" | grep -v "$$" >/dev/null; then
    echo "⚠️  El daemon de Alberth (master.sh) no está corriendo en background."
    echo "⚙️  Ejecutando pipeline de forma síncrona directamente..."
    echo ""
    bash "$WORKSPACE_DIR/alberth_master.sh" "$OUTPUT_FILE"
else
    echo "🔄 Enviado al daemon de Alberth en background."
    echo "   (Alberth responderá en audio automáticamente en unos segundos)"
    echo ""
fi
