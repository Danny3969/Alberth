#!/usr/bin/env python3
# =============================================================================
# ALBERTH WEB SERVER — Panel Web Premium con FastAPI + WebSocket
# Expone Alberth como aplicación web accesible desde cualquier dispositivo
# en la red local (LAN). Fase 1 del proyecto Alberth v3.0.
#
# Uso: python3 alberth_web_server.py
# Puerto: 8080
# =============================================================================

from __future__ import annotations
import os, sys, json, time, asyncio, subprocess, threading, socket, re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Cargar variables de entorno protegidas ─────────────────────────────────────
def load_env():
    env_path = os.path.expanduser("~/.openclaw/.env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    if line.startswith("export "):
                        line = line[7:]
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ[k] = v

load_env()

def verify_token_helper(authorization: Optional[str]):
    expected = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de acceso requerido")
    token = authorization.split(" ", 1)[1].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Token de acceso no autorizado")

def require_token(authorization: Optional[str] = Header(None)):
    """FastAPI Dependency para validar el token ANTES de procesar el body del request."""
    verify_token_helper(authorization)

# ── Configuración ──────────────────────────────────────────────────────────────
WORKSPACE     = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).resolve().parent)
PANEL_DIR     = WORKSPACE / "panel"
VOICE_INPUT   = WORKSPACE / "voice_exchange" / "input"
VOICE_OUTPUT  = WORKSPACE / "voice_exchange" / "output"
MASTER_SCRIPT = WORKSPACE / "alberth_master.sh"
SYSTEM_HELPER = WORKSPACE / "alberth_system_helper.py"
PORT = 8080
HOST = "0.0.0.0"

# ── Lifespan (reemplaza el deprecado on_event) ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    asyncio.create_task(watch_output())
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
    except: ip = "localhost"
    print(f"\n{'='*55}")
    print(f"  🎙️  ALBERTH PANEL v3.0")
    print(f"{'='*55}")
    print(f"  Local  → http://localhost:{PORT}")
    print(f"  iPhone → http://{ip}:{PORT}")
    print(f"{'='*55}\n")
    yield
    # ── Shutdown ── (espacio para limpieza futura)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Alberth Panel", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Montar directorios estáticos para audio y assets
app.mount("/output", StaticFiles(directory=str(VOICE_OUTPUT)), name="output")
app.mount("/assets", StaticFiles(directory=str(WORKSPACE)), name="assets")
if (PANEL_DIR / "assets").exists():
    app.mount("/panel/assets", StaticFiles(directory=str(PANEL_DIR / "assets")), name="panel_assets")

@app.get("/floating", response_class=FileResponse)
async def get_floating_bar():
    floating_file = PANEL_DIR / "floating.html"
    if floating_file.exists():
        return FileResponse(str(floating_file))
    raise HTTPException(status_code=404, detail="floating.html no encontrado")


# ── WebSocket Manager ──────────────────────────────────────────────────────────
class ConnectionManager:
    def __init__(self): self.active: list[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept(); self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.active: self.active.remove(ws)
    async def broadcast(self, msg: dict):
        dead = []
        for ws in self.active:
            try: await ws.send_json(msg)
            except: dead.append(ws)
        for ws in dead: self.disconnect(ws)
    async def send(self, ws: WebSocket, msg: dict):
        try: await ws.send_json(msg)
        except: self.disconnect(ws)

manager = ConnectionManager()
history: list[dict] = []

def add_history(role: str, content: str) -> dict:
    e = {"role": role, "content": content, "ts": time.strftime("%H:%M")}
    history.append(e)
    if len(history) > 100: history.pop(0)
    return e

# ── Pipeline de Alberth ────────────────────────────────────────────────────────
# Contexto de conversación en memoria (para dar contexto al gateway)
_conv_history: list[dict] = []

# Modelos Ollama disponibles localmente (en orden de preferencia)
# Modelos Ollama disponibles localmente (en orden de preferencia)
OLLAMA_MODELS = [
    "gemma:2b",          # Rápido, ~3B params
    "llama3:latest",     # Más capaz, ~8B params
    "gemma4:latest",     # Más nuevo, ~8B params
]

# Marca de tiempo de la última interacción visual (para contexto de seguimiento)
_last_vision_time: float = 0.0

def run_alberth_full(text: str) -> dict:
    """Pipeline maestro de Alberth v3.0:
    1. Sentido Visual:
       - Cámara FaceTime HD: 'verme', 'mírame', 'qué ves', 'qué sostengo en mi mano', 'qué objeto', etc.
       - Pantalla Mac: 'pantalla', 'captura la pantalla', 'analiza mi pantalla', etc.
    2. Sentido Operativo (macOS):
       - Spotify, Volumen, Finder, Carpetas ('crea carpeta X'), Apps, Batería.
    3. Sentido Intelectual (Cerebro IA):
       - Google Gemini Pro (si GEMINI_API_KEY está configurada).
       - Groq ultra rápido (openai/gpt-oss-120b).
       - NVIDIA NIM (meta/llama-3.2-11b-vision-instruct).
       - Fallback: Ollama local.
    4. Sentido Vocal (Edge-TTS):
       - Síntesis de voz cinematográfica para que Alberth responda por audio.
    """
    global _last_vision_time
    import requests as _req
    import urllib.request as _urlreq
    load_env()

    q_clean = text.strip()
    q_lower = q_clean.lower()

    resp_text = ""
    image_url = None
    audio_url = None

    # ── 1. Detección de Visión: Pantalla ──────────────────────────────────────
    is_screen_query = any(k in q_lower for k in [
        "pantalla", "captura la pantalla", "captura de pantalla",
        "qué hay en la pantalla", "que hay en la pantalla", "mira mi pantalla",
        "analiza mi pantalla", "visión mac", "vision mac", "screenshot"
    ])

    # ── 2. Detección de Visión: Cámara Web (Verme, Objetos, Manos, etc.) ──────
    camera_keywords = [
        # Ver y mirar
        "verme", "mírame", "mirame", "qué ves", "que ves", "mira la cámara",
        "mira la camara", "quién está frente", "quien esta frente", "quién está aquí",
        "quien esta aqui", "activa la cámara", "activa la camara", "mira por la cámara",
        "mira por la camara", "puedes verme", "me puedes ver", "ves algo",
        "foto de la cámara", "rostro", "cara", "cómo me veo", "como me veo",
        "mira de nuevo", "mírame otra vez", "mirame otra vez", "vuelve a mirar",
        "mira ahora", "mírame ahora", "me ves", "me estás viendo", "me estas viendo",
        "me estás mirando", "me estas mirando", "me ves?", "me ves ?",

        # Objetos, manos y lo que sostiene o muestra
        "mano", "manos", "sostengo", "sosteniendo", "agarrando", "tengo en la mano",
        "tengo en las manos", "qué tengo aquí", "que tengo aqui", "qué es esto",
        "que es esto", "mira esto", "observa esto", "qué objeto", "que objeto",
        "mostrando", "te muestro", "mira lo que tengo", "mira lo que sostengo",
        "qué tengo agarrado", "objeto tengo", "ves lo que tengo", "qué tengo en",
        "que tengo en", "qué hay en mi", "que hay en mi", "qué sostengo", "que sostengo",
        "qué tengo enfrente", "que tengo enfrente", "lo que tengo",

        # Vestimenta, accesorios y gestos
        "tengo puesto", "traigo puesto", "qué ropa", "que ropa", "color de mi",
        "lentes", "gafas", "sombrero", "gorra", "cuántos dedos", "cuantos dedos",
        "qué gesto", "que gesto", "qué hago", "que hago", "cómo estoy vestido",
        "como estoy vestido", "qué ropa llevo", "que ropa llevo", "cómo ando vestido",
        "como ando vestido", "qué traigo", "que traigo"
    ]

    is_direct_camera = any(k in q_lower for k in camera_keywords)

    # Excluir consultas que contengan URLs explícitas de la detección de cámara/pantalla
    has_url = bool(re.search(r'https?://', q_lower))

    # Preguntas de seguimiento visual en contexto reciente (< 90 segundos)
    is_followup_vision = (
        not has_url and
        (time.time() - _last_vision_time < 90) and
        any(k in q_lower for k in ["y ahora", "ahora qué", "ahora que", "mira ahora", "mírame ahora", "qué ves ahora", "qué observas ahora"])
    )

    is_camera_query = not has_url and not is_screen_query and (is_direct_camera or is_followup_vision)
    if has_url:
        is_screen_query = False

    # ── Ejecutar Visión si corresponde ────────────────────────────────────────
    if is_camera_query or is_screen_query:
        try:
            _last_vision_time = time.time()
            import sys
            if str(WORKSPACE) not in sys.path:
                sys.path.insert(0, str(WORKSPACE))
            import alberth_vision

            nv_key = os.environ.get("NVIDIA_API_KEY") or alberth_vision.get_nvidia_api_key()
            gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

            if is_screen_query:
                ok = alberth_vision.capture_screen()
                target_img = alberth_vision.SCREEN_PATH
                img_relative = f"/assets/voice_exchange/alberth_screen.jpg?t={int(time.time() * 1000)}"
                prompt_vision = (
                    f"Eres Alberth, el asistente técnico de élite del Señor Danny. "
                    f"El Señor Danny te pregunta sobre su pantalla: '{q_clean}'. "
                    f"Analiza con detalle las ventanas, aplicaciones y código visible y descríbeselo con respeto y precisión."
                )
            else:
                ok = alberth_vision.capture_image()
                target_img = alberth_vision.IMAGE_PATH
                img_relative = f"/assets/voice_exchange/alberth_vision.jpg?t={int(time.time() * 1000)}"
                
                # Prompt especializado si pregunta por objetos o manos
                is_hand_query = any(w in q_lower for w in ["mano", "sostengo", "sosteniendo", "agarrando", "objeto", "qué es esto", "que es esto", "qué tengo"])
                if is_hand_query:
                    prompt_vision = (
                        f"Eres Alberth, el asistente personal y mano derecha de élite del Señor Danny. "
                        f"El Señor Danny te pregunta mirando a la cámara web: '{q_clean}'. "
                        f"Inspecciona minuciosamente sus manos y el objeto que sostiene o te está mostrando frente a la cámara. "
                        f"Identifica y describe con máxima precisión el objeto exacto, qué es, su color, forma y qué está haciendo con él. "
                        f"Responde con respeto, calidez y estilo analítico dirigiéndote al Señor Danny."
                    )
                else:
                    prompt_vision = (
                        f"Eres Alberth, la mano derecha analítica y asistente personal de élite del Señor Danny. "
                        f"El Señor Danny te pregunta mirando a la cámara web: '{q_clean}'. "
                        f"Míralo a través de la cámara de su Mac y descríbele detalladamente con respeto, calidez y precisión "
                        f"lo que ves frente a la cámara (su vestimenta, entorno, postura y lo que observas)."
                    )

            if ok and (nv_key or gemini_key):
                desc = alberth_vision.describe_image(nv_key, custom_prompt=prompt_vision, target_image=target_img)
                if desc:
                    resp_text = desc.strip()
                    image_url = img_relative
        except Exception as e:
            print(f"[Vision Error] {e}")

    # ── 3. Acciones Nativas del Sistema Mac (si no es visión) ──────────────────
    if not resp_text:
        try:
            import sys
            if str(WORKSPACE) not in sys.path:
                sys.path.insert(0, str(WORKSPACE))
            import alberth_system_helper
            sys_res = alberth_system_helper.dispatch(q_clean)
            if sys_res and sys_res.get("exito"):
                resp_text = sys_res.get("resultado", "Acción completada exitosamente, Señor Danny.")
        except Exception as e:
            print(f"[System Helper Error] {e}")

    # ── 3.5. Misión Multi-Agente Autónoma (LangGraph: Estratega + Investigador + Ingeniero + QA) ──
    if not resp_text:
        multi_keywords = [
            "equipo multi-agente", "equipo multiagente", "multi-agente", "multiagente",
            "misión multi-agente", "mision multi-agente", "misión multiagente",
            "investiga y programa", "investiga y calcula", "analiza y crea",
            "planifica y ejecuta", "desarrolla y prueba", "equipo de trabajo"
        ]
        if any(mk in q_lower for mk in multi_keywords):
            try:
                import alberth_multi_agent
                print(f"[Web Server] 🚀 Activando Grafo Multi-Agente para: {q_clean}")
                ma_res = alberth_multi_agent.run_multi_agent_mission(q_clean)
                if ma_res and ma_res.get("final_summary"):
                    resp_text = ma_res["final_summary"]
            except Exception as mae:
                print(f"[Multi-Agent Error] {mae}")

    # ── 3.6. Navegación Web Autónoma con Playwright (Headless Browser Agent) ────
    if not resp_text:
        browser_keywords = [
            "navega a", "navega en", "entra a la web", "entra a la página",
            "entra a la pagina", "busca en la web y extrae", "busca en el portal",
            "abre el portal y busca", "extrae de la web", "navegador autónomo",
            "navegador autonomo"
        ]
        if any(bk in q_lower for bk in browser_keywords):
            try:
                import alberth_playwright_agent
                print(f"[Web Server] 🌐 Activando Agente Web Playwright para: {q_clean}")
                bw_res = alberth_playwright_agent.run_autonomous_browser_mission(mission=q_clean, max_steps=4)
                if bw_res and bw_res.get("summary"):
                    resp_text = bw_res["summary"]
            except Exception as bwe:
                print(f"[Browser Agent Error] {bwe}")

    # ── 4. Inteligencia Conversacional (Cerebro LLM) ───────────────────────────
    if not resp_text:
        soul_file = WORKSPACE / "SOUL.md"
        soul_content = soul_file.read_text(encoding="utf-8") if soul_file.exists() else ""
        orq_file = WORKSPACE / "agents" / "orquestador" / "PROMPT.md"
        orq_prompt = orq_file.read_text(encoding="utf-8") if orq_file.exists() else ""
        system_prompt = (
            f"AGENTE ORQUESTADOR CORE (OPENCLAW):\n{orq_prompt}\n\n"
            f"INSTRUCCIONES DE PERSONALIDAD (SOUL.md):\n{soul_content}\n\n"
            "DIRECTRICES OBLIGATORIAS:\n"
            "- Eres Alberth, el asistente personal de élite y mano derecha del Señor Danny.\n"
            "- Dirígete siempre al usuario con el título 'Señor Danny' con respeto y cercanía profesional.\n"
            "- Estás conectado localmente al hardware de su Mac: dispones de escucha activa por micrófono, visión en vivo por cámara web FaceTime HD, captura y análisis de pantalla, síntesis de voz y control de aplicaciones y archivos del sistema.\n"
            "- Responde siempre con seguridad, inteligencia, concisión y análisis directo en español. Nunca uses frases condescendientes ni muletillas vacías.\n"
            "- FORMATO OBLIGATORIO: Usa SOLO texto plano sin ningún tipo de formato markdown. Absolutamente prohibido usar asteriscos (**texto**), almohadillas (#), guiones de lista (* item), bloques de código (```), o cualquier otro símbolo de markdown. Escribe como si fuera una conversación natural y directa. Las respuestas deben ser completas, no las cortes a la mitad."
        )
        messages = [{"role": "system", "content": system_prompt}] + _conv_history[-8:] + [{"role": "user", "content": q_clean}]

        # ── Extracción y Análisis de URLs y Videos en la Consulta ───────────────
        url_in_prompt = re.search(r'https?://[^\s]+', q_clean)
        prompt_with_context = q_clean
        if url_in_prompt:
            target_url = url_in_prompt.group(0)
            is_video_platform = any(domain in target_url.lower() for domain in [
                "tiktok.com", "youtube.com", "youtu.be", "instagram.com", "twitter.com", "x.com", "vimeo.com"
            ]) or any(kw in q_clean.lower() for kw in ["video", "deepfake", "analiza el video", "es real", "es falso", "falsificacion"])
            
            if is_video_platform:
                try:
                    import alberth_video_analyzer
                    print(f"[VideoAnalyzer] Ejecutando análisis de video raw para: {target_url}")
                    vid_result = alberth_video_analyzer.process_video(target_url, max_frames=5)
                    if vid_result.get("success"):
                        frames_desc = "\n".join([f"- [{f['timestamp']}]: {f['analysis']}" for f in vid_result.get("frame_breakdown", [])])
                        prompt_with_context += (
                            f"\n\n[ANÁLISIS DE VIDEO RAW Y FOTOGRAMAS CLAVE ({target_url})]:\n"
                            f"Score de Autenticidad: {vid_result.get('authenticity_score')}\n"
                            f"Veredicto Técnico: {vid_result.get('verdict')}\n"
                            f"Fotogramas Clave Analizados:\n{frames_desc}\n\n"
                            f"Utiliza este análisis técnico directo de los fotogramas para responder detalladamente al Señor Danny."
                        )
                    else:
                        prompt_with_context += f"\n\n[NOTA DEL SISTEMA]: Intento de descarga/procesamiento del video ({target_url}): {vid_result.get('error')}. Responde evaluando el contexto y la tecnología actual de IA."
                except Exception as vide:
                    print(f"[VideoAnalyzer Error] {vide}")
            else:
                try:
                    import alberth_browser_agent
                    web_info = alberth_browser_agent.extract_web_content(target_url)
                    if web_info and web_info.get("exito") and len(web_info.get("contenido", "").strip()) > 40:
                        prompt_with_context += f"\n\n[CONTEXTO WEB EXTRAÍDO DE LA URL ({target_url})]:\nTítulo: {web_info['titulo']}\nContenido:\n{web_info['contenido']}"
                except Exception as urle:
                    print(f"[URL Context Extraction Error] {urle}")

        # ── Orquestador Multi-Modelo Fundacional (DeepSeek / Qwen Coder / Llama Vision) ──
        try:
            import alberth_foundation_models
            ans_text, model_tag, role_assigned = alberth_foundation_models.query_foundation_model(
                prompt=prompt_with_context,
                system_prompt=system_prompt,
                history=_conv_history[-8:],
                max_tokens=1200
            )
            if ans_text and ans_text != "Error" and not ans_text.startswith("Señor Danny, no fue posible") and "momentáneamente no disponibles" not in ans_text:
                resp_text = ans_text
                print(f"[Foundation Models] Rol: {role_assigned} | Modelo: {model_tag}")
        except Exception as e:
            print(f"[Foundation Models Router Error] {e}")

        # ── Fallback secundario directo: Google Gemini Direct Stream ──────────────
        if not resp_text:
            gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if gemini_key:
                for gm in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"]:
                    try:
                        g_url = f"https://generativelanguage.googleapis.com/v1beta/models/{gm}:generateContent?key={gemini_key}"
                        g_payload = {
                            "contents": [{"parts": [{"text": f"{system_prompt}\n\nSeñor Danny: {q_clean}"}]}],
                            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 500}
                        }
                        g_req = _urlreq.Request(g_url, data=json.dumps(g_payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                        with _urlreq.urlopen(g_req, timeout=3.5) as resp:
                            g_res = json.loads(resp.read().decode("utf-8"))
                            txt = g_res["candidates"][0]["content"]["parts"][0]["text"].strip()
                            if txt:
                                resp_text = txt
                                break
                    except Exception as e:
                        print(f"[Gemini Direct Stream {gm}] {e}")

        # ── Fallback terciario: Groq (GPT-OSS 120B / Qwen 3.8 / GPT-OSS 20B) ─────
        if not resp_text:
            groq_key = os.environ.get("GROQ_API_KEY")
            if groq_key:
                import requests as _req_groq
                for groq_m in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "groq/compound-mini"]:
                    try:
                        groq_payload = {
                            "model": groq_m,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": q_clean}
                            ],
                            "max_tokens": 1200,
                            "temperature": 0.5
                        }
                        groq_resp = _req_groq.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            json=groq_payload,
                            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                            timeout=4.0
                        )
                        if groq_resp.status_code == 200:
                            txt = groq_resp.json()["choices"][0]["message"]["content"].strip()
                            if txt:
                                resp_text = txt
                                print(f"[Groq Fallback] Respuesta OK — {groq_m}")
                                break
                        else:
                            print(f"[Groq Fallback {groq_m}] HTTP {groq_resp.status_code}: {groq_resp.text[:80]}")
                    except Exception as ge:
                        print(f"[Groq Fallback {groq_m} Error] {ge}")

        # Fallback final cortés y en carácter
        if not resp_text:
            resp_text = "Señor Danny, en este momento todos los proveedores de IA están experimentando alta demanda. Por favor intente de nuevo en unos segundos."

    # ── Limpiar Markdown de la respuesta final (seguro de respaldo) ──────────
    import re as _re
    resp_text = _re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', resp_text)   # **bold** y *italic*
    resp_text = _re.sub(r'^#{1,6}\s+', '', resp_text, flags=_re.MULTILINE)  # # encabezados
    resp_text = _re.sub(r'^[-*]\s+', '- ', resp_text, flags=_re.MULTILINE)  # * listas → guion
    resp_text = _re.sub(r'`{1,3}[^`]*`{1,3}', lambda m: m.group(0).replace('`',''), resp_text)  # `code`
    resp_text = resp_text.strip()

    # Guardar en memoria de conversación
    _conv_history.append({"role": "user", "content": q_clean})
    _conv_history.append({"role": "assistant", "content": resp_text})
    if len(_conv_history) > 20:
        _conv_history.pop(0)
        _conv_history.pop(0)

    # ── 5. Síntesis de Voz Asíncrona (Edge-TTS en background sin frenar la respuesta) ──
    try:
        import threading
        ts = time.strftime("%Y%m%d_%H%M%S")
        VOICE_OUTPUT.mkdir(parents=True, exist_ok=True)
        tts_file = VOICE_OUTPUT / f"alberth_{ts}.mp3"
        venv_py = WORKSPACE / "venv" / "bin" / "python3"
        py_exec = str(venv_py) if venv_py.exists() else sys.executable
        # Limpiar texto para pronunciación limpia
        clean_speech = resp_text.replace("**", "").replace("#", "").replace("`", "")
        clean_speech = " ".join(clean_speech.split()[:75]) # Limitar a primeras 75 palabras para agilidad

        def _bg_synthesize(speech_txt, dest_file):
            try:
                subprocess.run(
                    [py_exec, str(WORKSPACE / "alberth_tts_premium.py"), speech_txt, str(dest_file)],
                    capture_output=True, timeout=12
                )
            except Exception as te:
                print(f"[BG TTS Error] {te}")

        threading.Thread(target=_bg_synthesize, args=(clean_speech, tts_file), daemon=True).start()
        audio_url = f"/output/{tts_file.name}"
    except Exception as e:
        print(f"[TTS Initiation Error] {e}")

    return {
        "text": resp_text,
        "audio_url": audio_url,
        "image_url": image_url
    }

def run_alberth(text: str) -> str:
    """Retorna solo texto para retrocompatibilidad."""
    res = run_alberth_full(text)
    return res.get("text", "")

async def run_alberth_pipeline_async(text: str) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_alberth_full, text)

async def run_alberth_async(text: str) -> str:
    res = await run_alberth_pipeline_async(text)
    return res.get("text", "")


# ── Live Canvas (A2UI - Interfaces Dinámicas del Agente) ──────────────────────
class CanvasPayload(BaseModel):
    title: str = "Live Canvas UI"
    html: str
    js: Optional[str] = ""
    css: Optional[str] = ""

active_canvas = {
    "title": "Live Canvas UI",
    "html": "<div style='padding:20px;text-align:center;'><h3>🎨 Alberth Live Canvas</h3><p>Esperando componentes dinámicos generados por Alberth...</p></div>",
    "js": "",
    "css": ""
}

@app.post("/api/canvas")
async def update_canvas(payload: CanvasPayload, _: None = Depends(require_token)):
    global active_canvas
    active_canvas = payload.model_dump()
    await manager.broadcast({"type": "canvas_update", "canvas": active_canvas})
    return {"status": "ok", "canvas": active_canvas}

@app.get("/api/canvas")
async def get_canvas():
    return active_canvas


def run_sys_cmd(command: str, args: dict) -> dict:
    try:
        cmd = ["python3", str(SYSTEM_HELPER), command]
        for k, v in args.items(): cmd += [f"--{k}", str(v)]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE))
        return {"ok": r.returncode == 0, "output": (r.stdout or r.stderr).strip()}
    except Exception as e: return {"ok": False, "output": str(e)}

@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    # Validar token de acceso por query params (permitir localhost automáticamente)
    client_host = ws.client.host if ws.client else ""
    is_local = client_host in ["127.0.0.1", "::1", "localhost"]
    token = ws.query_params.get("token")
    expected = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if expected and not is_local and token != expected:
        await ws.close(code=1008, reason="Token de acceso inválido")
        return

    await manager.connect(ws)
    await manager.send(ws, {"type": "history", "messages": history})
    await manager.send(ws, {"type": "system", "text": "🟢 Alberth conectado"})
    try:
        while True:
            data = await ws.receive_json()
            t = data.get("type", "text")
            if t == "text":
                txt = data.get("text", "").strip()
                if not txt: continue
                await manager.broadcast({"type": "message", "message": add_history("user", txt)})
                await manager.broadcast({"type": "thinking", "active": True})
                full_resp = await run_alberth_pipeline_async(txt)
                await manager.broadcast({"type": "thinking", "active": False})

                msg_dict = add_history("alberth", full_resp["text"])
                if full_resp.get("image_url"):
                    msg_dict["image_url"] = full_resp["image_url"]
                if full_resp.get("audio_url"):
                    msg_dict["audio_url"] = full_resp["audio_url"]

                await manager.broadcast({"type": "message", "message": msg_dict})
            elif t == "ping":
                await manager.send(ws, {"type": "pong"})
    except WebSocketDisconnect: manager.disconnect(ws)
    except: manager.disconnect(ws)

# ── Audio ──────────────────────────────────────────────────────────────────────
@app.post("/audio")
async def recv_audio(file: UploadFile = File(...), _: None = Depends(require_token)):
    import requests
    VOICE_INPUT.mkdir(parents=True, exist_ok=True)
    VOICE_OUTPUT.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    
    orig_filename = file.filename or "audio.webm"
    ext = orig_filename.split(".")[-1].lower() if "." in orig_filename else "webm"
    if ext not in ["webm", "m4a", "wav", "caf", "mp3", "ogg"]:
        ext = "webm"

    raw = VOICE_INPUT / f"alberth_web_temp_{ts}.{ext}"
    wav = VOICE_INPUT / f"alberth_web_temp_{ts}.wav"
    raw.write_bytes(await file.read())
    
    try:
        # Convertir a WAV a 16000Hz mono para la API de Whisper
        r = subprocess.run(
            ["/usr/local/bin/ffmpeg", "-y", "-i", str(raw), "-ar", "16000", "-ac", "1", "-f", "wav", str(wav)],
            capture_output=True, timeout=30
        )
        raw.unlink(missing_ok=True)
        
        if r.returncode != 0 or not wav.exists():
            wav.unlink(missing_ok=True)
            return JSONResponse({"ok": False, "detail": "Error en la conversión de audio con ffmpeg"})
        
        # 1. Transcripción (STT) con Groq Whisper API
        load_env()
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            wav.unlink(missing_ok=True)
            return JSONResponse({"ok": False, "detail": "GROQ_API_KEY no configurada en el servidor"})
            
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}", "User-Agent": "AlberthAI/1.0"}
        query = ""
        with open(wav, "rb") as audio_file:
            files = {"file": (wav.name, audio_file, "audio/wav")}
            data = {"model": "whisper-large-v3-turbo", "language": "es"}
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=25)
            if resp.status_code == 200:
                query = resp.json().get("text", "").strip()
        
        wav.unlink(missing_ok=True)
        
        # Filtro de silencio o transcripción vacía
        if not query or len(query) < 3:
            return JSONResponse({"ok": True, "transcription": "", "response": "Silencio detectado."})
            
        # 2. Transmitir inmediatamente la transcripción a la UI de chat
        await manager.broadcast({"type": "message", "message": add_history("user", query)})
        await manager.broadcast({"type": "thinking", "active": True})
        
        # 3. Consulta al Pipeline Maestro de Alberth (Visión, Sistema, LLM, TTS)
        full_resp = await run_alberth_pipeline_async(query)
        await manager.broadcast({"type": "thinking", "active": False})
        
        # 4. Registrar y transmitir respuesta final
        alberth_msg = add_history("alberth", full_resp["text"])
        if full_resp.get("image_url"):
            alberth_msg["image_url"] = full_resp["image_url"]
        if full_resp.get("audio_url"):
            alberth_msg["audio_url"] = full_resp["audio_url"]
            
        await manager.broadcast({"type": "message", "message": alberth_msg})
        return JSONResponse({
            "ok": True, 
            "transcription": query, 
            "response": full_resp["text"], 
            "audio_url": full_resp.get("audio_url"),
            "image_url": full_resp.get("image_url")
        })
        
    except Exception as e:
        raw.unlink(missing_ok=True)
        wav.unlink(missing_ok=True)
        return JSONResponse({"ok": False, "detail": str(e)})

# ── Imagen de Cámara Móvil ─────────────────────────────────────────────────────
@app.post("/upload-vision")
async def recv_vision(file: UploadFile = File(...), _: None = Depends(require_token)):
    try:
        dest_dir = WORKSPACE / "voice_exchange"
        dest_dir.mkdir(parents=True, exist_ok=True)
        img_file = dest_dir / "alberth_vision.jpg"
        
        # Eliminar archivo viejo si existe
        img_file.unlink(missing_ok=True)
        
        # Guardar imagen directamente
        content = await file.read()
        img_file.write_bytes(content)
        
        return JSONResponse({"ok": True, "path": str(img_file), "size": len(content)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al guardar imagen de cámara: {str(e)}")

# ── Comandos de sistema ────────────────────────────────────────────────────────

class CmdReq(BaseModel):
    command: str
    args: dict = {}

@app.post("/command")
async def exec_cmd(req: CmdReq, _: None = Depends(require_token)):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, run_sys_cmd, req.command, req.args)
    return JSONResponse(result)

# ── Status ─────────────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    status = {
        "ok": True, "time": time.strftime("%H:%M:%S"),
        "date": time.strftime("%A %d de %B"), "messages": len(history),
        "server": "Alberth Panel v3.0"
    }
    try:
        v = subprocess.run(
            ["python3", str(SYSTEM_HELPER), "volume", "--action", "get"],
            capture_output=True, text=True, timeout=5, cwd=str(WORKSPACE)
        )
        if v.returncode == 0: status["volume"] = v.stdout.strip()
    except: pass
    return JSONResponse(status)

# ── Autocompletado Adaptativo & Frecuencias ─────────────────────────────────────
class FreqReq(BaseModel):
    command: Optional[str] = None
    freq_map: Optional[dict] = None

@app.get("/api/autocomplete/freq")
async def get_autocomplete_freq():
    """Retorna las frecuencias de comandos registradas en la DB de memoria."""
    try:
        if str(WORKSPACE) not in sys.path: sys.path.insert(0, str(WORKSPACE))
        import alberth_memory
        freqs = alberth_memory.get_cmd_frequencies()
        return JSONResponse({"ok": True, "frequencies": freqs})
    except Exception as e:
        return JSONResponse({"ok": False, "detail": str(e), "frequencies": {}})

@app.post("/api/autocomplete/freq")
async def sync_autocomplete_freq(req: FreqReq):
    """Sincroniza/Registra frecuencia de uso de comandos en SQLite."""
    try:
        if str(WORKSPACE) not in sys.path: sys.path.insert(0, str(WORKSPACE))
        import alberth_memory
        if req.command:
            alberth_memory.record_cmd_frequency(req.command)
        if req.freq_map:
            for cmd in req.freq_map:
                alberth_memory.record_cmd_frequency(cmd)
        freqs = alberth_memory.get_cmd_frequencies()
        return JSONResponse({"ok": True, "frequencies": freqs})
    except Exception as e:
        return JSONResponse({"ok": False, "detail": str(e)})

# ── Exportar Historial QA ──────────────────────────────────────────────────────
@app.get("/api/qa/export")
async def export_qa_logs(format: str = "json"):
    """Exporta el historial de auditoría y alertas QA en formato JSON o CSV."""
    from fastapi.responses import Response
    try:
        logs_file = WORKSPACE / "logs" / "audit_logs.jsonl"
        items = []
        if logs_file.exists():
            with open(logs_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try: items.append(json.loads(line))
                        except: pass

        if format.lower() == "csv":
            csv_lines = ["timestamp,modo,agente,modelo,latencia_ms,status,query"]
            for it in items:
                q = str(it.get("query", "")).replace('"', '""')
                csv_lines.append(f'"{it.get("timestamp")}","{it.get("modo")}","{it.get("agente")}","{it.get("modelo")}",{it.get("latencia_ms",0)},"{it.get("status")}","{q}"')
            return Response(content="\n".join(csv_lines), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=alberth_qa_export.csv"})
        else:
            return JSONResponse({"ok": True, "total": len(items), "items": items})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Integración con Calendario & DND ───────────────────────────────────────────
@app.get("/api/calendar/status")
async def get_calendar_status():
    """Retorna el estado de reuniones del sistema para Auto-DND por calendario."""
    try:
        res = subprocess.run(
            ["pgrep", "-i", "-f", "zoom|teams|slack|webex"],
            capture_output=True, text=True, timeout=2
        )
        in_meeting = (res.returncode == 0 and len(res.stdout.strip()) > 0)

        cal_file = WORKSPACE / "calendar_state.json"
        meeting_event = ""
        if cal_file.exists():
            try:
                data = json.loads(cal_file.read_text(encoding="utf-8"))
                if data.get("in_meeting"):
                    in_meeting = True
                    meeting_event = data.get("current_event", "")
            except Exception: pass

        return JSONResponse({
            "ok": True,
            "in_meeting": in_meeting,
            "event": meeting_event or ("Reunión activa detectada" if in_meeting else "Sin reuniones de calendario"),
            "timestamp": time.strftime("%H:%M:%S")
        })
    except Exception as e:
        return JSONResponse({"ok": False, "in_meeting": False, "detail": str(e)})


# ── Antigravity Architecture APIs (Capa 2 Native SDK & Sessions) ─────────────
class AntigravityTaskPayload(BaseModel):
    task: str
    mode: Optional[str] = "goal"

class AntigravityLearningPayload(BaseModel):
    correction_type: str = "user_correction"
    original_behavior: Optional[str] = ""
    corrected_behavior: str
    learned_rule: str

@app.get("/api/antigravity/tasks")
async def get_antigravity_tasks():
    """Retorna el historial de tareas delegadas a Antigravity."""
    try:
        import alberth_memory as memory
        tasks = memory.get_antigravity_tasks(limit=30)
        return JSONResponse({"ok": True, "tasks": tasks})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/antigravity/delegate")
async def delegate_antigravity_task(payload: AntigravityTaskPayload, _: None = Depends(require_token)):
    """Delega una tarea síncrona/secuencial a Antigravity Nativo."""
    try:
        from agente_antigravity_sdk import AntigravityNativeAgent
        agent = AntigravityNativeAgent()
        res = await agent.delegate_task(payload.task, mode=payload.mode or "goal")
        return JSONResponse({"ok": True, "result": res})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/antigravity/parallel")
async def launch_antigravity_parallel(payload: AntigravityTaskPayload, _: None = Depends(require_token)):
    """Delega una tarea en paralelo (segundo plano) a Antigravity."""
    try:
        from agente_antigravity_sdk import AntigravityParallelManager
        session_id = AntigravityParallelManager.launch_task_in_background(payload.task, mode=payload.mode or "goal")
        return JSONResponse({"ok": True, "session_id": session_id, "message": "Tarea lanzada en paralelo a Antigravity"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/antigravity/sessions")
async def get_antigravity_sessions():
    """Retorna las sesiones múltiples activas en paralelo de Antigravity."""
    try:
        from agente_antigravity_sdk import AntigravityParallelManager
        sessions = AntigravityParallelManager.get_active_sessions()
        return JSONResponse({"ok": True, "sessions": sessions})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/antigravity/learning")
async def get_antigravity_learning_rules():
    """Obtiene el historial de reglas y patrones aprendidos por Antigravity."""
    try:
        import alberth_memory as memory
        rules = memory.get_antigravity_learning(limit=50)
        return JSONResponse({"ok": True, "learning_rules": rules})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/antigravity/learning")
async def record_antigravity_learning_rule(payload: AntigravityLearningPayload, _: None = Depends(require_token)):
    """Registra una corrección del usuario para aprendizaje de patrones."""
    try:
        import alberth_memory as memory
        res = memory.record_antigravity_learning(
            payload.correction_type,
            payload.original_behavior or "",
            payload.corrected_behavior,
            payload.learned_rule
        )
        return JSONResponse({"ok": True, "result": res})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── DND Avanzado por Aplicación y Zona Horaria ────────────────────────────────
class DndAppsPayload(BaseModel):
    apps: List[str]

class DndTimezonePayload(BaseModel):
    start_time: str = "23:00"
    end_time: str = "07:00"
    timezone: str = "America/Bogota"
    enabled: bool = False

@app.get("/api/dnd/apps")
async def get_dnd_apps():
    """Retorna la lista de aplicaciones silenciadas en DND."""
    try:
        import alberth_memory as memory
        val = memory.get_dnd_setting("dnd_apps", '["Slack", "Teams", "Discord"]')
        apps = json.loads(val)
        return JSONResponse({"ok": True, "apps": apps})
    except Exception as e:
        return JSONResponse({"ok": True, "apps": ["Slack", "Teams", "Discord"]})

@app.post("/api/dnd/apps")
async def set_dnd_apps(payload: DndAppsPayload, _: None = Depends(require_token)):
    """Guarda la lista de apps silenciadas por DND."""
    try:
        import alberth_memory as memory
        memory.set_dnd_setting("dnd_apps", json.dumps(payload.apps))
        return JSONResponse({"ok": True, "apps": payload.apps})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dnd/timezone_config")
async def get_dnd_timezone_config():
    """Retorna la configuración de DND por zona horaria."""
    try:
        import alberth_memory as memory
        val = memory.get_dnd_setting("dnd_tz_config", json.dumps({
            "start_time": "23:00",
            "end_time": "07:00",
            "timezone": "America/Bogota",
            "enabled": False
        }))
        cfg = json.loads(val)
        return JSONResponse({"ok": True, "config": cfg})
    except Exception as e:
        return JSONResponse({"ok": True, "config": {"start_time": "23:00", "end_time": "07:00", "timezone": "America/Bogota", "enabled": False}})

@app.post("/api/dnd/timezone_config")
async def set_dnd_timezone_config(payload: DndTimezonePayload, _: None = Depends(require_token)):
    """Guarda la configuración de horas y zona horaria personalizadas para DND."""
    try:
        import alberth_memory as memory
        cfg = payload.model_dump()
        memory.set_dnd_setting("dnd_tz_config", json.dumps(cfg))
        return JSONResponse({"ok": True, "config": cfg})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class VideoAnalyzePayload(BaseModel):
    url: Optional[str] = None
    file_path: Optional[str] = None
    max_frames: Optional[int] = 5

@app.post("/api/video-analyze")
async def analyze_video_endpoint(payload: VideoAnalyzePayload):
    """Endpoint para análisis directo de video raw y detección de deepfakes."""
    target = payload.url or payload.file_path
    if not target:
        raise HTTPException(status_code=400, detail="Se requiere una URL o ruta de archivo local.")
    try:
        import alberth_video_analyzer
        result = alberth_video_analyzer.process_video(target, max_frames=payload.max_frames or 5)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Alertas de Pico Anómalo QA (Análisis Predictivo) ──────────────────────────
@app.get("/api/qa/predictive_alerts")
async def get_qa_predictive_alerts():
    """Analiza la densidad histórica de alertas QA y detecta si hay un pico anómalo actual."""
    try:
        import alberth_memory as memory
        logs_file = WORKSPACE / "logs" / "audit_logs.jsonl"
        items = []
        if logs_file.exists():
            with open(logs_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try: items.append(json.loads(line))
                        except: pass

        hour_counts = [0] * 24
        for it in items:
            ts_str = it.get("timestamp", "")
            if len(ts_str) >= 13 and "T" in ts_str:
                try:
                    hr = int(ts_str.split("T")[1].split(":")[0])
                    if 0 <= hr < 24:
                        hour_counts[hr] += 1
                except: pass

        avg_per_hour = sum(hour_counts) / 24.0 if sum(hour_counts) > 0 else 1.0
        current_hr = int(time.strftime("%H"))
        current_count = hour_counts[current_hr]

        # Detectar pico si la hora actual supera en >1.8x el promedio
        is_spike = current_count >= (avg_per_hour * 1.8) and current_count >= 3
        spike_pct = round(((current_count - avg_per_hour) / avg_per_hour) * 100, 1) if avg_per_hour > 0 else 0.0

        max_hr = hour_counts.index(max(hour_counts)) if hour_counts else current_hr

        return JSONResponse({
            "ok": True,
            "has_anomaly": is_spike,
            "current_hour": f"{current_hr:02d}:00",
            "current_count": current_count,
            "baseline_avg": round(avg_per_hour, 1),
            "spike_percentage": max(0.0, spike_pct),
            "predicted_peak_hour": f"{max_hr:02d}:00",
            "alert_message": f"⚠️ Pico anómalo detectado ({current_count} alertas a las {current_hr:02d}:00h, +{spike_pct}% sobre la media)" if is_spike else "🟢 Densidad de alertas QA dentro del rango normal"
        })
    except Exception as e:
        return JSONResponse({"ok": False, "has_anomaly": False, "detail": str(e)})

# ── Canal Bidireccional Mac → APK ─────────────────────────────────────────────
class PhoneCommand(BaseModel):
    action: str          # e.g. "call", "sms", "notification", "volume", "camera"
    payload: dict = {}   # parámetros de la acción: {"number": "...", "message": "..."}
    source: str = "mac"  # quién originó el comando

@app.post("/phone-command")
async def phone_command(cmd: PhoneCommand, _: None = Depends(require_token)):
    """
    Endpoint que permite al backend Mac enviarle comandos al teléfono Android.
    El servidor retransmite el comando a todos los clientes WebSocket conectados.
    La APK escucha mensajes de tipo 'phone_command' y los ejecuta.
    
    Acciones soportadas:
      - call: {number: "3001234567"}
      - sms: {number: "3001234567", message: "Hola"}
      - notification: {title: "Alberth", body: "Atención Señor"}
      - volume: {action: "up" | "down" | "mute"}
      - camera: {} (captura foto desde el teléfono)
      - location: {} (solicita GPS al teléfono)
      - open_app: {package: "com.whatsapp"}
    """
    msg = {
        "type": "phone_command",
        "action": cmd.action,
        "payload": cmd.payload,
        "source": cmd.source,
        "ts": time.strftime("%H:%M:%S")
    }
    await manager.broadcast(msg)
    connected = len(manager.active)
    return JSONResponse({"ok": True, "sent_to": connected, "action": cmd.action})

# ── Logging de errores de navegador ────────────────────────────────────────────
class BrowserError(BaseModel):
    message: str
    source: Optional[str] = None
    lineno: Optional[int] = None
    colno: Optional[int] = None
    error: Optional[str] = None

@app.post("/log_browser_error")
async def log_browser_error(err: BrowserError):
    print(f"🚨 [BROWSER ERROR] {err.message} at {err.source}:{err.lineno}:{err.colno}", flush=True)
    if err.error:
        print(f"   Stack: {err.error}", flush=True)
    # Guardar en log
    logs_dir = WORKSPACE / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    with open(logs_dir / "browser_errors.log", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {err.message} at {err.source}:{err.lineno}:{err.colno}\nStack: {err.error}\n\n")
    return {"ok": True}

# ── Servir Panel ───────────────────────────────────────────────────────────────
@app.get("/")
async def serve_panel():
    f = PANEL_DIR / "index.html"
    if f.exists():
        html = f.read_text(encoding="utf-8")
        # Inyectar dinámicamente el token esperado del servidor
        expected_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or ""
        if expected_token:
            html = html.replace(
                'let token = localStorage.getItem("alberth_token") || "";',
                f'localStorage.setItem("alberth_token", "{expected_token}");\n  let token = "{expected_token}";'
            )
        # Retornar respuesta deshabilitando el cacheo por completo
        from fastapi.responses import Response
        return Response(
            content=html, 
            media_type="text/html",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    return HTMLResponse("<h1>Panel no encontrado</h1>", 404)

# ── Limpieza de Audios Viejos ──────────────────────────────────────────────────
def cleanup_old_audio():
    """Elimina respuestas MP3 de más de 10 minutos y grabaciones/capturas de entrada de más de 48h para mantener el disco limpio."""
    now = time.time()
    for f in VOICE_OUTPUT.glob("*.mp3"):
        if f.name != "alberth_test_response.mp3" and (now - f.stat().st_mtime) > 600:
            try: f.unlink()
            except: pass

    # Limpieza preventiva de archivos temporales en input (>48 horas / 172800s)
    if VOICE_INPUT.exists():
        for pattern in ("*.wav", "*.jpg", "*.png"):
            for f in VOICE_INPUT.glob(pattern):
                try:
                    if (now - f.stat().st_mtime) > 172800:
                        f.unlink()
                except: pass

# ── Watcher de respuestas ──────────────────────────────────────────────────────
async def watch_output():
    VOICE_OUTPUT.mkdir(parents=True, exist_ok=True)
    seen = set(VOICE_OUTPUT.glob("*.txt"))
    cleanup_counter = 0
    while True:
        await asyncio.sleep(0.8)
        
        # Ejecutar limpieza de audios cada ~16 segundos (20 iteraciones * 0.8s)
        cleanup_counter += 1
        if cleanup_counter >= 20:
            cleanup_old_audio()
            cleanup_counter = 0

        # Detectar archivos .phone_cmd y retransmitir al APK
        for pcf in list(VOICE_OUTPUT.glob("*.phone_cmd")):
            try:
                raw = pcf.read_text().strip()
                if raw:
                    cmd_data = json.loads(raw)
                    cmd_data["type"] = "phone_command"
                    cmd_data["ts"] = time.strftime("%H:%M:%S")
                    await manager.broadcast(cmd_data)
                pcf.unlink(missing_ok=True)
            except Exception:
                pcf.unlink(missing_ok=True)

        cur = set(VOICE_OUTPUT.glob("*_response.txt"))
        for f in cur - seen:
            try:
                # Si es una respuesta de consulta de texto web, se maneja síncronamente en el WebSocket, no la duplicamos
                if f.name.startswith("web_text_"):
                    f.unlink(missing_ok=True)
                    # También limpiar el archivo de consulta original
                    orig_query = VOICE_OUTPUT / f.name.replace("_response.txt", ".txt")
                    orig_query.unlink(missing_ok=True)
                    continue

                txt = f.read_text().strip()
                if txt:
                    # Encontrar archivo MP3 de respuesta asociado
                    mp3_file = VOICE_OUTPUT / f.name.replace(".txt", ".mp3")
                    
                    audio_url = None
                    if mp3_file.exists():
                         audio_url = f"/output/{mp3_file.name}"
                    
                    # Detectar si hay captura de pantalla actualizada en los últimos 20 segundos
                    image_url = None
                    screen_jpg = WORKSPACE / "voice_exchange" / "alberth_screen.jpg"
                    if screen_jpg.exists() and (time.time() - screen_jpg.stat().st_mtime) < 20:
                        image_url = f"/assets/voice_exchange/alberth_screen.jpg?t={int(time.time())}"
                    
                    # Detectar si hay foto de la cámara actualizada
                    vision_jpg = WORKSPACE / "voice_exchange" / "alberth_vision.jpg"
                    if vision_jpg.exists() and (time.time() - vision_jpg.stat().st_mtime) < 20:
                        image_url = f"/assets/voice_exchange/alberth_vision.jpg?t={int(time.time())}"

                    payload = add_history("alberth", txt)
                    if audio_url:
                        payload["audio_url"] = audio_url
                    if image_url:
                        payload["image_url"] = image_url

                    await manager.broadcast({"type": "message", "message": payload})
                
                # Eliminar el archivo de respuesta y el de consulta original asociado para limpiar espacio
                f.unlink(missing_ok=True)
                orig_query = VOICE_OUTPUT / f.name.replace("_response.txt", ".txt")
                orig_query.unlink(missing_ok=True)
            except Exception as e:
                pass
        seen = set(VOICE_OUTPUT.glob("*_response.txt"))


if __name__ == "__main__":
    uvicorn.run("alberth_web_server:app", host=HOST, port=PORT, reload=False, log_level="info")
