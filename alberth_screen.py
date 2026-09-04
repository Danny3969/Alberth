#!/usr/bin/env python3
# =============================================================================
# ALBERTH SCREEN — Módulo de Captura y Descripción de Pantalla
# Toma una captura de pantalla silenciosa en macOS y la describe usando
# google/gemini-2.5-flash a través de la API de OpenRouter.
# =============================================================================

import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error

# Rutas
WORKSPACE_DIR = "/Users/digitalspace/.openclaw/workspace"
IMAGE_PATH = os.path.join(WORKSPACE_DIR, "voice_exchange", "alberth_screen.jpg")
CONFIG_PATH = os.path.expanduser("~/.openclaw/openclaw.json")

def log(msg):
    print(f"[Screen] {msg}", file=sys.stderr)

def get_api_key():
    # Prioridad 1: variable de entorno (sourceada desde ~/.openclaw/.env)
    env_key = os.environ.get("NVIDIA_API_KEY")
    if env_key:
        return env_key

    # Prioridad 2: leer desde openclaw.json (fallback)
    if not os.path.exists(CONFIG_PATH):
        log(f"Error: No se encontró openclaw.json en {CONFIG_PATH}")
        return None
        
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        api_key = config.get("models", {}).get("providers", {}).get("nvidia", {}).get("apiKey")
        if api_key:
            return api_key
            
        api_key = config.get("env", {}).get("NVIDIA_API_KEY")
        if api_key:
            return api_key
            
        log("Error: No se encontró la API Key de NVIDIA en openclaw.json")
        return None
    except Exception as e:
        log(f"Error al leer openclaw.json: {e}")
        return None

def get_vision_model():
    """Retorna el modelo de visión de NVIDIA NIM para análisis de pantalla."""
    return "meta/llama-3.2-11b-vision-instruct"

def capture_screen():
    # Asegurar directorio de destino
    os.makedirs(os.path.dirname(IMAGE_PATH), exist_ok=True)
    
    if os.path.exists(IMAGE_PATH):
        try:
            os.remove(IMAGE_PATH)
        except Exception:
            pass

    log("Capturando la pantalla principal de macOS...")
    # -x: captura silenciosa (sin sonido de obturador)
    cmd = ["screencapture", "-x", IMAGE_PATH]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        if os.path.exists(IMAGE_PATH) and os.path.getsize(IMAGE_PATH) > 0:
            log("Captura de pantalla realizada exitosamente.")
            return True
        else:
            log("Error: No se pudo generar el archivo de captura de pantalla.")
            log(result.stderr.decode('utf-8', errors='ignore'))
            return False
    except subprocess.TimeoutExpired:
        log("Error: Tiempo de espera agotado al capturar la pantalla.")
        return False
    except Exception as e:
        log(f"Excepción al capturar la pantalla: {e}")
        return False

def describe_screen(api_key, custom_prompt=None):
    if not os.path.exists(IMAGE_PATH):
        log("Error: Archivo de imagen no encontrado para descripción.")
        return None

    try:
        with open(IMAGE_PATH, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        log(f"Error al codificar imagen a base64: {e}")
        return None

    # Prompt base en español enfocado en productividad
    prompt = (
        "Analiza detalladamente esta captura de mi pantalla. Identifica qué aplicaciones "
        "o IDEs están abiertos, qué código o texto se visualiza, o qué mensajes de error "
        "o consola aparecen. Sé analítico y conciso. Responde en español."
    )
    if custom_prompt:
        prompt = custom_prompt

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": get_vision_model(),
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }

    log(f"Enviando solicitud a NVIDIA NIM ({get_vision_model()})...")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            description = res_json['choices'][0]['message']['content']
            return description.strip()
    except urllib.error.HTTPError as e:
        log(f"Error HTTP de NVIDIA NIM: {e.code} - {e.reason}")
        try:
            error_details = e.read().decode('utf-8')
            log(f"Detalles del error: {error_details}")
        except Exception:
            pass
        return None
    except Exception as e:
        log(f"Excepción al conectar con NVIDIA NIM: {e}")
        return None

def main():
    api_key = get_api_key()
    if not api_key:
        print("Error: Clave API no disponible.")
        sys.exit(1)

    custom_prompt = None
    if len(sys.argv) > 1:
        custom_prompt = " ".join(sys.argv[1:])

    if capture_screen():
        description = describe_screen(api_key, custom_prompt)
        if description:
            print(description)
            sys.exit(0)
            
    print("Error: No se pudo realizar el análisis de pantalla.")
    sys.exit(1)

if __name__ == "__main__":
    main()
