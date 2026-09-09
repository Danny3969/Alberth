#!/usr/bin/env python3
# =============================================================================
# ALBERTH TÁLAMO — Enrutador Inteligente Ultrarrápido (v4 — Híbrido Cero Latencia)
#
# 1. Reglas heurísticas semánticas instantáneas (<1ms)
# 2. Ollama Local solo si el puerto está activo (timeout 2.0s)
# 3. Fast-Path Cloud (NVIDIA NIM / Gemini Flash) en <1s
# 4. Fallback seguro GENERAL_TALK
# =============================================================================

from __future__ import annotations
import sys
import os
import re
import json
import socket
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

# Cargar variables de entorno si existen en ~/.openclaw/.env
env_file = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma:2b"

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
    """Elimina bloques markdown y extrae JSON puro."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return text.strip()


def _fast_heuristic_classifier(query: str) -> Optional[Dict[str, Any]]:
    """Enrutamiento heurístico en <1 milisegundo para patrones inequívocos."""
    q = query.lower().strip()

    # 1. Finanzas / Ticker
    if any(k in q for k in ["bitcoin", "ethereum", "solana", "crypto", "cripto", "dólar", "dolar", "euro"]) or (
        any(k in q for k in ["precio de", "cuánto vale", "cuanto vale", "cotización de", "cotizacion de"]) and
        any(k in q for k in ["apple", "tesla", "nvidia", "google", "amazon", "microsoft", "acción", "accion", "btc", "eth"])
    ):
        target = "bitcoin"
        for t in ["bitcoin", "ethereum", "solana", "apple", "tesla", "nvidia", "btc", "eth"]:
            if t in q:
                target = t
                break
        return {"tipo_tarea": "FINANCE_TICKER", "habilidad_requerida": "finance", "argumentos": {"activo": target}}

    # 2. Generación de Imágenes
    if any(q.startswith(k) or f" {k}" in q for k in ["dibuja", "crea una imagen", "genera una imagen", "diseña una imagen", "haz una ilustración", "genera imagen"]):
        desc = re.sub(r"^(dibuja|crea una imagen de|genera una imagen de|diseña una imagen de|genera imagen de)\s*", "", q, flags=re.I).strip()
        return {"tipo_tarea": "IMAGE_GEN", "habilidad_requerida": "image_gen", "argumentos": {"descripcion_imagen": desc or query}}

    # 3. Visión de Pantalla (Screen)
    if any(k in q for k in ["mi pantalla", "en la pantalla", "qué tengo abierto", "que tengo abierto", "mira este código", "mira el código", "vscode", "screenshot"]):
        return {"tipo_tarea": "VISION_SCREEN", "habilidad_requerida": "screen", "argumentos": {}}

    # 4. Visión de Cámara (Camera)
    if any(k in q for k in ["cámara", "camara", "mira a mi alrededor", "qué ves al frente", "que ves al frente", "quién está frente", "quien esta frente", "toma una foto"]):
        return {"tipo_tarea": "VISION_CAMERA", "habilidad_requerida": "vision", "argumentos": {}}

    # 5. YouTube
    if any(k in q for k in ["youtube", "reproduce en youtube", "pon la canción", "pon una canción", "video musical"]):
        yt_q = re.sub(r"^(reproduce|pon en youtube|abre youtube y pon|busca en youtube)\s*", "", q, flags=re.I).strip()
        return {"tipo_tarea": "YOUTUBE", "habilidad_requerida": "youtube", "argumentos": {"query": yt_q or query}}

    # 6. Lectura de PDF
    if any(k in q for k in ["este pdf", "archivo pdf", "el pdf", "documento pdf", "resume el pdf"]):
        return {"tipo_tarea": "READ_PDF", "habilidad_requerida": "pdf", "argumentos": {}}

    # 7. Control de Sistema Mac, Ecosistema Apple, Lector Web y RAG
    if any(k in q for k in [
        "sube el volumen", "baja el volumen", "silencia", "sube el brillo", "baja el brillo",
        "modo oscuro", "reinicia el", "apaga el mac", "calendario", "agenda", "mis reuniones",
        "crea una nota", "mis notas", "recordatorio", "recuérdame", "recuerdame", "atajo",
        "en mis documentos", "en mis pdfs", "según el archivo", "busca en el archivo",
        "lee la página", "resume este enlace", "http://", "https://"
    ]):
        return {"tipo_tarea": "SYSTEM_UTILS", "habilidad_requerida": "system", "argumentos": {"comando": query}}

    # 8. Recordatorios y Timers
    if any(k in q for k in ["recuérdame", "recuerdame", "pon un timer", "pon una alarma", "temporizador"]):
        return {"tipo_tarea": "REMINDER_TIMER", "habilidad_requerida": "reminder", "argumentos": {"query": query}}

    # 9. Clima / Búsqueda Web
    if any(k in q for k in ["clima en", "clima de", "temperatura en", "qué tiempo hace", "busca en internet", "busca en google"]):
        return {"tipo_tarea": "WEB_SEARCH", "habilidad_requerida": "search", "argumentos": {"query": query}}

    return None


def _via_ollama(query: str) -> Optional[Dict[str, Any]]:
    """Llama a Ollama solo si el socket local está respondiendo."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.15):
            pass
    except Exception:
        return None

    prompt = f"{SYSTEM_PROMPT}\"{query}\""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 120}
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("response", "")
        cleaned = _clean_json(content)
        result = json.loads(cleaned)
        log(f"Ollama OK → {result.get('tipo_tarea', 'UNKNOWN')}")
        return result
    except Exception as e:
        log(f"Ollama no respondió o error: {e}")
        return None


def _via_fast_cloud(query: str) -> Optional[Dict[str, Any]]:
    """Clasificador ultrarrápido vía Cloud (~0.7s) usando NVIDIA NIM o Gemini."""
    prompt_full = f"{SYSTEM_PROMPT}\"{query}\""

    # 1. NVIDIA NIM Fast-Path (~0.7s)
    nv_key = os.environ.get("NVIDIA_API_KEY")
    if nv_key:
        try:
            payload = json.dumps({
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [{"role": "user", "content": prompt_full}],
                "max_tokens": 120,
                "temperature": 0.1
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=payload,
                headers={"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
                txt = res_json["choices"][0]["message"]["content"].strip()
                cleaned = _clean_json(txt)
                result = json.loads(cleaned)
                log(f"NVIDIA Tálamo OK → {result.get('tipo_tarea')}")
                return result
        except Exception as e:
            log(f"NVIDIA Tálamo error: {e}")

    # 2. Google Gemini Fast-Path (~0.9s)
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            g_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt_full}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 120}
            }).encode("utf-8")
            req = urllib.request.Request(g_url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                g_res = json.loads(resp.read().decode("utf-8"))
                txt = g_res["candidates"][0]["content"]["parts"][0]["text"].strip()
                cleaned = _clean_json(txt)
                result = json.loads(cleaned)
                log(f"Gemini Tálamo OK → {result.get('tipo_tarea')}")
                return result
        except Exception as e:
            log(f"Gemini Tálamo error: {e}")

    return None


def clasificar_query(query: str) -> Dict[str, Any]:
    """Orquestación híbrida: Heurística (<1ms) -> Ollama (si está activo) -> Cloud Fast-Path (<1s) -> GENERAL_TALK."""
    # 1. Reglas instantáneas (<1ms)
    fast = _fast_heuristic_classifier(query)
    if fast:
        log(f"Heurística Instantánea (<1ms) → {fast.get('tipo_tarea')}")
        return fast

    # 2. Ollama local (si está activo y responde en <2.5s)
    result = _via_ollama(query)
    if result:
        return result

    # 3. Fast-Path Cloud (<1s)
    result = _via_fast_cloud(query)
    if result:
        return result

    # 4. Fallback GENERAL_TALK
    log("Sin coincidencia específica → GENERAL_TALK.")
    return {"tipo_tarea": "GENERAL_TALK", "habilidad_requerida": "agent", "argumentos": {}}


def warmup_model():
    """Warmup ligero."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=0.15):
            pass
    except Exception:
        log("Warmup omitido: Ollama no está escuchando en 11434.")
        return

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": "OK",
        "stream": False,
        "options": {"num_predict": 1}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        log("Warmup completado en Ollama.")
    except Exception as e:
        log(f"Warmup falló: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Falta query de entrada"}))
        sys.exit(1)

    if sys.argv[1] == "--warmup":
        warmup_model()
        sys.exit(0)

    query = sys.argv[1]
    resultado = clasificar_query(query)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
