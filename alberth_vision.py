#!/usr/bin/env python3
# =============================================================================
# ALBERTH VISION — Módulo de Captura y Descripción Visual
# Provider: NVIDIA NIM (integrate.api.nvidia.com)
# Modelo:   meta/llama-3.2-11b-vision-instruct  (fallback: phi-4-multimodal)
# API Key:  NVIDIA_API_KEY desde ~/.openclaw/.env
# =============================================================================

import os
import sys
import json
import base64
import subprocess
import urllib.request
import urllib.error
import time

# ── Rutas ────────────────────────────────────────────────────────────────────
WORKSPACE_DIR = "/Users/digitalspace/.openclaw/workspace"
IMAGE_PATH    = os.path.join(WORKSPACE_DIR, "voice_exchange", "alberth_vision.jpg")
CONFIG_PATH   = os.path.expanduser("~/.openclaw/openclaw.json")
ENV_PATH      = os.path.expanduser("~/.openclaw/.env")

# ── Configuración de NVIDIA NIM ───────────────────────────────────────────────
NVIDIA_API_URL    = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL_PRIMARY  = "meta/llama-3.2-11b-vision-instruct"
NVIDIA_MODEL_FALLBACK = "microsoft/phi-4-multimodal-instruct"
MAX_TOKENS = 500


def log(msg):
    print(f"[Vision] {msg}", file=sys.stderr)


def _source_env():
    """Carga variables de ~/.openclaw/.env en el entorno del proceso actual."""
    if not os.path.exists(ENV_PATH):
        return
    try:
        with open(ENV_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if "=" in line and not line.startswith("#"):
                    key, _, val = line.partition("=")
                    # Eliminar comillas opcionales
                    val = val.strip().strip('"').strip("'")
                    if key and val:
                        os.environ.setdefault(key.strip(), val)
    except Exception as e:
        log(f"WARN: No se pudo leer {ENV_PATH}: {e}")


def get_nvidia_api_key():
    """Lee NVIDIA_API_KEY desde entorno o ~/.openclaw/.env"""
    _source_env()
    key = os.environ.get("NVIDIA_API_KEY", "")
    if key:
        return key

    # Fallback: leer desde openclaw.json
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        key = (config.get("models", {})
                     .get("providers", {})
                     .get("nvidia", {})
                     .get("apiKey", ""))
        if key:
            return key
    except Exception:
        pass

    log("Error: No se encontró NVIDIA_API_KEY en el entorno ni en openclaw.json")
    return None


def capture_image():
    """Captura un frame de la cámara integrada con ffmpeg."""
    os.makedirs(os.path.dirname(IMAGE_PATH), exist_ok=True)

    if os.path.exists(IMAGE_PATH):
        try:
            os.remove(IMAGE_PATH)
        except Exception:
            pass

    log("Capturando frame de la cámara con ffmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "avfoundation",
        "-framerate", "30",
        "-video_size", "1280x720",
        "-i", "0",
        "-vframes", "1",
        "-update", "1",
        IMAGE_PATH
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12
        )
        if os.path.exists(IMAGE_PATH) and os.path.getsize(IMAGE_PATH) > 0:
            log("Captura realizada exitosamente.")
            return True
        else:
            log("Error: No se pudo generar el archivo de imagen.")
            log(result.stderr.decode("utf-8", errors="ignore")[-500:])
            return False
    except subprocess.TimeoutExpired:
        log("Error: Tiempo de espera agotado al acceder a la cámara.")
        return False
    except Exception as e:
        log(f"Excepción al capturar imagen: {e}")
        return False


def describe_image(api_key, custom_prompt=None, model=NVIDIA_MODEL_PRIMARY):
    """Envía la imagen a NVIDIA NIM y devuelve la descripción."""
    if not os.path.exists(IMAGE_PATH):
        log("Error: Archivo de imagen no encontrado.")
        return None

    try:
        with open(IMAGE_PATH, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        log(f"Error al codificar imagen: {e}")
        return None

    prompt = (
        custom_prompt or
        "Identifica objetos, personas, paisajes y todo lo que está alrededor "
        "en esta imagen. Sé descriptivo pero conciso. Responde en español."
    )

    # NVIDIA NIM acepta image_url con data URI
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.3
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    log(f"Enviando solicitud a NVIDIA NIM ({model})...")
    req = urllib.request.Request(
        NVIDIA_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            description = res_json["choices"][0]["message"]["content"]
            log(f"Respuesta recibida ({len(description)} chars).")
            return description.strip()

    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        log(f"Error HTTP {e.code} de NVIDIA NIM: {e.reason}")
        log(f"Detalles: {error_body[:300]}")

        # Intentar con modelo de fallback si el primario falla
        if model == NVIDIA_MODEL_PRIMARY and e.code in (404, 400, 422):
            log(f"Intentando con modelo fallback: {NVIDIA_MODEL_FALLBACK}")
            return describe_image(api_key, custom_prompt, model=NVIDIA_MODEL_FALLBACK)
        return None

    except Exception as e:
        log(f"Excepción al conectar con NVIDIA NIM: {e}")
        return None


def enroll_person(name: str, api_key: str) -> bool:
    """Captura un frame y registra visualmente a una persona conocida en la memoria de Alberth."""
    log(f"Iniciando registro visual para: '{name}'...")
    if not capture_image():
        log("Error al capturar frame para registro.")
        return False

    prompt = (
        f"Describe detalladamente el rostro, peinado, características físicas clave y ropa de la persona "
        f"que está frente a la cámara. Esta persona es '{name}'. Resume en 2 oraciones sus rasgos únicos."
    )
    desc = describe_image(api_key, custom_prompt=prompt)
    if not desc:
        return False

    # Guardar en memoria persistente de hechos
    try:
        sys.path.insert(0, WORKSPACE_DIR)
        from alberth_memory import save_conversation, get_db
        conn = get_db()
        fact_text = f"Persona conocida: {name} | Rasgos visuales: {desc}"
        conn.execute(
            "INSERT OR REPLACE INTO user_facts (category, fact, mode) VALUES (?, ?, ?)",
            ("personas_conocidas", fact_text, "personal")
        )
        conn.commit()
        conn.close()
        log(f"✅ Persona '{name}' registrada exitosamente en memoria visual.")
        return True
    except Exception as e:
        log(f"Error al guardar hecho visual: {e}")
        return False


def recognize_known_people(api_key: str, custom_query: str = "") -> str:
    """Captura un frame y verifica si hay personas conocidas registradas en user_facts."""
    if not capture_image():
        return ""

    # Cargar personas conocidas de la memoria
    known_facts = []
    try:
        sys.path.insert(0, WORKSPACE_DIR)
        from alberth_memory import get_db
        conn = get_db()
        rows = conn.execute("SELECT fact FROM user_facts WHERE category = 'personas_conocidas'").fetchall()
        known_facts = [r["fact"] for r in rows]
        conn.close()
    except Exception:
        pass

    known_context = ""
    if known_facts:
        known_context = "\nPersona(s) conocida(s) registrada(s) previamente:\n" + "\n".join(f"- {f}" for f in known_facts)

    prompt = (
        f"Analiza la imagen actual de la cámara. {known_context}\n"
        f"1. Identifica si alguna de las personas en la imagen coincide con las personas conocidas registradas.\n"
        f"2. {custom_query or 'Describe la escena, qué hace la persona y si debes saludarla por su nombre.'}\n"
        f"Sé conciso y responde en español."
    )
    return describe_image(api_key, custom_prompt=prompt) or ""


def main():
    api_key = get_nvidia_api_key()
    if not api_key:
        print("Error: NVIDIA_API_KEY no disponible.")
        sys.exit(1)

    import argparse
    parser = argparse.ArgumentParser(description="Alberth Vision & Face Recognition")
    parser.add_argument("--enroll", metavar="NOMBRE", help="Registra a una persona frente a la cámara")
    parser.add_argument("--recognize", action="store_true", help="Reconoce personas conocidas frente a la cámara")
    parser.add_argument("query", nargs="*", help="Query visual personalizada")
    args = parser.parse_args()

    if args.enroll:
        ok = enroll_person(args.enroll, api_key)
        if ok:
            print(f"Señor, he registrado visualmente a {args.enroll} en mi memoria.")
        else:
            print(f"No pude registrar visualmente a {args.enroll}. Revisa la cámara.")
        sys.exit(0 if ok else 1)

    if args.recognize:
        query_text = " ".join(args.query) if args.query else ""
        desc = recognize_known_people(api_key, query_text)
        if desc:
            print(desc)
            sys.exit(0)
        else:
            print("No se pudo reconocer la escena visual.")
            sys.exit(1)

    custom_prompt = " ".join(args.query) if args.query else None

    # Si la imagen existe y tiene menos de 25s, usarla directamente
    use_existing = False
    if os.path.exists(IMAGE_PATH) and os.path.getsize(IMAGE_PATH) > 0:
        age = time.time() - os.path.getmtime(IMAGE_PATH)
        if age < 25:
            log(f"Utilizando imagen existente (antigüedad: {age:.1f}s)")
            use_existing = True

    if use_existing or capture_image():
        description = describe_image(api_key, custom_prompt)
        if description:
            print(description)
            sys.exit(0)

    print("Error: No se pudo realizar el análisis de visión.")
    sys.exit(1)


if __name__ == "__main__":
    main()
