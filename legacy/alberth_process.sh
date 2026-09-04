#!/bin/bash
# Alberth Process Script
# Lee el texto transcrito, lo procesa y genera respuesta via OpenClaw.

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

INPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/input"
OUTPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/output"
LOG_DIR="$HOME/.openclaw/workspace/voice_exchange/logs"

LOGFILE="$LOG_DIR/alberth_process_$(date +%Y%m%d).log"
NOTIFY_FILE="$LOG_DIR/notification.log"

echo "[$(date)] Alberth Process iniciado." >> "$LOGFILE"

# Función para procesar un archivo de texto
process_text() {
    local text_file="$1"
    local base_name
    base_name=$(basename "$text_file" .txt)
    
    local response_file="$OUTPUT_DIR/${base_name}_response.txt"
    local audio_file="$OUTPUT_DIR/${base_name}_response.mp3"
    
    echo "[$(date)] Procesando texto: $text_file" >> "$LOGFILE"
    
    # Leer el contenido del archivo de texto
    local query
    query=$(cat "$text_file")
    
    if [[ -z "$query" ]]; then
        echo "[$(date)] Archivo de texto vacío: $text_file" >> "$LOGFILE"
        return
    fi
    
    echo "[$(date)] Consulta: $query" >> "$LOGFILE"
    
    # Enviar consulta al Agente OpenClaw (Alberth) con memoria y personalidad
    echo "[$(date)] Enviando consulta a OpenClaw Agent..." >> "$LOGFILE"
    local temp_response_json="/tmp/openclaw_response_$$.json"
    
    # Llamar al agente
    openclaw agent --agent main --message "$query" --json > "$temp_response_json" 2>&1
    local status=$?
    
    local response=""
    if [ $status -eq 0 ] && [ -s "$temp_response_json" ]; then
        response=$(jq -r '.result.payloads[0].text // ""' "$temp_response_json" 2>/dev/null)
    fi
    rm -f "$temp_response_json"
    
    # Fallback si falla
    if [ -z "$response" ] || [ "$response" == "null" ]; then
        echo "[$(date)] Falló la respuesta del Agente OpenClaw. Usando fallback básico." >> "$LOGFILE"
        response="Lo siento Señor, ocurrió un problema al conectar con el servidor de OpenClaw. ¿Podría repetirlo?"
    fi
    
    # Guardar la respuesta de texto
    echo "$response" > "$response_file"
    echo "[$(date)] Respuesta generada: $response" >> "$LOGFILE"
    
    # Generar audio de la respuesta usando el servicio TTS de OpenClaw (Kokoro en OpenRouter)
    echo "[$(date)] Generando audio de respuesta con OpenClaw TTS..." >> "$LOGFILE"
    if openclaw infer tts convert --text "$response" --output "$audio_file" >> "$LOGFILE" 2>&1; then
        echo "[$(date)] Audio generado exitosamente con OpenClaw TTS: $audio_file" >> "$LOGFILE"
        echo "AUDIO_RESPONSE:$audio_file" >> "$NOTIFY_FILE"
    else
        echo "[$(date)] Falló OpenClaw TTS. Intentando fallback local (macOS say)..." >> "$LOGFILE"
        if say -v Diego -o "$audio_file" -- "$response"; then
            echo "[$(date)] Audio generado con fallback local 'say': $audio_file" >> "$LOGFILE"
            echo "AUDIO_RESPONSE:$audio_file" >> "$NOTIFY_FILE"
        else
            echo "[$(date)] ERROR crítico: fallaron ambos métodos de TTS" >> "$LOGFILE"
            touch "$audio_file"
            echo "AUDIO_RESPONSE:$audio_file" >> "$NOTIFY_FILE"
        fi
    fi
    
    # Mover el archivo de texto procesado
    mkdir -p "$INPUT_DIR/processed"
    mv "$text_file" "$INPUT_DIR/processed/$(basename "$text_file").processed_$(date +%Y%m%d_%H%M%S)"
}

# Procesar archivos de texto existentes
echo "[$(date)] Procesando archivos de texto existentes..." >> "$LOGFILE"
for text_file in "$OUTPUT_DIR"/*.txt; do
    # Evitar procesar archivos de respuesta
    if [[ ! "$text_file" =~ _response\.txt$ ]]; then
        process_text "$text_file"
    fi
done

echo "[$(date)] Alberth Process completado." >> "$LOGFILE"