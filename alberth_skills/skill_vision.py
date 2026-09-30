#!/usr/bin/env python3
"""
skill_vision.py — Reconocimiento Facial & Vigilancia por Cámara
Identifica personas, registra nuevos rostros y vigila en tiempo real.
"""
from __future__ import annotations
from typing import Dict, Any

NAME = "vision"
DESCRIPTION = "Reconocimiento facial: identifica personas, registra nuevos rostros, vigilancia en tiempo real"
TRIGGER_KEYWORDS = [
    "quién es esta persona", "reconoce a", "identifica a", "registra a",
    "te presento a", "guarda esta cara", "reconocimiento facial",
    "quién está frente", "quien esta frente", "activa la cámara",
    "mira a", "captura la cámara",
]

def execute(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args:
        action (str): "identify" | "enroll"
        name   (str): nombre para registrar (solo si action="enroll")
    """
    action = args.get("action", "identify")
    name   = args.get("name", "").strip()

    try:
        import alberth_face_recognition as face
        if action == "enroll" and name:
            result = face.enroll_person(name)
            return {
                "success": True,
                "action": "enroll",
                "name": name,
                "summary": f"Rostro de '{name}' registrado. Alberth lo reconocerá automáticamente en futuras sesiones.",
            }
        else:
            result = face.identify_from_camera()
            identified = result.get("name", "Desconocido") if result else "Desconocido"
            confidence = result.get("confidence", 0.0) if result else 0.0
            return {
                "success": True,
                "action": "identify",
                "name": identified,
                "confidence": confidence,
                "summary": f"Persona identificada: {identified} (confianza: {confidence:.1%})" if identified != "Desconocido"
                           else "No se reconoció ninguna persona en el campo visual de la cámara.",
            }
    except ImportError:
        return {"error": "Módulo alberth_face_recognition no disponible.", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}
