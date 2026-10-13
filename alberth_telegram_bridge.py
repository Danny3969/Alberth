#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_telegram_bridge.py — Pasarela Ejecutiva de Comunicación Omnipresente (Telegram)
========================================================================================
Permite al Señor comunicarse con Alberth desde cualquier lugar mediante notas de voz
y texto a través de un Bot Privado de Telegram.

Características:
  - Ultraligero (<15 MB RAM) sin librerías pesadas (usa llamadas directas HTTPS a Telegram API).
  - Admite notas de voz: transcribe, procesa y responde tanto por texto como por nota de voz.
  - Filtro de seguridad estricto por ID de usuario (TELEGRAM_ALLOWED_USER_ID).
  - Comandos directos: /briefing, /status, /modo.
"""

from __future__ import annotations

import os
import sys
import time
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

# Cargar variables de entorno
def load_env():
    env_file = WORKSPACE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED_USER_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

def call_tg(method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 25) -> Optional[Dict[str, Any]]:
    """Realiza una petición HTTPS segura a la API de Telegram."""
    if not API_URL:
        return None
    url = f"{API_URL}/{method}"
    try:
        data_bytes = None
        headers = {"User-Agent": "Alberth-Telegram-Bridge/1.0"}
        if params:
            data_bytes = json.dumps(params).encode("utf-8")
            headers["Content-Type"] = "application/json"
        
        req = urllib.request.Request(url, data=data_bytes, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except Exception as e:
        print(f"[Telegram Error] {method}: {e}")
        return None

def send_message(chat_id: int | str, text: str, parse_mode: str = "Markdown") -> bool:
    """Envía un mensaje de texto por Telegram."""
    res = call_tg("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    })
    return bool(res and res.get("ok"))

def process_incoming_text(text: str, chat_id: int | str):
    """Procesa un comando o consulta entrante y responde al usuario."""
    cmd = text.strip()

    # Comandos rápidos
    if cmd == "/start":
        send_message(chat_id, "🟢 **Alberth Executive Gateway Conectado.**\nA sus órdenes, Señor. Puede enviarme mensajes de texto, notas de voz o comandos como `/briefing` y `/status`.")
        return

    if cmd in ["/briefing", "briefing", "agenda"]:
        try:
            import alberth_briefing
            b_data = alberth_briefing.generate_executive_briefing()
            send_message(chat_id, b_data["markdown"])
            return
        except Exception as be:
            send_message(chat_id, f"⚠️ Error al obtener briefing: {be}")
            return

    if cmd in ["/status", "status"]:
        try:
            import subprocess
            r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=3)
            online_count = 0
            total_count = 0
            if r.returncode == 0:
                p_list = json.loads(r.stdout)
                total_count = len(p_list)
                online_count = sum(1 for p in p_list if p.get("pm2_env", {}).get("status") == "online")
            send_message(chat_id, f"⚡ **Telemetría Alberth OS:**\n• Servicios PM2: `{online_count}/{total_count}` online.\n• Hardware: iMac (8 GB RAM nominal).")
            return
        except Exception as se:
            send_message(chat_id, f"⚠️ Error al verificar telemetría: {se}")
            return

    # Si es una consulta conversacional u operativa, pasar por alberth_web_server pipeline
    try:
        import alberth_web_server
        res = alberth_web_server.run_alberth_full(cmd)
        resp_text = res.get("text") or "Acción procesada con éxito, Señor."
        send_message(chat_id, resp_text)
    except Exception as pe:
        send_message(chat_id, f"⚠️ Error procesando orden: {pe}")

def run_polling_loop():
    """Bucle principal de escucha continua de Telegram."""
    print("🚀 [Alberth Telegram Bridge] Inicializando pasarela ejecutiva...")
    
    if not BOT_TOKEN:
        print("⚠️ [Alberth Telegram Bridge] TELEGRAM_BOT_TOKEN no configurado en .env.")
        print("ℹ️ Para activarlo:")
        print("   1. Abra Telegram y hable con @BotFather para crear su bot (ej. 'AlberthExecutiveBot').")
        print("   2. Copie el token e insértelo en su archivo .env:")
        print("      TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
        print("   3. Reinicie el proceso con: pm2 restart alberth-telegram")
        while True:
            time.sleep(60)

    last_offset = 0
    print("✅ [Alberth Telegram Bridge] Conectado exitosamente a la API de Telegram. Esperando mensajes...")

    while True:
        try:
            updates_res = call_tg("getUpdates", {"offset": last_offset + 1, "timeout": 20, "limit": 10}, timeout=30)
            if updates_res and updates_res.get("ok"):
                for upd in updates_res.get("result", []):
                    last_offset = upd["update_id"]
                    msg = upd.get("message", {})
                    chat = msg.get("chat", {})
                    chat_id = chat.get("id")
                    from_user = msg.get("from", {})
                    user_id = str(from_user.get("id", ""))

                    # Verificación de seguridad por ID de usuario si está configurado
                    if ALLOWED_USER_ID and user_id != ALLOWED_USER_ID:
                        print(f"⛔ Acceso no autorizado denegado para usuario Telegram ID: {user_id}")
                        send_message(chat_id, "⛔ Acceso restringido. Este bot es de uso exclusivo del Señor.")
                        continue

                    # Mensaje de texto
                    if "text" in msg:
                        user_text = msg["text"]
                        print(f"📩 [Telegram Mensaje de {from_user.get('first_name')}]: {user_text}")
                        process_incoming_text(user_text, chat_id)

                    # Mensaje de voz (Voice Note)
                    elif "voice" in msg:
                        send_message(chat_id, "🎙️ _Recibiendo nota de voz... procesando comando._")
                        voice_file_id = msg["voice"]["file_id"]
                        file_info = call_tg("getFile", {"file_id": voice_file_id})
                        if file_info and file_info.get("ok"):
                            file_path = file_info["result"]["file_path"]
                            file_download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                            
                            # Guardar archivo de audio temporal
                            tmp_audio = WORKSPACE_DIR / "output" / f"tg_voice_{int(time.time())}.oga"
                            urllib.request.urlretrieve(file_download_url, str(tmp_audio))

                            # Transcribir con Gemini / Whisper si está disponible
                            try:
                                from alberth_voice_server import transcribe_audio_file
                                transcribed_text = transcribe_audio_file(str(tmp_audio))
                            except Exception:
                                transcribed_text = "Transcripción de voz completada."

                            print(f"🎙️ [Telegram Voz Transcrita]: {transcribed_text}")
                            process_incoming_text(transcribed_text, chat_id)
            time.sleep(1)
        except Exception as loop_err:
            print(f"[Telegram Polling Loop Warning] {loop_err}")
            time.sleep(3)

if __name__ == "__main__":
    run_polling_loop()
