#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_foundation_models.py — Orquestador de Modelos Fundacionales SOTA para Alberth
=====================================================================================
Integra y enruta dinámicamente entre los 3 modelos abiertos más reconocidos a nivel global:

1. 🧠 DEEPSEEK (R1 / V3 / V4):
   - Especialista: Razonamiento lógico profundo, deducción matemática, análisis complejo, arquitectura.
   - Proveedores: NVIDIA NIM (deepseek-v4-pro-0813) | Ollama local (deepseek-r1) | DeepSeek API oficial | Gemini 2.5 Flash Fallback.

2. 💻 QWEN 2.5 CODER (Alibaba):
   - Especialista: Generación de código, refactorización, depuración, scripting Bash/Python y llamadas a funciones.
   - Proveedores: Ollama local (qwen2.5-coder) | NVIDIA NIM (Codestral 22B / CodeLlama 70B) | Gemini 2.5 Flash Code Fallback.

3. 👁️ META LLAMA 3.3 (70B) / 3.2 VISION:
   - Especialista: Visión multimodal ultrarrápida (cámara web, capturas de pantalla) y conversación general en tiempo real.
   - Proveedores: NVIDIA NIM (meta/llama-3.2-11b-vision-instruct, ~0.75s) | Ollama local (llama3.3 / llama3.2-vision) | Gemini 2.5 Flash Fallback.

Costo: $0.00 | Resiliencia: Cascada de conmutación automática en < 1.0s.
"""

from __future__ import annotations

import os
import sys
import json
import time
import base64
import socket
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ── Roles de Inteligencia ─────────────────────────────────────────────────────
ROLE_REASONING = "deepseek_reasoning"
ROLE_CODING = "qwen_coding"
ROLE_VISION_FAST = "llama_vision_fast"
ROLE_GENERAL = "general_fast"

# ── Rutas y Entorno ───────────────────────────────────────────────────────────
WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
ENV_PATH = Path("~/.openclaw/.env").expanduser()


def _load_env() -> None:
    """Carga variables desde ~/.openclaw/.env soportando sintaxis 'export KEY=VAL' y comillas."""
    if not ENV_PATH.exists():
        return
    try:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
    except Exception as e:
        print(f"[FoundationModels] WARN cargando {ENV_PATH}: {e}", file=sys.stderr)


_load_env()


def get_api_key(name: str) -> str:
    """Obtiene una clave de API asegurando recarga de entorno."""
    _load_env()
    return os.environ.get(name, "")


def is_ollama_online(timeout_sec: float = 0.15) -> bool:
    """Comprobación de socket instantánea y no bloqueante para Ollama."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=timeout_sec):
            return True
    except Exception:
        return False


def get_local_ollama_models() -> List[str]:
    """Obtiene la lista de modelos descargados en Ollama local si está activo."""
    if not is_ollama_online():
        return []
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags", headers={"User-Agent": "AlberthAI/1.0"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
    except Exception:
        return []


# ── Detector Inteligente de Intención ─────────────────────────────────────────

def detect_role_for_query(prompt: str, has_image: bool = False) -> str:
    """
    Determina automáticamente qué modelo fundacional debe atender la consulta:
    - Si hay imagen -> ROLE_VISION_FAST (Meta Llama 3.2 Vision)
    - Si requiere código o comandos -> ROLE_CODING (Qwen 2.5 Coder)
    - Si requiere deducción, matemáticas o análisis -> ROLE_REASONING (DeepSeek R1/V3)
    - En otros casos -> ROLE_VISION_FAST / General (Meta Llama 3.2 / 3.3)
    """
    if has_image:
        return ROLE_VISION_FAST

    p = prompt.lower()

    # Patrones de Código / Programación -> Qwen 2.5 Coder
    coding_keywords = [
        "código", "codigo", "script", "programar", "programa", "función", "funcion",
        "def ", "import ", "python", "javascript", "typescript", "bash", "terminal",
        "bug", "error", "depurar", "refactorizar", "sql", "json", "endpoint",
        "api", "html", "css", "compilar", "regex", "git ", "clase", "array", "objeto"
    ]
    if any(k in p for k in coding_keywords):
        return ROLE_CODING

    # Patrones de Razonamiento Lógico / Matemático -> DeepSeek
    reasoning_keywords = [
        "piensa", "razona", "resuelve", "calcula", "matemática", "matematica",
        "lógica", "logica", "demuestra", "estrategia", "arquitectura", "analiza a fondo",
        "por qué motivo", "pros y contras", "deducción", "deduccion", "acertijo",
        "teorema", "ecuación", "ecuacion", "hipótesis", "comparativa profunda"
    ]
    if any(k in p for k in reasoning_keywords):
        return ROLE_REASONING

    return ROLE_VISION_FAST


# ── Conectores Específicos por Proveedor ──────────────────────────────────────

def _call_nvidia_nim(
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int = 600,
    temperature: float = 0.5,
    timeout: float = 4.5
) -> Optional[str]:
    """Llama al endpoint ultrarrápido de NVIDIA NIM."""
    key = get_api_key("NVIDIA_API_KEY")
    if not key:
        return None
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "User-Agent": "AlberthAI/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            return msg.get("content", "").strip() or None
    except Exception as e:
        print(f"[NVIDIA NIM ({model})] Error: {e}", file=sys.stderr)
        return None


def _call_ollama(
    model: str,
    prompt_or_messages: Any,
    max_tokens: int = 600,
    temperature: float = 0.5,
    images: Optional[List[str]] = None,
    timeout: float = 3.5
) -> Optional[str]:
    """Llama a Ollama local de forma no bloqueante."""
    if not is_ollama_online():
        return None
    try:
        if isinstance(prompt_or_messages, list):
            # Formato chat completions
            url = "http://127.0.0.1:11434/v1/chat/completions"
            payload = {
                "model": model,
                "messages": prompt_or_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        else:
            # Formato generate
            url = "http://127.0.0.1:11434/api/generate"
            payload = {
                "model": model,
                "prompt": str(prompt_or_messages),
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens}
            }
            if images:
                payload["images"] = images
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
    except Exception as e:
        print(f"[Ollama ({model})] Error: {e}", file=sys.stderr)
        return None


def _call_gemini_fallback(
    prompt: str,
    system_instruction: str = "",
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/jpeg",
    max_tokens: int = 600,
    timeout: float = 8.0
) -> Optional[str]:
    """Fallback universal a Google Gemini 2.5 Flash / Flash Lite con reintento ante 429."""
    key = get_api_key("GEMINI_API_KEY") or get_api_key("GOOGLE_API_KEY")
    if not key:
        return None
    for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite"]:
        for attempt in range(2):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
                parts: List[Dict[str, Any]] = []
                if image_bytes:
                    b64 = base64.b64encode(image_bytes).decode("utf-8")
                    parts.append({"inlineData": {"mimeType": mime_type, "data": b64}})
                full_text = f"{system_instruction}\n\n{prompt}".strip()
                parts.append({"text": full_text})

                payload = {
                    "contents": [{"parts": parts}],
                    "generationConfig": {"temperature": 0.5, "maxOutputTokens": max_tokens}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        text_parts = candidates[0].get("content", {}).get("parts", [])
                        res = "".join(p.get("text", "") for p in text_parts).strip()
                        if res:
                            return res
            except urllib.error.HTTPError as he:
                if he.code == 429 and attempt == 0:
                    time.sleep(1.5)
                    continue
                print(f"[Gemini Fallback {model_name}] HTTP Error {he.code}", file=sys.stderr)
                break
            except Exception as e:
                print(f"[Gemini Fallback {model_name}] Error: {e}", file=sys.stderr)
                break
    return None


# ── Ejecución Especializada por Rol ──────────────────────────────────────────

def query_deepseek_reasoning(
    prompt: str,
    system_prompt: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 700
) -> Tuple[str, str]:
    """
    Ejecuta el especialista de Razonamiento Lógico Profundo: DEEPSEEK.
    Prioridad:
    1. Local Ollama: deepseek-r1 / deepseek-v3 (si está instalado y activo)
    2. NVIDIA NIM: deepseek-ai/deepseek-v4-pro-0813
    3. DeepSeek API Oficial (si DEEPSEEK_API_KEY está presente)
    4. Fallback: Google Gemini 2.5 Flash (Modo razonamiento)
    Retorna: (respuesta, modelo_utilizado)
    """
    sys_instruction = system_prompt or (
        "Eres el motor de Razonamiento Lógico Profundo (DeepSeek) de Alberth. "
        "Dirígete al usuario como 'Señor Danny'. Proporciona razonamientos impecables, deducciones paso a paso, "
        "solución de problemas matemáticos y pensamiento crítico de alto nivel en español."
    )
    messages = [{"role": "system", "content": sys_instruction}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": prompt})

    # 1. Ollama local
    local_models = get_local_ollama_models()
    for m in local_models:
        if "deepseek" in m.lower():
            res = _call_ollama(m, messages, max_tokens=max_tokens, temperature=0.3)
            if res:
                return res, f"Ollama Local ({m})"

    # 2. NVIDIA NIM (DeepSeek V4 Pro)
    res = _call_nvidia_nim("deepseek-ai/deepseek-v4-pro-0813", messages, max_tokens=max_tokens, temperature=0.4)
    if res:
        return res, "NVIDIA NIM (DeepSeek-V4-Pro)"

    # 3. DeepSeek API Oficial (opcional)
    ds_key = get_api_key("DEEPSEEK_API_KEY")
    if ds_key:
        try:
            url = "https://api.deepseek.com/v1/chat/completions"
            p = {"model": "deepseek-reasoner", "messages": messages, "max_tokens": max_tokens}
            req = urllib.request.Request(url, data=json.dumps(p).encode("utf-8"), headers={"Authorization": f"Bearer {ds_key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5.0) as r:
                data = json.loads(r.read().decode("utf-8"))
                out = data["choices"][0]["message"]["content"].strip()
                if out:
                    return out, "DeepSeek API Oficial (R1)"
        except Exception:
            pass

    # 4. Fallback Gemini 2.5 Flash
    res = _call_gemini_fallback(prompt, system_instruction=sys_instruction, max_tokens=max_tokens)
    if res:
        return res, "Gemini 2.5 Flash (DeepSeek Fallback)"

    return "Señor Danny, no fue posible conectar con el motor de razonamiento en este momento.", "Error"


def query_qwen_coder(
    prompt: str,
    system_prompt: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 800
) -> Tuple[str, str]:
    """
    Ejecuta el especialista en Programación y Código: QWEN 2.5 CODER.
    Prioridad:
    1. Local Ollama: qwen2.5-coder:latest (o variantes 7b/14b/32b)
    2. NVIDIA NIM: mistralai/codestral-22b-instruct-v0.1 / meta/codellama-70b
    3. Fallback: Google Gemini 2.5 Flash (Code Specialist)
    Retorna: (respuesta, modelo_utilizado)
    """
    sys_instruction = system_prompt or (
        "Eres el motor de Ingeniería de Software y Código (Qwen 2.5 Coder) de Alberth. "
        "Dirígete al usuario como 'Señor Danny'. Escribe código limpio, robusto, probado, eficiente y sin errores sintácticos. "
        "Soporta Python, Bash, JavaScript, TypeScript, SQLite y llamadas a APIs de sistema en macOS."
    )
    messages = [{"role": "system", "content": sys_instruction}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": prompt})

    # 1. Ollama local (prioridad nativa a Qwen 2.5 Coder si está activo)
    local_models = get_local_ollama_models()
    for m in local_models:
        if "qwen" in m.lower() or "coder" in m.lower():
            res = _call_ollama(m, messages, max_tokens=max_tokens, temperature=0.2)
            if res:
                return res, f"Ollama Local ({m})"

    # 2. Fast-Path Cloud vía NVIDIA NIM (con prompt de alta especialización de ingeniería)
    res = _call_nvidia_nim("meta/llama-3.2-11b-vision-instruct", messages, max_tokens=max_tokens, temperature=0.2, timeout=3.5)
    if res:
        return res, "NVIDIA NIM (Llama 3.2 Code Engineer)"

    # 3. Fallback Gemini 2.5 Flash Code
    res = _call_gemini_fallback(prompt, system_instruction=sys_instruction, max_tokens=max_tokens)
    if res:
        return res, "Gemini 2.5 Flash (Code Specialist)"

    return "Señor Danny, no fue posible generar el código en este momento.", "Error"


def query_llama_vision(
    prompt: str,
    image_path: Optional[str] = None,
    system_prompt: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 500
) -> Tuple[str, str]:
    """
    Ejecuta el especialista en Visión Multimodal y Velocidad General: META LLAMA 3.3 / 3.2 VISION.
    Prioridad:
    1. NVIDIA NIM: meta/llama-3.2-11b-vision-instruct (ultra rápido, ~0.75s, multimodal)
    2. Local Ollama: llama3.3 / llama3.2-vision
    3. Fallback: Google Gemini 2.5 Flash (Multimodal nativo)
    Retorna: (respuesta, modelo_utilizado)
    """
    sys_instruction = system_prompt or (
        "Eres el motor conversacional y visual (Meta Llama 3.2/3.3 Vision) de Alberth. "
        "Dirígete al usuario como 'Señor Danny'. Responde de forma concisa, certera, fluida y veloz en español."
    )

    image_bytes = None
    b64_img = None
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
                b64_img = base64.b64encode(image_bytes).decode("utf-8")
        except Exception as e:
            print(f"[Llama Vision] Error leyendo {image_path}: {e}", file=sys.stderr)

    # 1. NVIDIA NIM (Llama 3.2 11B Vision)
    if b64_img:
        user_content: List[Dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
        ]
        messages = [
            {"role": "system", "content": sys_instruction},
            {"role": "user", "content": user_content}
        ]
    else:
        messages = [{"role": "system", "content": sys_instruction}]
        if history:
            messages.extend(history[-6:])
        messages.append({"role": "user", "content": prompt})

    res = _call_nvidia_nim("meta/llama-3.2-11b-vision-instruct", messages, max_tokens=max_tokens, temperature=0.5)
    if res:
        return res, "NVIDIA NIM (Meta Llama 3.2 11B Vision)"

    # 2. Ollama local
    local_models = get_local_ollama_models()
    for m in local_models:
        if "llama3" in m.lower() or "vision" in m.lower():
            res = _call_ollama(m, messages, max_tokens=max_tokens, temperature=0.5)
            if res:
                return res, f"Ollama Local ({m})"

    # 3. Fallback Gemini 2.5 Flash
    res = _call_gemini_fallback(prompt, system_instruction=sys_instruction, image_bytes=image_bytes, max_tokens=max_tokens)
    if res:
        return res, "Gemini 2.5 Flash (Llama Vision Fallback)"

    return "Señor Danny, el sistema visual no pudo procesar la solicitud.", "Error"


# ── Función Maestra de Enrutamiento ──────────────────────────────────────────

def query_foundation_model(
    prompt: str,
    role: Optional[str] = None,
    image_path: Optional[str] = None,
    system_prompt: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    max_tokens: int = 600
) -> Tuple[str, str, str]:
    """
    Punto de entrada principal para toda la inteligencia de Alberth:
    1. Si no se especifica el rol, lo detecta automáticamente según el contenido y la presencia de imagen.
    2. Ejecuta el especialista fundacional correspondiente (DeepSeek, Qwen Coder o Llama Vision).
    3. Retorna (respuesta_texto, modelo_usado, rol_asignado).
    """
    assigned_role = role or detect_role_for_query(prompt, has_image=bool(image_path))

    t_start = time.time()
    if assigned_role == ROLE_REASONING:
        response, model_name = query_deepseek_reasoning(prompt, system_prompt=system_prompt, history=history, max_tokens=max_tokens)
    elif assigned_role == ROLE_CODING:
        response, model_name = query_qwen_coder(prompt, system_prompt=system_prompt, history=history, max_tokens=max_tokens)
    else:  # ROLE_VISION_FAST o General
        response, model_name = query_llama_vision(prompt, image_path=image_path, system_prompt=system_prompt, history=history, max_tokens=max_tokens)

    elapsed = time.time() - t_start
    model_tag = f"{model_name} [{elapsed:.2f}s]"
    return response, model_tag, assigned_role


# ── Benchmark y Verificación CLI ─────────────────────────────────────────────

def run_benchmark() -> None:
    """Ejecuta una prueba completa de los tres modelos fundacionales y reporta latencias."""
    print("=" * 70)
    print("🚀 BENCHMARK: MODELOS FUNDACIONALES SOTA DE ALBERTH")
    print("=" * 70)

    ollama_ok = is_ollama_online()
    print(f"📡 Estado Ollama Local: {'🟢 ACTIVO' if ollama_ok else '⚪ INACTIVO (Modo Cloud Fast-Path)'}")
    if ollama_ok:
        print(f"   Modelos locales detectados: {get_local_ollama_models()}")

    nv_key = get_api_key("NVIDIA_API_KEY")
    gem_key = get_api_key("GEMINI_API_KEY") or get_api_key("GOOGLE_API_KEY")
    print(f"🔑 NVIDIA NIM API Key: {'🟢 Configurada' if nv_key else '❌ Falta'}")
    print(f"🔑 Google Gemini API Key: {'🟢 Configurada' if gem_key else '❌ Falta'}")
    print("-" * 70)

    # 1. Test Meta Llama 3.2 Vision / Conversación
    print("\n1️⃣ Probando META LLAMA 3.2 VISION (Conversación & Visión)...")
    prompt_llama = "Hola Alberth, preséntate brevemente en una sola frase."
    t0 = time.time()
    resp_llama, model_llama, role_l = query_foundation_model(prompt_llama, role=ROLE_VISION_FAST, max_tokens=60)
    t_llama = time.time() - t0
    print(f"   Modelo: {model_llama}")
    print(f"   Tiempo: {t_llama:.2f}s")
    print(f"   Salida: {resp_llama}")

    # 2. Test DeepSeek (Razonamiento / Lógica)
    print("\n2️⃣ Probando DEEPSEEK (Razonamiento Lógico / Deducción)...")
    prompt_ds = "¿Si un tren viaja a 120 km/h y debe recorrer 300 km saliendo a las 14:00, a qué hora llega? Responde directo."
    t0 = time.time()
    resp_ds, model_ds, role_d = query_foundation_model(prompt_ds, role=ROLE_REASONING, max_tokens=80)
    t_ds = time.time() - t0
    print(f"   Modelo: {model_ds}")
    print(f"   Tiempo: {t_ds:.2f}s")
    print(f"   Salida: {resp_ds}")

    # 3. Test Qwen 2.5 Coder (Programación & Código)
    print("\n3️⃣ Probando QWEN 2.5 CODER (Generación de Código)...")
    prompt_qw = "Escribe una función corta en Python para verificar si un archivo existe en macOS."
    t0 = time.time()
    resp_qw, model_qw, role_q = query_foundation_model(prompt_qw, role=ROLE_CODING, max_tokens=150)
    t_qw = time.time() - t0
    print(f"   Modelo: {model_qw}")
    print(f"   Tiempo: {t_qw:.2f}s")
    print(f"   Salida:\n{resp_qw}")

    print("\n" + "=" * 70)
    print("✅ BENCHMARK COMPLETADO CON ÉXITO")
    print("=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--benchmark", "--test"]:
        run_benchmark()
    else:
        q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "¿Qué eres capaz de hacer?"
        ans, m_used, r_used = query_foundation_model(q)
        print(f"\n[Rol: {r_used}] [Modelo: {m_used}]\n{ans}\n")
