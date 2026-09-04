#!/usr/bin/env python3
# =============================================================================
# ALBERTH IMAGE HELPER — Generación de Imágenes (Pollinations AI)
#
# Genera imágenes a partir de texto usando Pollinations AI (100% gratuito,
# sin API key). Descarga la imagen y la abre en Preview.
# =============================================================================

import sys
import json
import subprocess
import urllib.parse
import os
import time


def log(msg):
    print(f"[ImageHelper] {msg}", file=sys.stderr, flush=True)


def generar_imagen(prompt: str) -> dict:
    """Genera una imagen con Pollinations AI y la muestra en Preview."""
    encoded_prompt = urllib.parse.quote(prompt)
    timestamp      = int(time.time())
    width, height  = 1024, 768

    # URL del servicio gratuito de generación de imágenes
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={timestamp}&nologo=true"

    output_path = f"/tmp/alberth_image_{timestamp}.png"
    log(f"Generando: '{prompt}'")
    log(f"URL: {url}")

    # Descargar imagen con curl
    result = subprocess.run(
        ["curl", "-sL", "--max-time", "60", "-o", output_path, url],
        capture_output=True, text=True, timeout=65
    )

    if result.returncode != 0:
        return {
            "success": False,
            "message": f"Error al descargar imagen: {result.stderr.strip()}",
            "url": url
        }

    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        return {
            "success": False,
            "message": "La imagen descargada está vacía o es inválida.",
            "url": url
        }

    file_size_kb = os.path.getsize(output_path) // 1024
    log(f"Imagen descargada: {output_path} ({file_size_kb} KB)")

    # Abrir en Preview (macOS)
    subprocess.Popen(["open", output_path])

    return {
        "success": True,
        "message": f"¡Imagen generada con éxito! Abriendo en Preview... ({file_size_kb} KB)",
        "path": output_path,
        "url": url
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        payload = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}
        prompt = payload.get("prompt", "")
    else:
        prompt = " ".join(sys.argv[1:])

    if not prompt:
        print(json.dumps({"success": False, "message": "No se especificó un prompt."}))
        sys.exit(1)

    result = generar_imagen(prompt)
    print(json.dumps(result, ensure_ascii=False))
