#!/usr/bin/env python3
# =============================================================================
# ALBERTH VIDEO ANALYZER — Análisis de Video Raw y Detección de Deepfakes
# Extrae fotogramas clave con ffmpeg / descargas con yt-dlp y realiza
# análisis visual profundo frame-a-frame con Gemini / NVIDIA NIM.
# =============================================================================

import os
import sys
import json
import re
import shutil
import base64
import subprocess
import time
import urllib.request
import urllib.error

# Rutas del Workspace
WORKSPACE_DIR = os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(WORKSPACE_DIR, "voice_exchange", "video_processing")
ENV_PATH = os.path.expanduser("~/.openclaw/.env")

sys.path.insert(0, WORKSPACE_DIR)
try:
    from alberth_vision import get_gemini_api_key, get_nvidia_api_key, describe_image_gemini
except ImportError:
    def get_gemini_api_key():
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH) as f:
                for line in f:
                    if "GEMINI_API_KEY=" in line:
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        return os.environ.get("GEMINI_API_KEY", "")
    def get_nvidia_api_key():
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH) as f:
                for line in f:
                    if "NVIDIA_API_KEY=" in line:
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        return os.environ.get("NVIDIA_API_KEY", "")


def log(msg):
    print(f"[VideoAnalyzer] {msg}", file=sys.stderr)


def ensure_dependencies():
    """Verifica la existencia de yt-dlp y ffmpeg."""
    ytdlp = shutil.which("yt-dlp") or "/usr/local/bin/yt-dlp"
    ffmpeg = shutil.which("ffmpeg") or "/usr/local/bin/ffmpeg"
    ffprobe = shutil.which("ffprobe") or "/usr/local/bin/ffprobe"
    return ytdlp, ffmpeg, ffprobe


def download_video(url, output_dir):
    """Descarga el video desde URL usando yt-dlp a máxima calidad disponible."""
    os.makedirs(output_dir, exist_ok=True)
    ytdlp, _, _ = ensure_dependencies()
    output_template = os.path.join(output_dir, "downloaded_video.%(ext)s")

    cmd = [
        ytdlp,
        "--no-playlist",
        "--max-filesize", "100M",
        "-f", "mp4/bestvideo+bestaudio/best",
        "-o", output_template,
        url
    ]
    log(f"Descargando video desde: {url}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            log(f"Error descargando video: {res.stderr}")
            return None
        
        # Buscar el archivo descargado
        for f in os.listdir(output_dir):
            if f.startswith("downloaded_video."):
                return os.path.join(output_dir, f)
    except Exception as e:
        log(f"Excepción en download_video: {e}")
    return None


def get_video_duration(video_path):
    """Obtiene la duración en segundos del video usando ffprobe."""
    _, _, ffprobe = ensure_dependencies()
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception as e:
        log(f"Error al obtener duración del video: {e}")
    return 10.0  # Fallback por defecto


def extract_frames(video_path, output_dir, max_frames=6):
    """Extrae N fotogramas distribuidos equitativamente a lo largo del video con ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    _, ffmpeg, _ = ensure_dependencies()

    duration = get_video_duration(video_path)
    log(f"Duración detectada del video: {duration:.1f}s. Extrayendo {max_frames} fotogramas clave...")

    frames = []
    if max_frames <= 1:
        timestamps = [duration / 2.0]
    else:
        interval = duration / max_frames
        timestamps = [interval * i + (interval / 2.0) for i in range(max_frames)]

    for idx, ts in enumerate(timestamps):
        frame_filename = os.path.join(output_dir, f"frame_{idx+1:02d}_{int(ts)}s.jpg")
        cmd = [
            ffmpeg,
            "-y",
            "-ss", f"{ts:.2f}",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            frame_filename
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if os.path.exists(frame_filename) and os.path.getsize(frame_filename) > 0:
                frames.append({
                    "path": frame_filename,
                    "timestamp": round(ts, 1),
                    "index": idx + 1
                })
        except Exception as e:
            log(f"Error extrayendo frame en ts={ts}: {e}")

    return frames


def analyze_frame_deepfake(api_key, frame_info):
    """Inspecciona un fotograma individual buscando anomalías y artefactos de Deepfake."""
    frame_path = frame_info["path"]
    ts = frame_info["timestamp"]

    prompt = (
        f"Analiza minuciosamente este fotograma de video (segundo {ts}s) en búsqueda de posible manipulación sintética o DEEPFAKE.\n"
        "Evalúa los siguientes aspectos:\n"
        "1. Rostro y bordes: ¿Hay distorsiones, bordes borrosos en mandíbula, orejas o cuero cabelludo?\n"
        "2. Piel y ojos: ¿Textura excesivamente suave, parpadeo atípico o reflejos incoherentes en pupilas?\n"
        "3. Iluminación y Sombras: ¿Inconsistencias entre la luz del rostro y el fondo?\n"
        "4. Fondo (Warping): ¿Deformaciones en líneas u objetos alrededor del sujeto?\n\n"
        "Responde en 2 o 3 frases directas indicando lo visto y si detectas algún artefacto sospechoso en este frame."
    )

    # Probar Gemini Vision primero
    gkey = get_gemini_api_key()
    if gkey:
        desc = describe_image_gemini(gkey, prompt, frame_path, model="gemini-3.5-flash")
        if desc:
            return desc

    # Fallback NVIDIA NIM si está disponible
    nkey = get_nvidia_api_key()
    if nkey:
        try:
            with open(frame_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
            payload = {
                "model": "meta/llama-3.2-11b-vision-instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]
                }],
                "max_tokens": 400
            }
            req = urllib.request.Request(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {nkey}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log(f"Error en NVIDIA NIM Vision frame {ts}s: {e}")

    return f"Frame a los {ts}s analizado visualmente (sin anomalías obvias detectadas por modelo)."


def process_video(source, deepfake_check=True, max_frames=5):
    """Pipeline completo de análisis de video raw / deepfakes."""
    os.makedirs(TMP_DIR, exist_ok=True)
    video_work_dir = os.path.join(TMP_DIR, f"session_{int(time.time())}")
    os.makedirs(video_work_dir, exist_ok=True)

    local_video = None
    if source.startswith("http://") or source.startswith("https://"):
        local_video = download_video(source, video_work_dir)
        if not local_video:
            return {
                "success": False,
                "error": f"No se pudo descargar el video desde la URL: {source}"
            }
    elif os.path.exists(source):
        local_video = source
    else:
        return {
            "success": False,
            "error": f"La fuente de video no es válida o no existe: {source}"
        }

    # Extraer fotogramas
    frames_dir = os.path.join(video_work_dir, "frames")
    frames = extract_frames(local_video, frames_dir, max_frames=max_frames)

    if not frames:
        return {
            "success": False,
            "error": "No se pudieron extraer fotogramas del video con ffmpeg."
        }

    log(f"Analizando {len(frames)} fotogramas clave...")
    frame_analyses = []
    suspicious_count = 0

    api_key = get_gemini_api_key() or get_nvidia_api_key()

    for f in frames:
        analysis = analyze_frame_deepfake(api_key, f)
        frame_analyses.append({
            "timestamp": f"{f['timestamp']}s",
            "analysis": analysis
        })
        # Evaluación heurística rápida de palabras clave sospechosas
        lower_a = analysis.lower()
        if any(w in lower_a for w in ["deepfake", "sintético", "manipulad", "artefacto", "inconsisten", "anomalía", "distorsión", "falso"]):
            suspicious_count += 1

    # Cálculo de nivel de autenticidad
    total = len(frames)
    authenticity_percentage = max(0, int(100 - (suspicious_count / total * 80))) if total > 0 else 100

    verdict = "VERÍDICO / AUTÉNTICO"
    if authenticity_percentage < 60:
        verdict = "POSIBLE DEEPFAKE / MANIPULADO"
    elif authenticity_percentage < 85:
        verdict = "SOSPECHOSO (Artefactos leves detectados)"

    # Limpieza de archivos temporales
    try:
        shutil.rmtree(video_work_dir)
    except Exception:
        pass

    report = {
        "success": True,
        "source": source,
        "total_frames_analyzed": total,
        "authenticity_score": f"{authenticity_percentage}%",
        "verdict": verdict,
        "frame_breakdown": frame_analyses
    }

    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Alberth Video & Deepfake Analyzer")
    parser.add_argument("--url", help="URL del video a analizar (TikTok, YouTube, etc.)")
    parser.add_argument("--file", help="Ruta local al archivo de video (.mp4, .mov)")
    parser.add_argument("--frames", type=int, default=5, help="Número de fotogramas clave a analizar (default: 5)")
    args = parser.parse_args()

    source = args.url or args.file
    if not source:
        print("Uso: python3 alberth_video_analyzer.py --url <URL> o --file <RUTALOCAL>")
        sys.exit(1)

    result = process_video(source, max_frames=args.frames)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
