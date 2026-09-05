#!/usr/bin/env python3
# =============================================================================
# ALBERTH WEB SERVER — Panel Web Premium con FastAPI + WebSocket
# Expone Alberth como aplicación web accesible desde cualquier dispositivo
# en la red local (LAN). Fase 1 del proyecto Alberth v3.0.
#
# Uso: python3 alberth_web_server.py
# Puerto: 8080
# =============================================================================

import os, sys, json, time, asyncio, subprocess, threading, socket
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

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
WORKSPACE     = Path("/Users/digitalspace/.openclaw/workspace")
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
OLLAMA_MODELS = [
    "gemma:2b",          # Rápido, ~3B params
    "llama3:latest",     # Más capaz, ~8B params
    "gemma4:latest",     # Más nuevo, ~8B params
]

def run_alberth(text: str) -> str:
    """Pipeline de respuesta de Alberth con 3 rutas en orden de velocidad:
    1. Ollama local (gemma:2b) — ultra rápido, sin overhead
    2. OpenClaw gateway REST — si Ollama no está disponible
    3. openclaw agent CLI — fallback lento pero confiable
    """
    import requests as _req

    # Mantener historial de conversación (últimas 10 interacciones)
    _conv_history.append({"role": "user", "content": text})
    if len(_conv_history) > 20:
        _conv_history.pop(0)

    soul_file = WORKSPACE / "SOUL.md"
    soul_content = ""
    if soul_file.exists():
        try:
            soul_content = soul_file.read_text(encoding="utf-8")
        except Exception:
            pass

    system_prompt = (
        f"INSTRUCCIONES DE PERSONALIDAD Y COMPORTAMIENTO (SOUL.md):\n{soul_content}\n\n"
        "Eres Alberth, la mano derecha analítica, directa y profesional del Señor Daniel."
    )
    messages = [{"role": "system", "content": system_prompt}] + _conv_history[-10:]

    # ── Ruta 1: Ollama local (más rápido, si está activo) ──────────────────────
    ollama_active = False
    try:
        ping = _req.get("http://localhost:11434/api/tags", timeout=1.5)
        if ping.status_code == 200:
            ollama_active = True
    except Exception:
        ollama_active = False

    if ollama_active:
        for model in OLLAMA_MODELS:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 600,
                    "temperature": 0.7,
                    "stream": False
                }
                resp = _req.post(
                    "http://localhost:11434/v1/chat/completions",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                if resp.status_code == 200:
                    answer = resp.json()["choices"][0]["message"]["content"].strip()
                    _conv_history.append({"role": "assistant", "content": answer})
                    return answer
            except Exception:
                continue  # Intentar siguiente modelo

    # Si Ollama falló, limpiar el último mensaje del historial
    if _conv_history:
        _conv_history.pop()

    # ── Ruta 2: OpenClaw Gateway REST (si el gateway lo soporta) ───────────────
    try:
        gw_tok = os.environ.get("OPENCLAW_GATEWAY_TOKEN", "")
        # Reintentar historial para ruta 2
        _conv_history.append({"role": "user", "content": text})
        messages2 = [{"role": "system", "content": system_prompt}] + _conv_history[-10:]
        payload2 = {
            "model": "nvidia/mistralai/mistral-small-4-119b-2603",
            "messages": messages2,
            "max_tokens": 512,
            "temperature": 0.7
        }
        resp2 = _req.post(
            "http://localhost:18789/v1/chat/completions",
            json=payload2,
            headers={"Authorization": f"Bearer {gw_tok}", "Content-Type": "application/json"},
            timeout=30
        )
        if resp2.status_code == 200:
            answer2 = resp2.json()["choices"][0]["message"]["content"].strip()
            _conv_history.append({"role": "assistant", "content": answer2})
            return answer2
        else:
            if _conv_history:
                _conv_history.pop()
    except Exception:
        if _conv_history:
            _conv_history.pop()

    # ── Ruta 3: openclaw agent CLI (fallback, más lento pero con memoria completa) ──
    try:
        env = os.environ.copy()
        env["ALBERTH_WEB_MODE"] = "1"
        existing_path = env.get("PATH", "")
        extra_paths = "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
        env["PATH"] = f"{extra_paths}:{existing_path}" if existing_path else extra_paths
        r = subprocess.run(
            ["/usr/local/bin/openclaw", "agent", "--agent", "main", "--message", text],
            capture_output=True, text=True, timeout=90, env=env, cwd=str(WORKSPACE)
        )
        out = r.stdout.strip()
        if out:
            FAIL_PREFIX = "[assistant turn failed before producing content]"
            if FAIL_PREFIX in out:
                out = out.replace(FAIL_PREFIX, "").strip()
            return out if out else "Entendido."
        err = r.stderr.strip() if r.stderr else ""
        useful = [l for l in err.splitlines() if l.strip() and not any(x in l for x in ["INFO", "DEBUG", "[plugins]", "[agent/"])]
        if useful:
            return " ".join(useful[-3:])
        return "Entendido."
    except subprocess.TimeoutExpired:
        return "Lo siento, el procesamiento tardó demasiado. Por favor, intente de nuevo."
    except Exception as e:
        return f"❌ Error: {e}"

async def run_alberth_async(text: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_alberth, text)


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

# ── WebSocket ──────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def ws_chat(ws: WebSocket):
    # Validar token de acceso por query params
    token = ws.query_params.get("token")
    expected = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if expected and token != expected:
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
                resp = await run_alberth_async(txt)
                await manager.broadcast({"type": "thinking", "active": False})
                await manager.broadcast({"type": "message", "message": add_history("alberth", resp)})
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
        groq_key = os.environ.get("GROQ_API_KEY")
        if not groq_key:
            wav.unlink(missing_ok=True)
            return JSONResponse({"ok": False, "detail": "GROQ_API_KEY no configurada en el servidor"})
            
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
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
        
        # 3. Consulta al Agente Alberth
        resp_text = await run_alberth_async(query)
        await manager.broadcast({"type": "thinking", "active": False})
        
        # 4. Generación de Audio de Respuesta (TTS)
        tts_wav = VOICE_OUTPUT / f"alberth_web_{ts}_response.mp3"
        tts_r = subprocess.run(
            ["python3", str(WORKSPACE / "alberth_tts_premium.py"), resp_text, str(tts_wav)],
            capture_output=True, timeout=20
        )
        
        audio_url = None
        if tts_wav.exists():
            audio_url = f"/output/{tts_wav.name}"
            
        # 5. Registrar y transmitir respuesta final
        alberth_msg = add_history("alberth", resp_text)
        if audio_url:
            alberth_msg["audio_url"] = audio_url
            
        await manager.broadcast({"type": "message", "message": alberth_msg})
        return JSONResponse({
            "ok": True, 
            "transcription": query, 
            "response": resp_text, 
            "audio_url": audio_url
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
    """Elimina respuestas MP3 de más de 10 minutos para ahorrar espacio."""
    now = time.time()
    for f in VOICE_OUTPUT.glob("*.mp3"):
        if f.name != "alberth_test_response.mp3" and (now - f.stat().st_mtime) > 600:
            try: f.unlink()
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
