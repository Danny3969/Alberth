#!/usr/bin/env python3
# =============================================================================
# ALBERTH LIVE BRIDGE — Servidor Puente WebSocket para Gemini Live API
# Conversación por voz bidireccional streaming en tiempo real (<300ms)
# =============================================================================

import os
import sys
import json
import asyncio
import base64
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect
import websockets

from alberth_foundation_models import get_api_key

GEMINI_LIVE_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"

SYSTEM_INSTRUCTION = (
    "Eres Alberth, el mayordomo y asistente de inteligencia artificial personal de Señor. "
    "DEBES dirigirte al usuario estricta y respetuosamente como 'Señor' en todo momento. "
    "Bajo ninguna circunstancia uses tratamientos informales ni nombres propios como Danny; dirígete única y exclusivamente como 'Señor'. "
    "Tu personalidad es distinguida, refinada, sumamente educada, cálida, eficiente y leal. "
    "Responde siempre en español con elegancia británica moderna. Mantén tus intervenciones habladas concisas, fluidas y naturales "
    "para preservar una dinámica de conversación rápida y sin demoras innecesarias."
)

MODELS_PRIORITY = [
    "gemini-3.1-flash-live-preview",
    "gemini-2.5-flash-native-audio-preview-12-2025"
]

async def connect_gemini_live(api_key: str):
    """
    Intenta conectar con la API de Gemini Live probando los modelos en orden de prioridad.
    """
    last_error = None
    for model_name in MODELS_PRIORITY:
        url = f"{GEMINI_LIVE_URL}?key={api_key}"
        try:
            gemini_ws = await websockets.connect(
                url,
                ssl=True,
                max_size=10 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20
            )
            
            setup_payload = {
                "setup": {
                    "model": f"models/{model_name}",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {
                                    "voiceName": "Charon"
                                }
                            }
                        }
                    },
                    "systemInstruction": {
                        "parts": [{"text": SYSTEM_INSTRUCTION}]
                    },
                    "inputAudioTranscription": {}
                }
            }
            
            await gemini_ws.send(json.dumps(setup_payload))
            
            # Esperar confirmación de setup
            raw_resp = await asyncio.wait_for(gemini_ws.recv(), timeout=7.0)
            setup_data = json.loads(raw_resp) if isinstance(raw_resp, (str, bytes)) else {}
            
            if "setupComplete" in setup_data or not ("error" in setup_data):
                print(f"[Gemini Live Bridge] Conectado exitosamente con modelo '{model_name}'.", flush=True)
                return gemini_ws, model_name
            else:
                print(f"[Gemini Live Bridge] Respuesta no esperada con '{model_name}': {raw_resp}", file=sys.stderr)
                await gemini_ws.close()
        except Exception as e:
            last_error = e
            print(f"[Gemini Live Bridge] Error iniciando '{model_name}': {e}", file=sys.stderr)
            continue
            
    raise RuntimeError(f"No se pudo conectar a Gemini Live API con ningún modelo disponible: {last_error}")


async def handle_live_websocket(websocket: WebSocket):
    """
    Maneja la conexión WebSocket bidireccional entre el navegador del usuario y Gemini Live API.
    Reenvía audio PCM (16kHz) desde el micrófono del usuario a Gemini y reenvía
    el audio PCM sintetizado (24kHz) y transcripciones de vuelta al navegador.
    """
    # Validar token si es conexión remota
    client_host = websocket.client.host if websocket.client else ""
    is_local = client_host in ["127.0.0.1", "::1", "localhost"]
    token = websocket.query_params.get("token")
    expected = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    if expected and not is_local and token != expected:
        await websocket.close(code=1008, reason="Token de acceso inválido")
        return

    await websocket.accept()

    api_key = get_api_key("GEMINI_API_KEY") or get_api_key("GOOGLE_API_KEY")
    if not api_key:
        await websocket.send_json({
            "type": "error",
            "message": "GEMINI_API_KEY no encontrada en el sistema ni en ~/.openclaw/.env."
        })
        await websocket.close(code=1008, reason="Sin API Key de Gemini")
        return

    # Notificar al cliente que se está estableciendo el enlace
    await websocket.send_json({
        "type": "system",
        "text": "⚡ Estableciendo enlace neuronal de ultra-baja latencia con Gemini Live..."
    })

    try:
        gemini_ws, active_model = await connect_gemini_live(api_key)
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Fallo al conectar con Gemini Live API: {str(e)}"
        })
        await websocket.close(code=1011, reason=str(e))
        return

    await websocket.send_json({
        "type": "ready",
        "text": f"🎙️ Modo Ultra-Live Activo ({active_model} · Voz Charon). A su entera disposición, Señor.",
        "model": active_model
    })

    stop_event = asyncio.Event()

    async def client_to_gemini():
        """Recibe audio y mensajes del navegador y los envía a Gemini."""
        try:
            while not stop_event.is_set():
                msg = await websocket.receive()
                
                # Caso 1: Audio binario crudo PCM 16-bit 16kHz
                if "bytes" in msg and msg["bytes"]:
                    pcm_bytes = msg["bytes"]
                    if len(pcm_bytes) > 0:
                        encoded = base64.b64encode(pcm_bytes).decode("utf-8")
                        payload = {
                            "realtimeInput": {
                                "audio": {
                                    "data": encoded,
                                    "mimeType": "audio/pcm;rate=16000"
                                }
                            }
                        }
                        await gemini_ws.send(json.dumps(payload))

                # Caso 2: Mensaje JSON de texto / control
                elif "text" in msg and msg["text"]:
                    try:
                        data = json.loads(msg["text"])
                    except Exception:
                        continue

                    msg_type = data.get("type")

                    if msg_type == "audio" and "data" in data:
                        # Base64 enviado explícitamente en JSON
                        payload = {
                            "realtimeInput": {
                                "audio": {
                                    "data": data["data"],
                                    "mimeType": data.get("mimeType", "audio/pcm;rate=16000")
                                }
                            }
                        }
                        await gemini_ws.send(json.dumps(payload))

                    elif msg_type == "text" and "text" in data:
                        # Mensaje de texto inyectado en la sesión en vivo
                        payload = {
                            "realtimeInput": {
                                "text": data["text"]
                            }
                        }
                        await gemini_ws.send(json.dumps(payload))

                    elif msg_type == "audio_stream_end":
                        # Notificar fin de turno / silencio
                        payload = {
                            "realtimeInput": {
                                "audioStreamEnd": True
                            }
                        }
                        await gemini_ws.send(json.dumps(payload))

                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        except Exception as e:
            if not stop_event.is_set():
                print(f"[Gemini Live Bridge] Error en client_to_gemini: {e}", file=sys.stderr)
        finally:
            stop_event.set()

    async def gemini_to_client():
        """Recibe respuestas de audio, transcripción e interrupciones de Gemini y las envía al navegador."""
        try:
            while not stop_event.is_set():
                raw_msg = await gemini_ws.recv()
                if isinstance(raw_msg, bytes):
                    raw_msg = raw_msg.decode("utf-8")

                data = json.loads(raw_msg)

                if "serverContent" in data:
                    sc = data["serverContent"]

                    # 1. Detección de Interrupción (Barge-in: el usuario empezó a hablar mientras Alberth hablaba)
                    if sc.get("interrupted"):
                        await websocket.send_json({
                            "type": "interrupted",
                            "message": "Interrupción detectada"
                        })

                    # 2. Transcripción de lo que dijo el usuario
                    if "inputTranscription" in sc:
                        user_text = sc["inputTranscription"].get("text", "").strip()
                        if user_text:
                            await websocket.send_json({
                                "type": "user_transcript",
                                "text": user_text
                            })

                    # 3. Transcripción de la respuesta de Alberth
                    if "outputTranscription" in sc:
                        ai_text = sc["outputTranscription"].get("text", "").strip()
                        if ai_text:
                            await websocket.send_json({
                                "type": "ai_transcript",
                                "text": ai_text
                            })

                    # 4. Chunks de Audio PCM 24kHz de Alberth
                    if "modelTurn" in sc and "parts" in sc["modelTurn"]:
                        for part in sc["modelTurn"]["parts"]:
                            if "inlineData" in part:
                                inline = part["inlineData"]
                                audio_b64 = inline.get("data", "")
                                mime_type = inline.get("mimeType", "audio/pcm;rate=24000")
                                if audio_b64:
                                    await websocket.send_json({
                                        "type": "audio",
                                        "data": audio_b64,
                                        "mimeType": mime_type
                                    })

                    # 5. Fin de turno de respuesta
                    if sc.get("turnComplete"):
                        await websocket.send_json({
                            "type": "turn_complete"
                        })

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            if not stop_event.is_set():
                print(f"[Gemini Live Bridge] Error en gemini_to_client: {e}", file=sys.stderr)
        finally:
            stop_event.set()

    # Ejecutar ambas direcciones concurrentemente
    t1 = asyncio.create_task(client_to_gemini())
    t2 = asyncio.create_task(gemini_to_client())

    # Esperar a que una de las conexiones termine
    done, pending = await asyncio.wait(
        [t1, t2],
        return_when=asyncio.FIRST_COMPLETED
    )

    stop_event.set()
    for task in pending:
        task.cancel()

    try:
        await gemini_ws.close()
    except Exception:
        pass

    try:
        await websocket.close()
    except Exception:
        pass

    print("[Gemini Live Bridge] Sesión Ultra-Live finalizada limpiamente.", flush=True)
