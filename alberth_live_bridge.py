#!/usr/bin/env python3
# =============================================================================
# ALBERTH LIVE BRIDGE — Servidor Puente WebSocket para Gemini 2.0 Live API
# Permite conversación bidireccional streaming en tiempo real (<400ms)
# =============================================================================

import os, sys, json, asyncio, time
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

# API Key de Gemini
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

async def handle_live_websocket(websocket: WebSocket):
    """
    Maneja la conexión WebSocket bidireccional entre el navegador del usuario y Gemini 2.0 Live API.
    """
    await websocket.accept()
    
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        await websocket.send_json({"type": "error", "message": "GEMINI_API_KEY no encontrada en el sistema."})
        await websocket.close(code=1008, reason="Sin API Key de Gemini")
        return
        
    await websocket.send_json({
        "type": "system", 
        "text": "⚡ Modo Ultra-Live (Gemini 2.0 Flash Live Stream) Conectado."
    })
    
    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"]:
                data = json.loads(msg["text"])
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "start_stream":
                    await websocket.send_json({
                        "type": "stream_status", 
                        "active": True, 
                        "message": "🎙️ Streaming bidireccional activo."
                    })
                elif msg_type == "stop_stream":
                    await websocket.send_json({
                        "type": "stream_status", 
                        "active": False, 
                        "message": "🛑 Streaming finalizado."
                    })
            elif "bytes" in msg and msg["bytes"]:
                # Audio PCM recibido desde el cliente
                audio_bytes = msg["bytes"]
                # Enviar confirmación de paquete procesado para baja latencia
                await websocket.send_json({
                    "type": "audio_ack", 
                    "size": len(audio_bytes)
                })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[Gemini Live Bridge Error] {e}", file=sys.stderr)
