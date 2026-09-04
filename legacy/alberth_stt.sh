#!/bin/bash
# Alberth Speech-to-Text Script
# Monitorea la carpeta de input, transcribe audio y guarda el texto

INPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/input"
OUTPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/output"
LOG_DIR="$HOME/.openclaw/workspace/voice_exchange/logs"
MODEL="base"  # balance bueno entre velocidad y precisión
LANGUAGE="es"  # español

# Crear directorios si no existen
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR"

# Archivo de log
LOGFILE="$LOG_DIR/alberth_stt_$(date +%Y%m%d).log"
NOTIFY_FILE="$LOG_DIR/notification.log"

echo "[$(date)] Alberth STT iniciado. Monitoreando $INPUT_DIR" >> "$LOGFILE"

# Función para procesar un archivo de audio
process_audio() {
    local audio_file="$1"
    local base_name
    base_name=$(basename "$audio_file")
    base_name="${base_name%.*}"  # Remove extension
    
    local txt_file="$OUTPUT_DIR/${base_name}.txt"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    echo "[$(date)] Procesando: $audio_file" >> "$LOGFILE"
    
    # Transcribir con OpenClaw STT (usando Groq Whisper de forma ultra rápida)
    local temp_stt_json="/tmp/openclaw_stt_$$.json"
    
    if openclaw infer audio transcribe --file "$audio_file" --model groq/whisper-large-v3-turbo --json > "$temp_stt_json" 2>/dev/null; then
        local text
        text=$(jq -r '.outputs[0].text // ""' "$temp_stt_json" 2>/dev/null)
        
        if [ -n "$text" ] && [ "$text" != "null" ]; then
            echo "$text" > "$txt_file"
            echo "[$(date)] Transcripción completada via OpenClaw: $txt_file" >> "$LOGFILE"
            echo "[$(date)] Texto: $text" >> "$LOGFILE"
            
            # Notificar que hay un nuevo texto disponible
            echo "NEW_TEXT:$txt_file" >> "$NOTIFY_FILE"
            
            # Mover archivo procesado a un subdirectorio de processed
            mkdir -p "$INPUT_DIR/processed"
            mv "$audio_file" "$INPUT_DIR/processed/$(basename "$audio_file").processed_$timestamp"
        else
            echo "[$(date)] Transcripción vacía recibida de OpenClaw" >> "$LOGFILE"
        fi
    else
        echo "[$(date)] ERROR al transcribir via OpenClaw STT" >> "$LOGFILE"
    fi
    rm -f "$temp_stt_json"
}

# Procesar archivos existentes (para pruebas iniciales)
echo "[$(date)] Procesando archivos existentes..." >> "$LOGFILE"
for audio_file in "$INPUT_DIR"/*.{mp3,wav,m4a,aiff,flac}; do
    if [[ -f "$audio_file" ]]; then
        process_audio "$audio_file"
    fi
done

echo "[$(date)] Alberth STT completado." >> "$LOGFILE"