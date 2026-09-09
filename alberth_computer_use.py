#!/usr/bin/env python3
# =============================================================================
# ALBERTH COMPUTER USE — Automatización Visual Autónoma de macOS (Costo $0.00)
#
# Alternativa Gratuita y de Código Abierto a Anthropic Computer Use API:
#   1. Captura de pantalla nativa (/usr/sbin/screencapture).
#   2. Localización visual y Grounding de coordenadas con Google Gemini 2.5 Flash (Capa gratuita).
#   3. Fallback a NVIDIA NIM Llama 3.2 11B Vision.
#   4. Ejecución nativa de eventos de ratón y teclado mediante PyAutoGUI.
#
# Acciones soportadas:
#   - click, double_click, right_click
#   - type (escribir texto)
#   - press / hotkey (Return, Escape, Command+Espacio, etc.)
#   - scroll (desplazamiento vertical)
#
# Uso:
#   python3 alberth_computer_use.py "haz clic en el icono de Safari"
#   python3 alberth_computer_use.py --coord 500 300
#   python3 alberth_computer_use.py --type "Hola Señor Danny"
# =============================================================================

from __future__ import annotations
import os
import sys
import json
import time
import base64
import subprocess
import urllib.request
import urllib.error
import re
from typing import Dict, Any, Tuple, Optional

# Cargar variables de entorno desde ~/.openclaw/.env
env_file = os.path.expanduser("~/.openclaw/.env")
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("export "):
                line = line[7:].strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

WORKSPACE_DIR = os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or os.path.dirname(os.path.abspath(__file__))
TEMP_SCREENSHOT = "/tmp/alberth_computer_use_screen.jpg"


def log(msg: str):
    print(f"[ComputerUse] {msg}", file=sys.stderr, flush=True)


def capture_screen() -> Tuple[bool, str, int, int]:
    """Captura la pantalla completa, comprime a JPEG 1280px para subida instantánea y obtiene la resolución real."""
    import pyautogui
    w, h = pyautogui.size()
    try:
        if os.path.exists(TEMP_SCREENSHOT):
            os.remove(TEMP_SCREENSHOT)
        res = subprocess.run(["/usr/sbin/screencapture", "-x", "-t", "jpg", TEMP_SCREENSHOT], timeout=5)
        if res.returncode == 0 and os.path.exists(TEMP_SCREENSHOT) and os.path.getsize(TEMP_SCREENSHOT) > 0:
            # Comprimir a 1280px para subida ultrarrápida (reduce tamaño de 4MB a ~100KB)
            subprocess.run(["/usr/bin/sips", "-Z", "1280", TEMP_SCREENSHOT], capture_output=True, timeout=4)
            return True, TEMP_SCREENSHOT, w, h
    except Exception as e:
        log(f"Error al capturar pantalla: {e}")
    return False, "", w, h


def _clean_json(text: str) -> str:
    """Extrae JSON puro eliminando markdown."""
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


def locate_ui_element(instruction: str, screenshot_path: str, screen_w: int, screen_h: int) -> Optional[Dict[str, Any]]:
    """Usa Gemini 2.5 Flash (Gratis) o NVIDIA NIM para analizar la pantalla y devolver la acción y coordenadas."""
    with open(screenshot_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = f"""Eres el agente de Computer Use de Alberth para macOS.
Tu tarea es observar la captura de pantalla y determinar la acción precisa de ratón o teclado para cumplir la siguiente orden del usuario:
"{instruction}"

La pantalla tiene una resolución de {screen_w}x{screen_h} píxeles.
Devuelve las coordenadas en una escala normalizada de 0 a 1000 (donde [0, 0] es la esquina superior izquierda y [1000, 1000] es la esquina inferior derecha).

Devuelve ÚNICAMENTE un objeto JSON válido con este formato:
{{
  "pensamiento": "Breve explicación de qué elemento visual detectaste",
  "accion": "click" | "double_click" | "right_click" | "type" | "press" | "scroll",
  "coordenadas": [x_normalizado, y_normalizado],
  "texto": "texto a escribir si accion es type",
  "tecla": "tecla a presionar si accion es press (ej: return, escape, space, tab, backspace, command)",
  "direccion": "up" | "down"
}}
"""

    # 1. Google Gemini 2.5 Flash (Capa gratuita)
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            log("Analizando pantalla con Google Gemini 2.5 Flash...")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inlineData": {
                                    "mimeType": "image/jpeg",
                                    "data": img_b64
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json"
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                txt = res["candidates"][0]["content"]["parts"][0]["text"].strip()
                cleaned = _clean_json(txt)
                data = json.loads(cleaned)
                log(f"Gemini Grounding OK → {data.get('accion')} en {data.get('coordenadas')}")
                return data
        except Exception as e:
            log(f"Gemini Computer Use error: {e}")

    # 2. Fallback: NVIDIA NIM Llama 3.2 Vision
    nv_key = os.environ.get("NVIDIA_API_KEY")
    if nv_key:
        try:
            log("Intentando fallback con NVIDIA NIM Llama 3.2 Vision...")
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                        ]
                    }
                ],
                "max_tokens": 250,
                "temperature": 0.1
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {nv_key}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                txt = res["choices"][0]["message"]["content"].strip()
                cleaned = _clean_json(txt)
                data = json.loads(cleaned)
                log(f"NVIDIA Grounding OK → {data.get('accion')}")
                return data
        except Exception as e:
            log(f"NVIDIA Computer Use error: {e}")

    return None


def execute_action(action_data: Dict[str, Any], screen_w: int, screen_h: int) -> Dict[str, Any]:
    """Ejecuta la acción de ratón o teclado en el sistema macOS."""
    import pyautogui
    pyautogui.FAILSAFE = True

    accion = action_data.get("accion", "click").lower()
    pensamiento = action_data.get("pensamiento", "")
    coords = action_data.get("coordenadas") or [500, 500]

    # Convertir coordenadas normalizadas (0-1000) a píxeles reales de la pantalla
    norm_x, norm_y = coords[0], coords[1]
    real_x = int((norm_x / 1000.0) * screen_w)
    real_y = int((norm_y / 1000.0) * screen_h)

    # Limitar dentro de los bordes de la pantalla
    real_x = max(5, min(screen_w - 5, real_x))
    real_y = max(5, min(screen_h - 5, real_y))

    try:
        if accion == "click":
            log(f"Moviendo a ({real_x}, {real_y}) y haciendo clic...")
            pyautogui.moveTo(real_x, real_y, duration=0.25)
            pyautogui.click()
            return {"exito": True, "accion": "click", "coordenadas": [real_x, real_y], "detalle": pensamiento}

        elif accion == "double_click":
            log(f"Haciendo doble clic en ({real_x}, {real_y})...")
            pyautogui.moveTo(real_x, real_y, duration=0.25)
            pyautogui.doubleClick()
            return {"exito": True, "accion": "double_click", "coordenadas": [real_x, real_y], "detalle": pensamiento}

        elif accion == "right_click":
            log(f"Haciendo clic derecho en ({real_x}, {real_y})...")
            pyautogui.moveTo(real_x, real_y, duration=0.25)
            pyautogui.rightClick()
            return {"exito": True, "accion": "right_click", "coordenadas": [real_x, real_y], "detalle": pensamiento}

        elif accion == "type":
            text_to_type = action_data.get("texto", "")
            if coords:
                pyautogui.moveTo(real_x, real_y, duration=0.2)
                pyautogui.click()
                time.sleep(0.1)
            log(f"Escribiendo texto: '{text_to_type}'...")
            pyautogui.write(text_to_type, interval=0.03)
            return {"exito": True, "accion": "type", "texto": text_to_type, "detalle": pensamiento}

        elif accion == "press":
            key_name = action_data.get("tecla", "enter").lower()
            key_map = {
                "return": "enter", "intro": "enter", "escape": "esc", "espacio": "space",
                "borrar": "backspace", "tabulador": "tab"
            }
            mapped_key = key_map.get(key_name, key_name)
            log(f"Presionando tecla: {mapped_key}...")
            pyautogui.press(mapped_key)
            return {"exito": True, "accion": "press", "tecla": mapped_key, "detalle": pensamiento}

        elif accion == "scroll":
            direction = action_data.get("direccion", "down").lower()
            clicks = -6 if direction == "down" else 6
            log(f"Desplazando pantalla {direction}...")
            pyautogui.scroll(clicks)
            return {"exito": True, "accion": "scroll", "direccion": direction, "detalle": pensamiento}

    except Exception as e:
        log(f"Error al ejecutar acción de PyAutoGUI: {e}")
        return {"exito": False, "error": str(e)}

    return {"exito": False, "error": f"Acción desconocida: {accion}"}


def run_computer_action(instruction: str) -> Dict[str, Any]:
    """Flujo autónomo de Computer Use:
    1. Si la orden incluye coordenadas numéricas o comando directo, ejecuta en <1ms.
    2. Si es visual ('haz clic en el botón X'), captura pantalla, localiza con IA y ejecuta.
    """
    import pyautogui
    w, h = pyautogui.size()
    t0 = time.time()
    inst_lower = instruction.lower().strip()

    # ── Fast-Path Heurístico ──────────────────────────────────────────────────
    # A. Clic en el centro
    if "centro" in inst_lower and ("clic" in inst_lower or "click" in inst_lower):
        res = execute_action({"accion": "click", "coordenadas": [500, 500], "pensamiento": "Centro de la pantalla"}, w, h)
        res["tiempo_segundos"] = round(time.time() - t0, 3)
        res["orden"] = instruction
        return res

    # B. Coordenadas directas: "clic en 800 400"
    coord_match = re.search(r'\b(?:clic|click|mueve|posicion)\s+(?:en\s+)?(\d{2,4})\s*[,xX\s]\s*(\d{2,4})\b', instruction, re.I)
    if coord_match:
        cx, cy = int(coord_match.group(1)), int(coord_match.group(2))
        norm_x = int((cx / w) * 1000)
        norm_y = int((cy / h) * 1000)
        res = execute_action({"accion": "click", "coordenadas": [norm_x, norm_y], "pensamiento": f"Coordenadas directas {cx}x{cy}"}, w, h)
        res["tiempo_segundos"] = round(time.time() - t0, 3)
        res["orden"] = instruction
        return res

    # C. Escribir texto directo: "escribe Hola Mundo"
    type_match = re.search(r'^(?:escribe|teclea|digita)\s+["\']?(.+?)["\']?$', instruction, re.I)
    if type_match:
        txt = type_match.group(1).strip()
        res = execute_action({"accion": "type", "texto": txt, "coordenadas": None, "pensamiento": "Escritura directa de texto"}, w, h)
        res["tiempo_segundos"] = round(time.time() - t0, 3)
        res["orden"] = instruction
        return res

    # D. Presionar tecla directa: "presiona Enter" o "presiona Escape"
    press_match = re.search(r'\b(?:presiona|pulsa|tecla)\s+(enter|intro|return|escape|esc|espacio|space|tab|tabulador|borrar|backspace)\b', inst_lower)
    if press_match:
        key = press_match.group(1)
        res = execute_action({"accion": "press", "tecla": key, "pensamiento": f"Pulsación directa de tecla {key}"}, w, h)
        res["tiempo_segundos"] = round(time.time() - t0, 3)
        res["orden"] = instruction
        return res

    # ── Path Visual Autónomo (Grounding con IA) ───────────────────────────────
    ok, img_path, w, h = capture_screen()
    if not ok:
        return {"exito": False, "mensaje": "No se pudo capturar la pantalla para Computer Use."}

    action_data = locate_ui_element(instruction, img_path, w, h)
    if not action_data:
        return {"exito": False, "mensaje": f"No se pudo identificar en la pantalla cómo ejecutar: '{instruction}'."}

    result = execute_action(action_data, w, h)
    latency = round(time.time() - t0, 2)
    result["tiempo_segundos"] = latency
    result["orden"] = instruction
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Uso: alberth_computer_use.py '<instruccion>'"}))
        sys.exit(1)

    user_instruction = " ".join(sys.argv[1:])
    res = run_computer_action(user_instruction)
    print(json.dumps(res, ensure_ascii=False, indent=2))
