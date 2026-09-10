#!/usr/bin/env python3
# =============================================================================
# ALBERTH TTS PREMIUM — Síntesis de voz cinematográfica con edge-tts
# Usa las voces de Microsoft Edge (alta calidad, sin costo).
# Voz por defecto: es-MX-DaliaNeural (femenina, clara, cálida)
# Alternativas masculinas: es-MX-JorgeNeural, es-ES-AlvaroNeural
#
# Uso:
#   python3 alberth_tts_premium.py "Texto a sintetizar" /ruta/salida.mp3
#   python3 alberth_tts_premium.py --list-voices  → lista voces en español
#
# Salida:
#   Archivo MP3 en la ruta especificada. Exit 0 = OK, Exit 1 = error.
# =============================================================================

import asyncio
import os
import sys
import subprocess

# ── Configuración de voz ──────────────────────────────────────────────────────
# Voces recomendadas en español:
#   es-MX-DaliaNeural   → Femenina, cálida, clara (México) — DEFAULT
#   es-MX-JorgeNeural   → Masculina, profesional (México)
#   es-ES-AlvaroNeural  → Masculina, elegante (España)
#   es-ES-ElviraNeural  → Femenina, natural (España)
#   es-AR-ElenaNeural   → Femenina, argentina
#   es-AR-TomasNeural   → Masculina, argentina
DEFAULT_VOICE = "es-MX-JorgeNeural"

# Ajustes de prosodia (edge-tts SSML)
# rate:  "-20%"  = más lento, "+0%" = normal, "+15%" = más rápido
# pitch: "-5Hz"  = más grave, "+0Hz" = normal, "+5Hz" = más agudo
SPEECH_RATE  = "-8%"    # Ligeramente más pausado — más solemne
SPEECH_PITCH = "-3Hz"   # Ligeramente más grave — más autoritario/serio


def log(msg: str):
    print(f"[TTS-Premium] {msg}", file=sys.stderr, flush=True)


def synthesize_offline(text: str, output_path: str) -> bool:
    """
    Sintetiza `text` de forma 100% local y offline usando el motor nativo de macOS (`/usr/bin/say`).
    Convierte a MP3 mediante ffmpeg o afconvert. Cero consumo de internet y cero dependencias pesadas.
    """
    try:
        temp_aiff = "/tmp/alberth_say_tmp.aiff"
        if os.path.exists(temp_aiff):
            os.remove(temp_aiff)

        # Elegir voz en español disponible (Paulina es_MX / Mónica es_ES / Eddy)
        voice_choice = "Paulina"
        cmd_say = ["/usr/bin/say", "-v", voice_choice, text, "-o", temp_aiff]
        res = subprocess.run(cmd_say, capture_output=True, timeout=10)
        if res.returncode != 0 or not os.path.exists(temp_aiff):
            # Reintentar con voz por defecto del sistema
            subprocess.run(["/usr/bin/say", text, "-o", temp_aiff], capture_output=True, timeout=10)

        if not os.path.exists(temp_aiff) or os.path.getsize(temp_aiff) == 0:
            log("ERROR: macOS say no pudo generar audio offline.")
            return False

        # Convertir a MP3 mediante ffmpeg
        ffmpeg_bin = "/usr/local/bin/ffmpeg" if os.path.exists("/usr/local/bin/ffmpeg") else "ffmpeg"
        res_conv = subprocess.run(
            [ffmpeg_bin, "-y", "-i", temp_aiff, "-codec:a", "libmp3lame", "-qscale:a", "4", output_path],
            capture_output=True, timeout=8
        )
        if res_conv.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            size_kb = os.path.getsize(output_path) // 1024
            log(f"OK (Fallback Offline) → Audio generado con macOS '{voice_choice}': {os.path.basename(output_path)} ({size_kb} KB)")
            return True

        # Fallback alternativo con afconvert si ffmpeg no estuviera disponible
        res_af = subprocess.run(
            ["/usr/bin/afconvert", "-f", "MP4F", "-d", "aac", temp_aiff, output_path],
            capture_output=True, timeout=6
        )
        if res_af.returncode == 0 and os.path.exists(output_path):
            log(f"OK (Offline AAC) → Audio generado con afconvert: {os.path.basename(output_path)}")
            return True

        return False
    except Exception as e:
        log(f"ERROR en fallback offline: {e}")
        return False


async def synthesize(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> bool:
    """
    Sintetiza `text` con edge-tts (online) y lo guarda en `output_path` (MP3).
    Si no hay conexión a internet o falla Edge-TTS, conmuta automáticamente
    al motor offline nativo de macOS para que Alberth nunca quede mudo.
    """
    # Asegurar directorio de salida
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text,
            voice,
            rate=SPEECH_RATE,
            pitch=SPEECH_PITCH,
        )
        await communicate.save(output_path)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            size_kb = os.path.getsize(output_path) // 1024
            log(f"OK (Online) → Audio generado: {os.path.basename(output_path)} ({size_kb} KB) | Voz: {voice}")
            return True
        else:
            log("Aviso: edge-tts no generó el archivo de salida.")
    except Exception as e:
        log(f"Aviso: Edge-TTS no disponible o sin conexión ({e}).")

    # ── Fallback Automático Offline (macOS say) ──
    log("🔄 Activando Fallback Offline de macOS...")
    return synthesize_offline(text, output_path)


async def list_es_voices():
    """Lista todas las voces disponibles en español."""
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        es_voices = [v for v in voices if v["Locale"].startswith("es-")]
        print(f"\n{'NOMBRE':<35} {'GÉNERO':<10} {'LOCALE'}")
        print("-" * 65)
        for v in sorted(es_voices, key=lambda x: x["Locale"]):
            print(f"{v['ShortName']:<35} {v['Gender']:<10} {v['Locale']}")
        print(f"\nTotal: {len(es_voices)} voces en español\n")
    except Exception as e:
        print(f"Error al listar voces: {e}")


def main():
    if len(sys.argv) < 2:
        print("Uso: alberth_tts_premium.py <texto> [ruta_salida.mp3] [--voice nombre_voz]")
        print("     alberth_tts_premium.py --list-voices")
        sys.exit(1)

    # ── Listar voces ──────────────────────────────────────────────────────────
    if sys.argv[1] == "--list-voices":
        asyncio.run(list_es_voices())
        sys.exit(0)

    # ── Síntesis ──────────────────────────────────────────────────────────────
    # Parsear argumentos
    text       = None
    output_mp3 = None
    voice      = DEFAULT_VOICE

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--voice" and i + 1 < len(sys.argv):
            voice = sys.argv[i + 1]
            i += 2
        elif text is None:
            text = sys.argv[i]
            i += 1
        elif output_mp3 is None:
            output_mp3 = sys.argv[i]
            i += 1
        else:
            i += 1

    if not text:
        log("ERROR: No se proporcionó texto para sintetizar.")
        sys.exit(1)

    # Ruta de salida por defecto
    if not output_mp3:
        output_mp3 = "/tmp/alberth_tts_premium.mp3"

    log(f"Sintetizando {len(text)} caracteres con voz '{voice}'...")
    success = asyncio.run(synthesize(text, output_mp3, voice))

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
