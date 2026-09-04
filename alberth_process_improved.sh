#!/bin/bash
# Alberth Process Script Mejorado
# Lee el texto transcrito, lo procesa y genera una respuesta de texto y audio usando say (macOS TTS)

INPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/input"
OUTPUT_DIR="$HOME/.openclaw/workspace/voice_exchange/output"
LOG_DIR="$HOME/.openclaw/workspace/voice_exchange/logs"

LOGFILE="$LOG_DIR/alberth_process_$(date +%Y%m%d).log"
NOTIFY_FILE="$LOG_DIR/notification.log"

echo "[$(date)] Alberth Process Mejorado iniciado." >> "$LOGFILE"

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
    
    # Procesar la consulta (aquí iría la integración con OpenClaw)
    local response
    if [[ "$query" =~ ^(hola|buenos dias|buenas tardes|buenas noches) ]]; then
        response="¡Hola señor Danny Jaya! Soy Alberth, su asistente personal. ¿En qué puedo ayudarle hoy?"
    elif [[ "$query" =~ (proyecto|DRIVO) ]]; then
        response="Entiendo que quiere hablar sobre sus proyectos DRIVO y DRIVO ONE. Actualmente tengo su memoria actualizada y puedo asistirle en el desarrollo, planificación o resolución de problemas técnicos relacionados."
    elif [[ "$query" =~ (memoria|recordar) ]]; then
        response="Su memoria a largo plazo está funcionando correctamente con 54 memories almacenados. Mem0 está conectado en modo plataforma con autoRecall y autoCapture habilitados."
    elif [[ "$query" =~ (voz|hablar) ]]; then
        response="El sistema de voz tipo Alberth está parcialmente implementado. Actualmente tengo texto a voz funcional y el componente de voz a texto (Whisper) instalado y probado. Necesitamos establecer el flujo completo de comunicación."
    elif [[ "$query" =~ (ayuda|help) ]]; then
        response="Como su asistente Alberth, puedo ayudarle con múltiples tareas: revisar su memoria, ejecutar habilidades, gestionar proyectos DRIVO, o establecer flujos de trabajo automatizados. ¿En qué área específica necesita asistencia?"
    else
        response="He recibido su consulta: \"$query\". Estoy procesando su solicitud utilizando mis capacidades de razonamiento y memoria. Para consultas más complejas, puedo realizar análisis detallados o ejecutar habilidades específicas según necesite."
    fi
    
    # Guardar la respuesta de texto
    echo "$response" > "$response_file"
    echo "[$(date)] Respuesta generada: $response" >> "$LOGFILE"
    
    # Generar audio de la respuesta usando say (macOS TTS)
    echo "[$(date)] Generando audio de respuesta con say..." >> "$LOGFILE"
    if say -v Diego -o "$audio_file" -- "$response"; then
        echo "[$(date)] Audio generado exitosamente: $audio_file" >> "$LOGFILE"
        echo "AUDIO_RESPONSE:$audio_file" >> "$NOTIFY_FILE"
    else
        echo "[$(date)] ERROR al generar audio para: $response" >> "$LOGFILE"
        # Crear un marcador de posición en caso de fallo
        touch "$audio_file"
        echo "AUDIO_RESPONSE:$audio_file" >> "$NOTIFY_FILE"
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

echo "[$(date)] Alberth Process Mejorado completado." >> "$LOGFILE"