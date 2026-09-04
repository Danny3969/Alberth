#!/usr/bin/env python3
# =============================================================================
# ALBERTH VOICE SERVER — Servidor de Escucha Continua con VAD (Manos Libres)
# Escucha el micrófono de forma continua usando Voice Activity Detection (VAD).
# Cuando detecta que el usuario habla y luego guarda silencio (1.5s), guarda
# el audio en voice_exchange/input/ para que alberth_master.sh lo procese.
#
# Requisitos: pip3 install sounddevice webrtcvad
# Uso: python3 alberth_voice_server.py
# =============================================================================

import os
import sys
import time
import wave
import math
import struct
import collections
import threading
import sounddevice as sd
import webrtcvad

# ── Configuración ──────────────────────────────────────────────────────────────
WORKSPACE_DIR = "/Users/digitalspace/.openclaw/workspace"
INPUT_DIR     = os.path.join(WORKSPACE_DIR, "voice_exchange", "input")

SAMPLE_RATE    = 16000   # Hz — requerido por webrtcvad
FRAME_DURATION = 30      # ms por frame (10, 20 o 30)
CHANNELS       = 1       # mono

# Sensibilidad VAD: 0=más permisivo, 3=más estricto (menos falsos positivos)
# NOTA: bajado a 1 porque el micrófono genera señal baja y modo 3 descartaba habla real
VAD_AGGRESSIVENESS = 1

# Silencio posterior para cortar la grabación (en frames de FRAME_DURATION ms)
SILENCE_THRESHOLD_MS   = 1500  # ms de silencio = fin de turno
SILENCE_FRAMES_NEEDED  = int(SILENCE_THRESHOLD_MS / FRAME_DURATION)

# Mínimo de voz antes de guardar (evitar ruidos cortos)
# NOTA: reducido a 600ms para capturar comandos cortos
MIN_SPEECH_FRAMES = int(600 / FRAME_DURATION)  # ~600ms mínimo de habla

# Energía RMS mínima para considerar el audio como habla real
# NOTA: bajado de 400 a 120 porque el micrófono del sistema genera RMS ~116-270
RMS_ENERGY_THRESHOLD = 120  # ajustar si hay falsos negativos/positivos

# ── Estado global ──────────────────────────────────────────────────────────────
vad           = webrtcvad.Vad(VAD_AGGRESSIVENESS)
audio_buffer  = []          # frames de la grabación actual
ring_buffer   = collections.deque(maxlen=10)  # ventana deslizante de VAD
triggered     = False       # True = estamos en modo "hablando"
silence_count = 0           # frames de silencio consecutivos
lock          = threading.Lock()

FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION / 1000)   # muestras por frame


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[VoiceServer {ts}] {msg}", flush=True)


def compute_rms(frames: list) -> float:
    """Calcula la energía RMS promedio de los frames de audio 16-bit PCM."""
    raw = b"".join(frames)
    num_samples = len(raw) // 2
    if num_samples == 0:
        return 0.0
    samples = struct.unpack(f"{num_samples}h", raw)
    rms = math.sqrt(sum(s * s for s in samples) / num_samples)
    return rms


def save_audio(frames: list) -> str | None:
    """Guarda la lista de frames de audio como un archivo .wav en input/.
    Retorna None si la energía es demasiado baja (silencio/ruido ambiente)."""
    # ── Chequeo de energía RMS antes de guardar ──────────────────────────
    rms = compute_rms(frames)
    if rms < RMS_ENERGY_THRESHOLD:
        log(f"🔇 Audio descartado — energía RMS={rms:.0f} < umbral={RMS_ENERGY_THRESHOLD} (silencio/ruido)")
        return None

    os.makedirs(INPUT_DIR, exist_ok=True)
    ts      = time.strftime("%Y%m%d_%H%M%S")
    outpath = os.path.join(INPUT_DIR, f"alberth_voice_{ts}.wav")

    with wave.open(outpath, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)   # 16-bit PCM = 2 bytes
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))

    log(f"✅ Audio guardado (RMS={rms:.0f}): {os.path.basename(outpath)}")
    return outpath


def is_alberth_speaking() -> bool:
    """Comprueba si Alberth está reproduciendo audio por el altavoz."""
    return os.path.exists(os.path.join(WORKSPACE_DIR, "voice_exchange", ".alberth_speaking"))


def process_frame(pcm_bytes: bytes):
    """Evalúa un frame PCM con el VAD y gestiona el ciclo de grabación."""
    global triggered, silence_count, audio_buffer, ring_buffer

    # ── ANTI-ECO: Si Alberth está hablando, descartar TODO ──
    # Esto evita que el mic grabe la salida del altavoz
    if is_alberth_speaking():
        if triggered:
            # Estábamos grabando pero Alberth empezó a hablar → abortar
            log("🔇 Alberth hablando — descartando grabación en curso")
            triggered = False
            silence_count = 0
            audio_buffer = []
            ring_buffer.clear()
        return  # No procesar nada mientras habla

    try:
        is_speech = vad.is_speech(pcm_bytes, SAMPLE_RATE)
    except Exception:
        is_speech = False

    if not triggered:
        # Modo espera: llenar ring_buffer para detectar inicio de habla
        ring_buffer.append((pcm_bytes, is_speech))
        num_voiced = sum(1 for _, speech in ring_buffer if speech)

        # Si más del 70% del ring_buffer es voz → inicio del turno
        if num_voiced > 0.7 * ring_buffer.maxlen:
            triggered     = True
            silence_count = 0
            # Pre-incluir el contenido del ring_buffer (no perder el inicio)
            audio_buffer  = [f for f, _ in ring_buffer]
            ring_buffer.clear()
            log("🎙️  Voz detectada — grabando...")
    else:
        # Modo grabación: acumular frames
        audio_buffer.append(pcm_bytes)

        if is_speech:
            silence_count = 0
        else:
            silence_count += 1

        # Si hay suficiente silencio → fin del turno
        if silence_count >= SILENCE_FRAMES_NEEDED:
            log(f"🔇 Silencio detectado ({SILENCE_THRESHOLD_MS}ms) — finalizando turno")
            triggered     = False
            silence_count = 0

            # Solo guardar si hay suficiente contenido de habla
            if len(audio_buffer) >= MIN_SPEECH_FRAMES:
                save_audio(audio_buffer)
            else:
                log("⚠️  Grabación muy corta, descartada.")

            audio_buffer = []
            ring_buffer.clear()
            log("👂  Escuchando de nuevo...")


# ── Callback de sounddevice ────────────────────────────────────────────────────
overflow_count = 0

def audio_callback(indata, frames, time_info, status):
    """Recibe bloques de audio de sounddevice y los trocea en frames VAD."""
    global overflow_count

    if status and status.input_overflow:
        overflow_count += 1
        if overflow_count % 20 == 1:
            log(f"⚠️  Input overflow ×{overflow_count} (normal en uso intensivo de CPU)")

    # indata es un array NumPy (float32). Convertir a int16 PCM para webrtcvad
    import array as arr
    pcm_int16 = (indata[:, 0] * 32768).astype("int16")

    # Convertir a bytes
    raw = pcm_int16.tobytes()

    # Trocear en frames del tamaño exacto que webrtcvad necesita
    frame_bytes = FRAME_SIZE * 2  # 2 bytes por muestra int16
    i = 0
    while i + frame_bytes <= len(raw):
        with lock:
            process_frame(raw[i : i + frame_bytes])
        i += frame_bytes


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("Alberth Voice Server — Modo Manos Libres")
    log(f"  Sample rate      : {SAMPLE_RATE} Hz")
    log(f"  Frame duration   : {FRAME_DURATION} ms")
    log(f"  VAD aggressiveness: {VAD_AGGRESSIVENESS}")
    log(f"  Silence threshold : {SILENCE_THRESHOLD_MS} ms")
    log(f"  Output dir        : {INPUT_DIR}")
    log("=" * 60)
    log("👂  Listo. Hable cuando quiera...")

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=FRAME_SIZE,
            callback=audio_callback,
        ):
            while True:
                time.sleep(0.1)

    except KeyboardInterrupt:
        log("🛑 Voice Server detenido por el usuario.")
    except Exception as e:
        log(f"❌ Error crítico: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
