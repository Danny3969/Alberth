#!/bin/bash
# =============================================================================
# ALBERTH MASTER — Orquestador de Pipeline de Voz
# Versión: 3.0 (Sprint 6 — Tálamo Inteligente + Finanzas + Imágenes)
# Monitorea voice_exchange/input/, transcribe, procesa y reproduce respuesta.
# =============================================================================

export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"

# --- Cargar API Keys desde archivo protegido ---
# shellcheck source=/dev/null
[[ -f "$HOME/.openclaw/.env" ]] && source "$HOME/.openclaw/.env"

# --- Rutas base ---
WORKSPACE_DIR="$HOME/.openclaw/workspace"
VOICE_DIR="$WORKSPACE_DIR/voice_exchange"
INPUT_DIR="$VOICE_DIR/input"
OUTPUT_DIR="$VOICE_DIR/output"
LOG_DIR="$VOICE_DIR/logs"
LOCK_FILE="$VOICE_DIR/.alberth.lock"

# --- Inicialización ---
mkdir -p "$INPUT_DIR" "$OUTPUT_DIR" "$LOG_DIR"
LOGFILE="$LOG_DIR/alberth_master_$(date +%Y%m%d).log"

# --- Functions: Security, Sanitization & Connectivity (Fase 1) ---
is_online() {
    curl -s --connect-timeout 1.5 -I http://1.1.1.1 >/dev/null 2>&1
}

sanitize_input() {
    local input="$1"
    # Eliminar metacaracteres peligrosos para evitar RCE (Command Injection)
    echo "$input" | tr -d '`$&|<>\' | head -c 2000
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

# --- Rotación de logs (mantener solo 7 días) ---
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null

log "============================================"
log "Alberth Master v3.0 iniciado (PID: $$)"
log "Monitoreando: $INPUT_DIR"
log "============================================"

# --- Pre-carga del Tálamo (gemma:2b en Ollama) ---
# Se ejecuta en background para no bloquear el arranque de Alberth.
# Cuando llega el primer audio, el modelo ya está caliente en RAM.
log "Iniciando warmup del Tálamo (gemma:2b)..."
python3 "$WORKSPACE_DIR/alberth_talamo.py" --warmup >> "$LOGFILE" 2>&1 &


run_pipeline() {
    local audio_file="$1"
    local is_text_only=false
    local query=""

    if [[ "$audio_file" == "--text" ]]; then
        is_text_only=true
        query="$2"
    else
        # Verificar que el archivo existe y tiene contenido
        [[ ! -f "$audio_file" ]] && return
        [[ ! -s "$audio_file" ]] && return
        # Ignorar archivos de respuesta de audio (evitar loops)
        [[ "$audio_file" =~ _response\.(mp3|wav|m4a)$ ]] && return
    fi

    # Control de concurrencia: solo un proceso a la vez
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if kill -0 "$lock_pid" 2>/dev/null; then
            if [ "$is_text_only" = true ]; then
                log "Pipeline ocupado (PID $lock_pid). Esperando liberación..."
                # Esperar hasta 5 segundos (10 * 0.5s)
                local wait_count=0
                while [ -f "$LOCK_FILE" ] && [ $wait_count -lt 10 ]; do
                    sleep 0.5
                    wait_count=$((wait_count + 1))
                done
                # Si sigue bloqueado, procedemos de todos modos para no colgar la UI de texto
                if [ -f "$LOCK_FILE" ]; then
                    log "Pipeline sigue ocupado tras esperar. Procediendo de todos modos para consulta de texto."
                fi
            else
                log "Pipeline ocupado (PID $lock_pid). Omitiendo: $(basename -- "$audio_file")"
                return
            fi
        else
            # Lock huérfano: eliminarlo
            rm -f "$LOCK_FILE"
        fi
    fi

    # Adquirir lock
    echo $$ > "$LOCK_FILE"
    
    local base_name
    if [ "$is_text_only" = true ]; then
        base_name="web_text_$(date +%Y%m%d_%H%M%S)"
        log "--- PIPELINE INICIADO (TEXTO): $query ---"
    else
        base_name=$(basename -- "$audio_file")
        base_name="${base_name%.*}"
        log "--- PIPELINE INICIADO (AUDIO): $(basename -- "$audio_file") ---"
    fi

    local txt_file="$OUTPUT_DIR/${base_name}.txt"
    local response_txt="$OUTPUT_DIR/${base_name}_response.txt"
    local response_mp3="$OUTPUT_DIR/${base_name}_response.mp3"
    local temp_stt_json="/tmp/alberth_stt_$$.json"
    local temp_agent_json="/tmp/alberth_agent_$$.json"

    # ── PASO 1: STT — Transcripción de audio ──────────────────────────────
    if [ "$is_text_only" = false ]; then
        log "PASO 1: Transcribiendo audio con Groq Whisper (Cloud)..."
    local query=""

        if openclaw infer audio transcribe \
            --file "$audio_file" \
            --model groq/whisper-large-v3-turbo \
            --json > "$temp_stt_json" 2>/dev/null; then

            query=$(jq -r '.result.outputs[0].text // .outputs[0].text // ""' "$temp_stt_json" 2>/dev/null)
            rm -f "$temp_stt_json"

            if [[ -z "$query" || "$query" == "null" ]]; then
                log "WARN: Groq devolvió transcripción vacía. Activando fallback local..."
                query=""
            else
                log "STT CLOUD OK → Transcripción: $query"
                echo "$query" > "$txt_file"
            fi
        else
            log "WARN: Groq Whisper Cloud falló (sin conexión o API error). Activando fallback local..."
            rm -f "$temp_stt_json"
        fi

        # ── PASO 1b: STT FALLBACK — Whisper Local ─────────────────────────────
        if [[ -z "$query" ]]; then
            log "PASO 1b: Transcripción local con Whisper (modelo: base)..."
            local whisper_out_dir="/tmp/alberth_whisper_$$"
            mkdir -p "$whisper_out_dir"

            if whisper "$audio_file" \
                --model base \
                --language es \
                --output_format txt \
                --output_dir "$whisper_out_dir" \
                --fp16 False > /dev/null 2>&1; then

                local whisper_txt
                whisper_txt=$(ls "$whisper_out_dir"/*.txt 2>/dev/null | head -1)

                if [[ -n "$whisper_txt" && -s "$whisper_txt" ]]; then
                    query=$(cat "$whisper_txt")
                    log "STT LOCAL OK → Transcripción: $query"
                    echo "$query" > "$txt_file"
                else
                    log "ERROR: Whisper local no generó salida. Abortando pipeline."
                    rm -rf "$whisper_out_dir" "$LOCK_FILE"
                    return
                fi
            else
                log "ERROR: Whisper local también falló. Abortando pipeline."
                rm -rf "$whisper_out_dir" "$LOCK_FILE"
                return
            fi

            rm -rf "$whisper_out_dir"
        fi

        if [[ -z "$query" ]]; then
            log "ERROR: No se pudo obtener transcripción por ningún método. Abortando."
            rm -f "$LOCK_FILE"
            return
        fi

        # ── Filtro anti-basura (silencio / eco de altavoz) ──────────────────
        # Whisper devuelve estas frases cuando el audio está vacío o es ruido puro.
        local query_lower_filter
        query_lower_filter=$(echo "$query" | tr '[:upper:]' '[:lower:]' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
        local junk_phrases=("thank you" "thanks" "thank you." "thanks." "gracias" "gracias." \
            "." ".." "..." "!" "ok" "okay" "um" "uh" "hmm" "mm" "bye" "bye." \
            "you" "the" "a" "si" "sí" "no" \
            "yes" "yes." "yeah" "yeah." "yep" "nope" "sure" "right" \
            "this is the video" "this is the video." \
            "subtítulos realizados por la comunidad de amara.org" \
            "subtitulos en español" "suscríbete" "suscribete" \
            "music" "music." "applause" "laughter")
        local is_junk=false
        for junk in "${junk_phrases[@]}"; do
            if [[ "$query_lower_filter" == "$junk" ]]; then
                is_junk=true
                break
            fi
        done
        # También filtrar si la query tiene menos de 4 caracteres
        if [[ ${#query_lower_filter} -lt 4 ]]; then
            is_junk=true
        fi
        if [[ "$is_junk" == true ]]; then
            log "FILTRO: Transcripción descartada por ser basura/silencio: '$query'"
            rm -f "$audio_file" "$LOCK_FILE"
            return
        fi
        log "FILTRO: Transcripción válida → '$query'"

        # ── Wake Word Check ──────────────────────────────────────────────────
        local ww_mode_file="$WORKSPACE_DIR/.wakeword_mode"
        if [ -f "$ww_mode_file" ] && [ "$(cat "$ww_mode_file" 2>/dev/null)" = "true" ]; then
            local session_active=false
            local session_timeout=45
            local session_file="/tmp/alberth_session_active"
            
            if [ -f "$session_file" ]; then
                local now last_active diff
                now=$(date +%s)
                last_active=$(stat -f "%m" "$session_file" 2>/dev/null || stat -c "%Y" "$session_file" 2>/dev/null || echo 0)
                diff=$((now - last_active))
                if [ $diff -lt $session_timeout ]; then
                    session_active=true
                    log "Sesión de voz activa (última actividad hace ${diff}s)."
                fi
            fi

            local query_lower_trigger
            query_lower_trigger=$(echo "$query" | tr '[:upper:]' '[:lower:]')

            if [[ "$query_lower_trigger" =~ (alberth|alberto|albert|oye\ alberth|hey\ alberth) ]] || [ "$session_active" = true ]; then
                touch "$session_file"
                # Limpiar palabra clave del inicio
                query=$(echo "$query" | sed -E 's/^(alberth|alberto|albert|oye alberth|hey alberth)[, ]*//I')
                log "Wake Word detectado. Query procesada: '$query'"
            else
                log "Ignorando audio: Wake word no detectado y sesión inactiva."
                rm -f "$LOCK_FILE"
                rm -f "$audio_file"
                return
            fi
        else
            # Si no está en modo wake-word, igual actualizamos el archivo de sesión para que si se cambia de modo haya registro
            touch "/tmp/alberth_session_active" 2>/dev/null
        fi

        # Mover audio procesado
        mkdir -p "$INPUT_DIR/processed"
        mv "$audio_file" "$INPUT_DIR/processed/${base_name}.processed_$(date +%Y%m%d_%H%M%S)${audio_file##*.}" 2>/dev/null
    else
        # Para texto, guardamos el query en txt_file
        echo "$query" > "$txt_file"
    fi

    # ── Fast-Cache: Consultas instantáneas de Hora y Fecha (<15ms) ───────
    local query_clean
    query_clean=$(echo "$query" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-zA-Z0-9áéíóúñÁÉÍÓÚÑ ]//g' | tr '[:upper:]' '[:lower:]' | sed -E 's/^[[:space:]]*//;s/[[:space:]]*$//')
    if [[ "$query_clean" =~ ^(qu|que)\ (hora\ es|fecha\ es\ hoy|da\ es\ hoy)|^(dame\ la\ (hora|fecha))|^(hora|fecha)\ actual$ ]]; then
        local now_str
        now_str=$(date '+%A, %d de %B de %Y a las %H:%M')
        local response="Señor, hoy es ${now_str}."
        log "FAST-CACHE OK → $response"
        echo "$response" > "$response_txt"
        python3 "$WORKSPACE_DIR/alberth_tts_premium.py" "$response" "$response_mp3" >>"$LOGFILE" 2>&1
        afplay "$response_mp3" 2>/dev/null &
        [ "$is_text_only" = true ] && echo "$response"
        rm -f "$LOCK_FILE"
        return
    fi

    # ── PASO 1.5: TÁLAMO — Pre-enrutamiento inteligente ──────────────────
    # El Tálamo clasifica semánticamente la query para detectar habilidades
    # especializadas ANTES del despacho a la IA principal.
    local talamo_json=""
    local talamo_tipo="GENERAL_TALK"

    log "PASO 1.5: Consultando Tálamo para clasificación semántica..."
    talamo_json=$(python3 "$WORKSPACE_DIR/alberth_talamo.py" "$query" 2>>"$LOGFILE")

    if [[ -n "$talamo_json" ]]; then
        talamo_tipo=$(echo "$talamo_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tipo_tarea','GENERAL_TALK'))" 2>/dev/null)
        log "Tálamo → Tipo: $talamo_tipo"
    else
        log "WARN: Tálamo sin respuesta. Enrutamiento por regex activado."
    fi

    # ── Rama 0a: FINANZAS — Criptomonedas, Acciones, Divisas ────────────
    if [[ "$talamo_tipo" == "FINANCE_TICKER" ]]; then
        log "Tálamo → Enrutando a FINANCE HELPER..."
        local talamo_args
        talamo_args=$(echo "$talamo_json" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); args=d.get('argumentos',{}); q=args.get('simbolo',args.get('activo','$query')); print(q)" 2>/dev/null)
        [[ -z "$talamo_args" ]] && talamo_args="$query"

        local finance_out
        finance_out=$(python3 "$WORKSPACE_DIR/alberth_finance_helper.py" "$talamo_args" 2>>"$LOGFILE")
        local finance_msg
        finance_msg=$(echo "$finance_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Error consultando finanzas'))" 2>/dev/null)

        # Si hay resultado, generar respuesta directa sin pasar por el agente
        if [[ -n "$finance_msg" ]]; then
            response="$finance_msg"
            log "FINANCE OK → $response"
            echo "$response" > "$response_txt"
            python3 "$WORKSPACE_DIR/alberth_tts_premium.py" "$response" "$response_mp3" >>"$LOGFILE" 2>&1
            afplay "$response_mp3" 2>/dev/null &
            [ "$is_text_only" = true ] && echo "$response"
            log "--- PIPELINE COMPLETADO (FINANCE) ---"
            rm -f "$LOCK_FILE"
            return
        fi
    fi

    # ── Rama 0b: IMÁGENES — Generación artística con Pollinations AI ─────
    if [[ "$talamo_tipo" == "IMAGE_GEN" ]]; then
        log "Tálamo → Enrutando a IMAGE HELPER..."
        local talamo_prompt
        talamo_prompt=$(echo "$talamo_json" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); args=d.get('argumentos',{}); p=args.get('descripcion_imagen',args.get('prompt','$query')); print(p)" 2>/dev/null)
        [[ -z "$talamo_prompt" ]] && talamo_prompt="$query"

        local img_out
        img_out=$(python3 "$WORKSPACE_DIR/alberth_image_helper.py" "$talamo_prompt" 2>>"$LOGFILE")
        local img_msg
        img_msg=$(echo "$img_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','Imagen generada'))" 2>/dev/null)

        response="Señor, ${img_msg:-su imagen está siendo procesada. La abriré en Preview en un momento.}"
        log "IMAGE OK → $response"
        echo "$response" > "$response_txt"
        python3 "$WORKSPACE_DIR/alberth_tts_premium.py" "$response" "$response_mp3" >>"$LOGFILE" 2>&1
        afplay "$response_mp3" 2>/dev/null &
        [ "$is_text_only" = true ] && echo "$response"
        log "--- PIPELINE COMPLETADO (IMAGE_GEN) ---"
        rm -f "$LOCK_FILE"
        return
    fi

    # ── PASO 2: Detección por contexto visual y ramas especializadas ───────
    log "PASO 2: Consultando al Agente Alberth..."

    # Inicializar contextos vacíos
    local visual_context=""
    local file_context=""
    local youtube_context=""
    local system_context=""
    local search_context=""
    local is_talamo_routed=false

    local query_lower
    query_lower=$(echo "$query" | tr '[:upper:]' '[:lower:]')

    # --- ENRUTAMIENTO POR TÁLAMO ---
    if [[ "$talamo_tipo" == "VISION_SCREEN" ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a VISION_SCREEN..."
        
        # ── Sub-rama 1a: MODO DIFF — "qué cambió" ─────
        if [[ "$query_lower" =~ (qué\ cambió|que\ cambio|cambió\ algo|cambio\ algo|qué\ pasó|que\ paso|hay\ algo\ nuevo|algo\ nuevo) ]]; then
            log "Activador DIFF de pantalla detectado. Comparando capturas..."
            local diff_interval=8
            local screen_desc
            screen_desc=$(python3 "$WORKSPACE_DIR/alberth_screen_copilot.py" --diff "$diff_interval" 2>/dev/null)
            if [[ -n "$screen_desc" ]]; then
                log "Análisis DIFF completado."
                visual_context="[ANÁLISIS DIFERENCIAL DE PANTALLA: Comparaste dos capturas separadas por ${diff_interval} segundos. Descripción de los cambios detectados: ${screen_desc}] "
            else
                log "WARN: No se pudo realizar análisis diferencial."
            fi

        # ── Sub-rama 1b: MODO COPILOTO CONTINUO — "activa copiloto" ──────
        elif [[ "$query_lower" =~ (activa\ el\ copiloto|inicia\ el\ copiloto|copiloto\ de\ pantalla|empieza\ a\ monitorear|monitorea\ mi\ pantalla|modo\ copiloto) ]]; then
            log "Activando COPILOTO DE PANTALLA en modo daemon..."
            local watch_interval=30
            if [[ "$query_lower" =~ cada\ ([0-9]+)\ seg ]]; then
                watch_interval="${BASH_REMATCH[1]}"
            fi
            python3 "$WORKSPACE_DIR/alberth_screen_copilot.py" --watch "$watch_interval" >> "$LOGFILE" 2>&1 &
            visual_context="[SISTEMA: Se ha activado el Copiloto de Pantalla en modo daemon. Alberth ahora analizará tu pantalla automáticamente cada ${watch_interval} segundos. Los análisis quedarán guardados en voice_exchange/copilot_latest.txt. Para detenerlo, dile: 'desactiva el copiloto'.] "

        # ── Sub-rama 1c: DETENER COPILOTO ─────────────────────────────────
        elif [[ "$query_lower" =~ (desactiva\ el\ copiloto|detén\ el\ copiloto|detén\ el\ monitoreo|para\ el\ copiloto|stop\ copiloto) ]]; then
            log "Deteniendo COPILOTO DE PANTALLA..."
            python3 "$WORKSPACE_DIR/alberth_screen_copilot.py" --stop 2>/dev/null
            visual_context="[SISTEMA: El Copiloto de Pantalla ha sido desactivado correctamente.] "

        # ── Sub-rama 1d: SNAPSHOT ESTÁNDAR ──────
        else
            log "Iniciando captura de pantalla..."
            local screen_desc
            screen_desc=$(python3 "$WORKSPACE_DIR/alberth_screen_copilot.py" "$query" 2>/dev/null)
            if [[ -n "$screen_desc" ]]; then
                log "Análisis de pantalla completado con éxito."
                visual_context="[CONTEXTO DE PANTALLA: El usuario te ha pedido que analices su pantalla de trabajo. La herramienta de visión describe lo siguiente: ${screen_desc}] "
            else
                log "WARN: No se pudo obtener descripción de pantalla."
            fi
        fi

    elif [[ "$talamo_tipo" == "VISION_CAMERA" ]] || [[ "$query_lower" =~ (te\ presento\ a|mira\ a|quién\ está\ frente|activa\ la\ cámara|quien\ esta\ frente) ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a VISION_CAMERA (Reconocimiento Visual)..."
        local vision_desc=""

        # Detección de frase de presentación/registro ("te presento a mi hija Danna", "te presento a Juan")
        if [[ "$query_lower" =~ (te\ presento\ a|ella\ es|él\ es)\ ([a-zA-ZáéíóúñÁÉÍÓÚÑ ]+) ]]; then
            local person_name="${BASH_REMATCH[2]}"
            log "Detector de presentación visual → Registrando a: '$person_name'"
            vision_desc=$(python3 "$WORKSPACE_DIR/alberth_vision.py" --enroll "$person_name" 2>/dev/null)
        else
            log "Detección y reconocimiento visual de escena..."
            vision_desc=$(python3 "$WORKSPACE_DIR/alberth_vision.py" --recognize "$query" 2>/dev/null)
        fi

        if [[ -n "$vision_desc" ]]; then
            log "Análisis visual completado con éxito."
            visual_context="[CONTEXTO VISUAL: Capturaste la cámara FaceTime del usuario. Resultado del análisis visual: ${vision_desc}. Si identificaste a una persona conocida (ej. Danna), salúdala por su nombre de forma cálida y profesional.] "
        else
            log "WARN: No se pudo obtener descripción visual de la cámara."
        fi

    elif [[ "$talamo_tipo" == "READ_PDF" ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a READ_PDF..."
        local pdf_out
        pdf_out=$(uv run "$WORKSPACE_DIR/alberth_pdf_helper.py" "$query" 2>&1)
        local pdf_status=$?
        if [ $pdf_status -eq 0 ]; then
            log "Lectura de PDF completada con éxito."
            file_context="[CONTEXTO DE ARCHIVO PDF: Se localizó un PDF en su sistema y se extrajo el texto relevante. Aquí está la información del archivo y el texto:
${pdf_out}
Presenta al Señor un resumen detallado y estructurado de este archivo en base a su contenido, manteniendo tu personalidad semiformal, analítica y directa.] "
        else
            log "WARN: No se pudo obtener información del PDF (código de salida: $pdf_status)."
            if [ $pdf_status -eq 2 ]; then
                file_context="[SISTEMA: El usuario solicitó resumir un PDF, pero el archivo localizado está vacío o es una imagen escaneada sin capa de texto legible. Indícale amigablemente al Señor que el PDF es una imagen escaneada y que requieres que te lo envíe en formato de texto o que lo intente de otra forma.] "
            else
                file_context="[SISTEMA: El usuario solicitó resumir un PDF, pero no se encontró ningún archivo PDF reciente en Downloads o Desktop. Pídele al Señor que te proporcione el nombre del archivo o que lo coloque en la carpeta de Descargas.] "
            fi
        fi

    elif [[ "$talamo_tipo" == "YOUTUBE" ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a YOUTUBE..."
        local yt_out
        yt_out=$(python3 "$WORKSPACE_DIR/alberth_youtube_helper.py" "$query" 2>&1)
        local yt_status=$?
        if [ $yt_status -eq 0 ]; then
            log "Búsqueda y apertura en YouTube completada."
            youtube_context="[CONTEXTO DE SISTEMA: Ejecutaste con éxito el script de YouTube. Resultados:
${yt_out}
Confirma verbalmente al Señor de forma natural y cálida que has buscado y abierto el video correspondiente en su navegador.] "
        else
            log "WARN: Falló la apertura de YouTube."
            youtube_context="[SISTEMA: Hubo un problema al intentar buscar o abrir YouTube. Infórmale al Señor amigablemente.] "
        fi

    elif [[ "$talamo_tipo" == "SYSTEM_UTILS" || "$talamo_tipo" == "REMINDER_TIMER" ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a SYSTEM_UTILS..."
        local sys_out
        sys_out=$(python3 "$WORKSPACE_DIR/alberth_system_helper.py" "$query" 2>&1)
        local sys_status=$?
        if [ $sys_status -eq 0 ]; then
            local sys_accion sys_resultado
            sys_accion=$(echo "$sys_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('accion',''))" 2>/dev/null)
            sys_resultado=$(echo "$sys_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resultado',''))" 2>/dev/null)
            log "SISTEMA OK → Acción: $sys_accion | Resultado: $sys_resultado"
            system_context="[CONTEXTO DE CONTROL DE SISTEMA: Se ejecutó exitosamente la acción '${sys_accion}'. Resultado: ${sys_resultado}. Confirma al Señor de forma directa y natural que lo has completado, con tu tono semiformal y cálido.] "
        else
            local sys_resultado
            sys_resultado=$(echo "$sys_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resultado','Error desconocido'))" 2>/dev/null)
            [[ -z "$sys_resultado" ]] && sys_resultado="$sys_out"
            log "WARN: Sistema helper devolvió código $sys_status. Resultado: $sys_resultado"
            system_context="[CONTEXTO DE CONTROL DE SISTEMA: Se intentó ejecutar la acción de sistema pero ocurrió un problema. Detalle: ${sys_resultado}. Comunica esto al Señor de forma clara y ayúdalo a resolverlo.] "
        fi

    elif [[ "$talamo_tipo" == "WEB_SEARCH" ]]; then
        is_talamo_routed=true
        log "Tálamo → Enrutando a WEB_SEARCH..."
        local search_out
        search_out=$(python3 "$WORKSPACE_DIR/alberth_search_helper.py" "$query" 2>&1)
        local search_status=$?
        if [ $search_status -eq 0 ]; then
            local search_res
            search_res=$(echo "$search_out" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('resultado',''))" 2>/dev/null)
            log "BÚSQUEDA OK"
            search_context="[CONTEXTO OBTENIDO DE INTERNET:
${search_res}
Usa esta información de forma analítica para responder al Señor con precisión, manteniendo tu tono cálido y directo.] "
        else
            log "WARN: Falló la búsqueda web."
        fi
    fi

    local soul_context=""
    if [[ -f "$WORKSPACE_DIR/SOUL.md" ]]; then
        soul_context="[INSTRUCCIONES DE PERSONALIDAD Y REGLAS DE COMPORTAMIENTO (SOUL.md):
$(cat "$WORKSPACE_DIR/SOUL.md")
] "
    fi

    local agent_message="${soul_context}${memory_context}${visual_context}${file_context}${youtube_context}${system_context}${search_context}${query}"
    local start_ts=$(date +%s%3N 2>/dev/null || echo $(date +%s)000)
    local model_used="nvidia/z-ai/glm-5.1"
    local agent_success=false

    # Sanitizar query de entrada (Anti-RCE)
    query=$(sanitize_input "$query")

    if is_online; then
        if openclaw agent \
            --agent main \
            --message "$agent_message" \
            --json > "$temp_agent_json" 2>&1; then

            response=$(jq -r '.result.payloads[0].text // ""' "$temp_agent_json" 2>/dev/null)
            rm -f "$temp_agent_json"

            # Limpiar prefijos de error de openclaw
            response=$(echo "$response" | sed 's/^\[assistant turn failed before producing content\]//g' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')

            if [[ -n "$response" && "$response" != "null" ]]; then
                agent_success=true
                log "AGENT CLOUD OK → Respuesta (${#response} chars)"
            fi
        fi
    else
        log "🌐 MODO OFFLINE DETECTADO (Sin Internet) — Conmutando a Ollama Local (qwen2.5:3b)..."
    fi

    # Fallback local con Ollama si falló la nube o estamos offline
    if [[ "$agent_success" == false ]]; then
        log "OFFLINE FALLBACK → Generando respuesta local con Ollama (qwen2.5:3b)..."
        model_used="ollama/qwen2.5:3b-local"
        local payload
        payload=$(jq -n --arg prompt "$agent_message" '{model: "qwen2.5:3b", prompt: $prompt, stream: false}')
        response=$(curl -s -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d "$payload" | jq -r '.response // ""' 2>/dev/null)

        if [[ -z "$response" || "$response" == "null" ]]; then
            log "WARN: Ollama local no disponible o sin respuesta. Usando mensaje de resiliencia."
            response="Señor, estoy operando en modo offline. Los servicios en la nube no están disponibles y Ollama está inactivo."
        else
            log "OFFLINE OLLAMA OK → Respuesta local (${#response} chars)"
        fi
    fi

    local end_ts=$(date +%s%3N 2>/dev/null || echo $(date +%s)000)
    local latency_ms=$((end_ts - start_ts))

    echo "$response" > "$response_txt"

    # Auditoría y Trazabilidad Estructurada + Guardado en Memoria
    python3 "$WORKSPACE_DIR/alberth_memory.py" --audit "orquestador" "$query" "$model_used" "$latency_ms" >> "$LOGFILE" 2>&1 &
    python3 "$WORKSPACE_DIR/alberth_memory.py" --save "$query" "$response" >> "$LOGFILE" 2>&1 &

    # ── PASO 3: TTS — Síntesis de voz ────────────────────────────────────
    # Prioridad 1: edge-tts Premium (Microsoft, alta calidad, sin costo)
    log "PASO 3: Generando audio de respuesta (TTS Premium edge-tts)..."
    if python3 "$WORKSPACE_DIR/alberth_tts_premium.py" "$response" "$response_mp3" >> "$LOGFILE" 2>&1; then
        log "TTS PREMIUM OK → Audio: $response_mp3 (edge-tts)"
    else
        # Prioridad 2: OpenClaw TTS (API cloud)
        log "WARN: edge-tts falló. Intentando OpenClaw TTS..."
        if openclaw infer tts convert \
            --text "$response" \
            --output "$response_mp3" >> "$LOGFILE" 2>&1; then
            log "TTS OPENCLAW OK → Audio: $response_mp3"
        else
            # Prioridad 3: macOS say (último recurso, calidad baja)
            log "WARN: OpenClaw TTS falló. Usando fallback macOS 'say'."
            say -v Mónica -o "$response_mp3" -- "$response" 2>/dev/null || {
                log "ERROR: Todos los métodos TTS fallaron."
                rm -f "$LOCK_FILE"
                return
            }
            log "TTS FALLBACK OK → Audio generado con 'say -v Mónica'"
        fi
    fi

    # ── PASO 4: REPRODUCCIÓN — Respuesta audible ─────────────────────────
    log "PASO 4: Reproduciendo respuesta..."
    # Señal de MUTING: le dice al voice_server que pause la captura del mic
    # para evitar que grabe la propia respuesta de Alberth (eco acústico).
    local mute_signal="$VOICE_DIR/.alberth_speaking"
    touch "$mute_signal"
    afplay "$response_mp3" 2>/dev/null
    # Esperar un momento después de que termine afplay para que el eco se disipe
    sleep 0.5
    rm -f "$mute_signal"

    # Si es modo texto, imprimimos la respuesta en stdout para que el web server la capture
    if [ "$is_text_only" = true ]; then
        echo "$response"
    fi

    log "--- PIPELINE COMPLETADO ---"

    # Liberar lock
    rm -f "$LOCK_FILE"
}

# --- Modo de ejecución ---
if [[ "$1" == "--text" ]]; then
    run_pipeline "--text" "$2"
    exit 0
fi

# Si se llama con un argumento, procesar ese archivo directamente (modo test)
if [[ -n "$1" && -f "$1" ]]; then
    log "Modo TEST: procesando archivo directo → $1"
    run_pipeline "$1"
    exit 0
fi

# --- Modo daemon: procesar archivos existentes al inicio ---
log "Procesando archivos existentes en input/..."
for audio_file in "$INPUT_DIR"/*.{mp3,wav,m4a,aiff,flac,ogg}; do
    [[ -f "$audio_file" ]] && run_pipeline "$audio_file"
done

# --- Modo daemon: watcher continuo con fswatch ---
log "Iniciando watcher fswatch en modo continuo..."
fswatch \
    --event Created \
    --event MovedTo \
    --latency 1 \
    --recursive \
    "$INPUT_DIR" | while read -r changed_file; do
        # Solo procesar archivos de audio (no subdirectorios ni archivos procesados)
        if [[ "$changed_file" =~ \.(mp3|wav|m4a|aiff|flac|ogg)$ ]] && \
           [[ ! "$changed_file" =~ /processed/ ]] && \
           [[ ! "$changed_file" =~ _response\. ]]; then
            log "fswatch detectó nuevo archivo: $changed_file"
            # Pequeña espera para asegurar que el archivo esté completamente escrito
            sleep 1
            run_pipeline "$changed_file"
        fi
    done