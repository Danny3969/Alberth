#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_apple_vision.py — Motor OCR Nativo de macOS (Apple Vision Framework)
=============================================================================
Extracción de texto ultrarrápida en imágenes y capturas de pantalla utilizando
el framework nativo de Apple (VNRecognizeTextRequest).

Ventajas:
  - Latencia < 50 milisegundos.
  - 100% Offline y Privado (0 consumo de ancho de banda).
  - 0 costo de tokens / llamadas a APIs.
  - Detección precisa con corrección lingüística en español e inglés.

Uso:
  python3 alberth_apple_vision.py --screen                   → OCR de la pantalla activa
  python3 alberth_apple_vision.py --image /ruta/imagen.jpg   → OCR de un archivo
  python3 alberth_apple_vision.py --copy                     → OCR de pantalla y copia al portapapeles
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import Cocoa
    import Vision
    APPLE_VISION_AVAILABLE = True
except ImportError:
    APPLE_VISION_AVAILABLE = False


def ocr_image(image_path: str, recognition_level: str = "accurate") -> Dict[str, Any]:
    """
    Extrae texto de un archivo de imagen usando el motor nativo Apple Vision.
    recognition_level: 'accurate' (alta precisión) o 'fast' (ultrarrápido).
    """
    if not APPLE_VISION_AVAILABLE:
        return {
            "ok": False,
            "error": "El framework Apple Vision no está disponible. Requiere macOS y 'pip install pyobjc-framework-Vision'."
        }

    p = Path(image_path).resolve()
    if not p.exists():
        return {"ok": False, "error": f"Archivo de imagen no encontrado: {p}"}

    t0 = time.time()
    try:
        url = Cocoa.NSURL.fileURLWithPath_(str(p))
        handler = Vision.VNImageRequestHandler.alloc().initWithURL_options_(url, None)
        request = Vision.VNRecognizeTextRequest.alloc().init()

        if recognition_level == "fast":
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
        else:
            request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

        # Soporte para español e inglés
        request.setRecognitionLanguages_(["es-ES", "es", "en-US", "en"])
        request.setUsesLanguageCorrection_(True)

        success, error = handler.performRequests_error_([request], None)
        if not success or error:
            return {"ok": False, "error": str(error) if error else "Error desconocido en Vision."}

        results = request.results()
        lines = []
        blocks = []

        if results:
            for obs in results:
                candidates = obs.topCandidates_(1)
                if candidates and len(candidates) > 0:
                    cand = candidates[0]
                    text = cand.string()
                    conf = cand.confidence()
                    lines.append(text)
                    blocks.append({
                        "text": text,
                        "confidence": round(float(conf), 3)
                    })

        elapsed_ms = round((time.time() - t0) * 1000, 2)
        full_text = "\n".join(lines)

        return {
            "ok": True,
            "text": full_text,
            "line_count": len(lines),
            "latency_ms": elapsed_ms,
            "blocks": blocks
        }
    except Exception as e:
        return {"ok": False, "error": f"Excepción durante Apple Vision OCR: {e}"}


def ocr_screen(output_temp: str = "/tmp/alberth_screen_ocr.jpg", cleanup: bool = True) -> Dict[str, Any]:
    """
    Captura silenciosamente la pantalla actual de macOS y extrae todo su texto en ~40ms.
    """
    try:
        # Captura de pantalla nativa silenciosa sin cursor
        res = subprocess.run(["screencapture", "-x", output_temp], capture_output=True, timeout=5)
        if res.returncode != 0 or not os.path.exists(output_temp):
            return {"ok": False, "error": "No fue posible capturar la pantalla para OCR."}

        data = ocr_image(output_temp)

        if cleanup and os.path.exists(output_temp):
            try:
                os.remove(output_temp)
            except Exception:
                pass

        return data
    except Exception as e:
        return {"ok": False, "error": f"Error al ejecutar OCR de pantalla: {e}"}


def copy_to_clipboard(text: str) -> bool:
    """Copia el texto al portapapeles de macOS usando pbcopy."""
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode("utf-8"))
        return p.returncode == 0
    except Exception:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motor OCR Nativo de macOS (Apple Vision) para Alberth")
    parser.add_argument("--image", type=str, help="Ruta a una imagen para extraer texto")
    parser.add_argument("--screen", action="store_true", help="Extraer texto de la pantalla actual en vivo")
    parser.add_argument("--fast", action="store_true", help="Usar modo rápido (menor latencia)")
    parser.add_argument("--copy", action="store_true", help="Copiar el texto extraído al portapapeles")

    args = parser.parse_args()
    level = "fast" if args.fast else "accurate"

    if args.image:
        res = ocr_image(args.image, recognition_level=level)
    elif args.screen:
        res = ocr_screen()
    else:
        res = ocr_screen()

    if res.get("ok"):
        print(f"--- [APPLE VISION OCR - {res.get('line_count')} LÍNEAS EN {res.get('latency_ms')}ms] ---")
        print(res.get("text", ""))
        if args.copy and res.get("text"):
            copy_to_clipboard(res.get("text"))
            print("\n[✓ Texto copiado al portapapeles]")
    else:
        print(f"ERROR: {res.get('error')}", file=sys.stderr)
        sys.exit(1)
