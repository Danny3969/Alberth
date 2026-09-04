#!/usr/bin/env python3
# =============================================================================
# ALBERTH TÁLAMO — Enrutador Inteligente (v3 — Ollama Local)
#
# Usa gemma:2b via Ollama (local, rápido, sin latencia cloud) para clasificar
# semánticamente la query del usuario. Fallback a openclaw si Ollama falla.
# =============================================================================

import sys
import json
import urllib.request
import urllib.error
import subprocess

# ─── Configuración ────────────────────────────────────────────────────────────
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b"           # Rápido, ligero, suficiente para routing

SYSTEM_PROMPT = """Clasifica la orden del usuario en una de estas categorías y devuelve JSON puro (sin markdown).

Categorías disponibles:
FINANCE_TICKER = precio de crypto (bitcoin, ethereum, solana), acción (apple, tesla, nvidia), o divisa (euro, peso)
IMAGE_GEN = crear, dibujar, generar, diseñar una imagen o ilustración
SYSTEM_UTILS = control del Mac: volumen, brillo, apps, terminal, archivos, screenshot, modo oscuro, no molestar
REMINDER_TIMER = recordatorios, alarmas, timers ("recuérdame en X minutos")
WEB_SEARCH = buscar en internet, clima, Wikipedia, noticias, clima de hoy, qué temperatura hace
VISION_SCREEN = analizar la pantalla, ver lo que está abierto en la pantalla de la computadora, ver el código, errores del IDE, vscode o "mira mi pantalla", "qué tengo abierto", "qué se ve"
VISION_CAMERA = ver el entorno físico usando la cámara web web, fotos, o preguntas como "¿qué ves?", "mírame", "describe mi alrededor"
READ_PDF = leer, resumir, analizar o buscar información en un archivo PDF o documento local
YOUTUBE = abrir o reproducir videos de YouTube
GENERAL_TALK = todo lo demás: conversación general, código, explicaciones, preguntas conceptuales

Devuelve solo este JSON:
{"tipo_tarea":"<CATEGORIA>","habilidad_requerida":"<skill>","argumentos":{<args>}}

Ejemplos reales:
Orden: "cuánto vale el bitcoin" → {"tipo_tarea":"FINANCE_TICKER","habilidad_requerida":"finance","argumentos":{"activo":"bitcoin"}}
Orden: "precio de Apple" → {"tipo_tarea":"FINANCE_TICKER","habilidad_requerida":"finance","argumentos":{"activo":"apple"}}
Orden: "dibuja un gato astronauta" → {"tipo_tarea":"IMAGE_GEN","habilidad_requerida":"image_gen","argumentos":{"descripcion_imagen":"gato astronauta"}}
Orden: "genera imagen de ciudad futurista" → {"tipo_tarea":"IMAGE_GEN","habilidad_requerida":"image_gen","argumentos":{"descripcion_imagen":"ciudad futurista"}}
Orden: "sube el volumen" → {"tipo_tarea":"SYSTEM_UTILS","habilidad_requerida":"system","argumentos":{"accion":"subir_volumen"}}
Orden: "cuál es el clima en Madrid" → {"tipo_tarea":"WEB_SEARCH","habilidad_requerida":"search","argumentos":{"query":"clima Madrid"}}
Orden: "qué ves en mi pantalla?" → {"tipo_tarea":"VISION_SCREEN","habilidad_requerida":"screen","argumentos":{}}
Orden: "Qué tengo abierto en mi pantalla?" → {"tipo_tarea":"VISION_SCREEN","habilidad_requerida":"screen","argumentos":{}}
Orden: "mira este código en vscode" → {"tipo_tarea":"VISION_SCREEN","habilidad_requerida":"screen","argumentos":{}}
Orden: "qué tengo al frente de mí?" → {"tipo_tarea":"VISION_CAMERA","habilidad_requerida":"vision","argumentos":{}}
Orden: "toma una foto de la cámara" → {"tipo_tarea":"VISION_CAMERA","habilidad_requerida":"vision","argumentos":{}}
Orden: "resume este archivo pdf" → {"tipo_tarea":"READ_PDF","habilidad_requerida":"pdf","argumentos":{}}
Orden: "reproduce un video de música lofi en youtube" → {"tipo_tarea":"YOUTUBE","habilidad_requerida":"youtube","argumentos":{}}
Orden: "explícame la inteligencia artificial" → {"tipo_tarea":"GENERAL_TALK","habilidad_requerida":"agent","argumentos":{}}

Orden del usuario: """


def log(msg):
    print(f"[Tálamo] {msg}", file=sys.stderr, flush=True)


def _clean_json(text: str) -> str:
    """Elimina bloques markdown y devuelve JSON limpio."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    # Extraer primer bloque JSON
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return text.strip()


def _via_ollama(query: str) -> dict | None:
    """Llama a Ollama (local) usando urllib — sin subprocess ni red externa."""
    prompt = f"{SYSTEM_PROMPT}\"{query}\""
    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 200}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        content = data.get("response", "")
        cleaned = _clean_json(content)
        result  = json.loads(cleaned)
        log(f"Ollama OK → {result.get('tipo_tarea', 'UNKNOWN')}")
        return result

    except urllib.error.URLError:
        log("Ollama no disponible (URLError). Activando fallback.")
        return None
    except json.JSONDecodeError as e:
        log(f"JSON inválido de Ollama: {e}. Activando fallback.")
        return None
    except Exception as e:
        log(f"Error Ollama: {e}. Activando fallback.")
        return None


def _via_openclaw_fallback(query: str) -> dict | None:
    """Fallback: openclaw infer model run (cloud, más lento)."""
    model_id    = "nvidia/deepseek-ai/deepseek-v4-flash"
    prompt_full = f"{SYSTEM_PROMPT}\"{query}\""
    cmd = [
        "openclaw", "infer", "model", "run",
        "--model", model_id,
        "--prompt", prompt_full,
        "--json"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            return None
        res_json = json.loads(result.stdout.strip())
        outputs  = res_json.get("outputs", [])
        if not outputs:
            return None
        content = _clean_json(outputs[0].get("text", ""))
        parsed  = json.loads(content)
        log(f"OpenClaw fallback OK → {parsed.get('tipo_tarea', 'UNKNOWN')}")
        return parsed
    except Exception as e:
        log(f"Fallback openclaw también falló: {e}")
        return None


def clasificar_query(query: str) -> dict:
    """Intenta Ollama primero; si falla, intenta openclaw; si todo falla, retorna GENERAL_TALK."""
    result = _via_ollama(query)
    if result:
        return result

    log("Intentando fallback cloud (openclaw)...")
    result = _via_openclaw_fallback(query)
    if result:
        return result

    log("Todos los métodos fallaron. Retornando GENERAL_TALK.")
    return {"tipo_tarea": "GENERAL_TALK", "habilidad_requerida": "fallback", "argumentos": {}}


def warmup_model():
    """Envía un prompt mínimo para pre-cargar gemma:2b en RAM (elimina cold start)."""
    log("Pre-calentando gemma:2b en Ollama...")
    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": "OK",
        "stream": False,
        "options": {"num_predict": 1}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp.read()
        log("Warmup completado — gemma:2b listo en RAM.")
    except Exception as e:
        log(f"Warmup falló (no crítico): {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta query de entrada"}))
        sys.exit(1)

    # Modo warmup: precarga el modelo en RAM sin procesar query
    if sys.argv[1] == "--warmup":
        warmup_model()
        sys.exit(0)

    query     = sys.argv[1]
    resultado = clasificar_query(query)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
