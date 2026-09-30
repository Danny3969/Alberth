#!/usr/bin/env python3
# =============================================================================
# ALBERTH FACE RECOGNITION — Sistema de Reconocimiento Facial con Memoria
#
# Funcionalidades:
#   1. REGISTRAR PERSONA: Toma foto desde webcam o carga imagen → guarda encoding
#      Uso: python3 alberth_face_recognition.py register "Nombre Apellido"
#
#   2. RECONOCIMIENTO EN VIVO: Abre webcam y detecta + nombra en tiempo real
#      Uso: python3 alberth_face_recognition.py live
#
#   3. RECONOCER IMAGEN: Identifica personas en una imagen estática
#      Uso: python3 alberth_face_recognition.py identify ruta/imagen.jpg
#
#   4. LISTAR PERSONAS CONOCIDAS:
#      Uso: python3 alberth_face_recognition.py list
#
#   5. ELIMINAR PERSONA:
#      Uso: python3 alberth_face_recognition.py forget "Nombre Apellido"
#
#   6. SERVIDOR DE RECONOCIMIENTO CONTINUO (para integración con panel Alberth):
#      Uso: python3 alberth_face_recognition.py server [--port 8765]
#
# Dependencias: opencv-python, face-recognition, numpy, websockets
# =============================================================================

from __future__ import annotations
import sys, json, os, time, threading, base64, argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

# ─── Rutas de datos ──────────────────────────────────────────────────────────
WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).resolve().parent)
FACES_DIR     = WORKSPACE / "memory" / "faces"
ENCODINGS_DB  = FACES_DIR / "encodings.json"
FACES_PHOTOS  = FACES_DIR / "photos"
FACES_DIR.mkdir(parents=True, exist_ok=True)
FACES_PHOTOS.mkdir(parents=True, exist_ok=True)

# ─── Configuración de reconocimiento ─────────────────────────────────────────
TOLERANCE       = 0.52   # Tolerancia de similitud (0.4=estricto, 0.6=relajado)
SCALE_FACTOR    = 0.5    # Escalar frame para más velocidad
DETECTION_MODEL = "hog"  # "hog" (CPU/rápido) o "cnn" (GPU/preciso)

# ─── Colores HUD (BGR para OpenCV) ───────────────────────────────────────────
COLOR_KNOWN   = (0, 240, 255)   # Cyan — persona conocida
COLOR_UNKNOWN = (0, 80, 255)    # Naranja — desconocido
COLOR_BG      = (10, 14, 26)    # Fondo oscuro


class FaceDatabase:
    """Gestiona la base de datos de encodings de rostros conocidos."""

    def __init__(self):
        self._db: dict = self._load()

    def _load(self) -> dict:
        if ENCODINGS_DB.exists():
            try:
                return json.loads(ENCODINGS_DB.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save(self):
        ENCODINGS_DB.write_text(json.dumps(self._db, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_person(self, name: str, encoding: list, photo_path: str = ""):
        """Registra o actualiza una persona. Puede tener múltiples encodings."""
        slug = name.lower().replace(" ", "_")
        if slug not in self._db:
            self._db[slug] = {
                "name": name,
                "slug": slug,
                "photos": [],
                "encodings": [],
                "registered_at": datetime.now().isoformat(),
                "last_seen": None,
                "seen_count": 0,
            }
        self._db[slug]["encodings"].append(encoding)
        if photo_path:
            self._db[slug]["photos"].append(photo_path)
        self._db[slug]["last_updated"] = datetime.now().isoformat()
        self._save()
        return slug

    def update_last_seen(self, slug: str):
        if slug in self._db:
            self._db[slug]["last_seen"] = datetime.now().isoformat()
            self._db[slug]["seen_count"] = self._db[slug].get("seen_count", 0) + 1
            self._save()

    def get_all_encodings(self) -> tuple[list, list]:
        """Devuelve (encodings_array, names_array) para face_recognition.compare_faces."""
        import numpy as np
        encodings, names = [], []
        for slug, data in self._db.items():
            for enc in data.get("encodings", []):
                encodings.append(np.array(enc, dtype=float))
                names.append(data["name"])
        return encodings, names

    def forget(self, name: str) -> bool:
        slug = name.lower().replace(" ", "_")
        if slug in self._db:
            # Eliminar fotos
            for p in self._db[slug].get("photos", []):
                try:
                    Path(p).unlink()
                except Exception:
                    pass
            del self._db[slug]
            self._save()
            return True
        return False

    def list_people(self) -> list[dict]:
        return [
            {
                "name": d["name"],
                "encodings": len(d.get("encodings", [])),
                "seen_count": d.get("seen_count", 0),
                "last_seen": d.get("last_seen", "nunca"),
                "registered_at": d.get("registered_at", "?"),
            }
            for d in self._db.values()
        ]


# ─── Carga diferida de face_recognition y cv2 ────────────────────────────────
def _import_libs():
    """Importa las librerías pesadas en el momento de uso."""
    try:
        import face_recognition
        import cv2
        import numpy as np
        return face_recognition, cv2, np
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("   Instala con: venv/bin/pip install face-recognition opencv-python numpy")
        sys.exit(1)


def _draw_hud_box(frame, top, right, bottom, left, name: str, is_known: bool, cv2):
    """Dibuja una caja HUD estilo Alberth alrededor del rostro detectado."""
    color = COLOR_KNOWN if is_known else COLOR_UNKNOWN
    # Marco principal
    cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
    # Esquinas tácticas
    sz = 14
    for (x, y, dx, dy) in [(left, top, 1, 1), (right, top, -1, 1),
                             (left, bottom, 1, -1), (right, bottom, -1, -1)]:
        cv2.line(frame, (x, y), (x + dx * sz, y), color, 3)
        cv2.line(frame, (x, y), (x, y + dy * sz), color, 3)
    # Etiqueta de nombre
    label = name if is_known else "⚡ DESCONOCIDO"
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    cv2.rectangle(frame, (left, bottom), (left + tw + 10, bottom + th + 10), color, cv2.FILLED)
    cv2.putText(frame, label, (left + 5, bottom + th + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 14, 26), 1)


def cmd_register(name: str):
    """Captura foto desde webcam y registra a la persona."""
    fr, cv2, np = _import_libs()
    db = FaceDatabase()

    print(f"\n📷 Registrando: {name}")
    print("   Presiona ESPACIO para capturar el rostro, ESC para cancelar.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ No se pudo acceder a la cámara.")
        return

    captured = False
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detectar rostros en tiempo real
        small = cv2.resize(frame, (0, 0), fx=SCALE_FACTOR, fy=SCALE_FACTOR)
        rgb_small = small[:, :, ::-1]
        locations = fr.face_locations(rgb_small, model=DETECTION_MODEL)

        for (top, right, bottom, left) in locations:
            t, r, b, l = [int(v / SCALE_FACTOR) for v in (top, right, bottom, left)]
            _draw_hud_box(frame, t, r, b, l, f"Posiciona: {name}", True, cv2)

        cv2.putText(frame, f"Registrando: {name} | ESPACIO=capturar  ESC=cancelar",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_KNOWN, 2)
        cv2.imshow(f"Alberth — Registro: {name}", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("   Cancelado.")
            break
        elif key == 32:  # ESPACIO
            if not locations:
                print("   ⚠️  No se detectó ningún rostro. Reintenta.")
                continue

            # Tomar el primer rostro
            rgb_full = frame[:, :, ::-1]
            encodings = fr.face_encodings(rgb_full, [locations[0]])
            if not encodings:
                print("   ⚠️  No se pudo calcular el encoding. Reintenta.")
                continue

            encoding = encodings[0].tolist()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_name = f"{name.lower().replace(' ','_')}_{ts}.jpg"
            photo_path = str(FACES_PHOTOS / photo_name)
            cv2.imwrite(photo_path, frame)

            slug = db.add_person(name, encoding, photo_path)
            total = len(db._db.get(slug, {}).get("encodings", []))
            print(f"\n   ✅ ¡{name} registrado!")
            print(f"      Encodings totales: {total}")
            print(f"      Foto guardada: {photo_path}")
            captured = True
            break

    cap.release()
    cv2.destroyAllWindows()

    if not captured:
        print("   No se guardó ningún registro.")
    return captured


def cmd_live(notify_callback=None):
    """
    Reconocimiento facial en tiempo real desde la webcam.
    notify_callback(name, is_known): llamado cada vez que se detecta alguien.
    """
    fr, cv2, np = _import_libs()
    db = FaceDatabase()

    print("\n🎥 Modo RECONOCIMIENTO EN VIVO — Alberth Vision")
    print("   Presiona 'q' para salir | 'r' para añadir la persona actual")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ No se pudo acceder a la cámara.")
        return

    known_encodings, known_names = db.get_all_encodings()
    last_notify: dict[str, float] = {}
    NOTIFY_COOLDOWN = 10  # segundos entre notificaciones de la misma persona

    frame_count = 0
    face_results: list[tuple] = []  # cache entre frames

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        # Procesar solo 1 de cada 3 frames para rendimiento
        if frame_count % 3 == 0:
            small = cv2.resize(frame, (0, 0), fx=SCALE_FACTOR, fy=SCALE_FACTOR)
            rgb_small = small[:, :, ::-1]
            locations = fr.face_locations(rgb_small, model=DETECTION_MODEL)
            encodings = fr.face_encodings(rgb_small, locations)

            face_results = []
            for (loc, enc) in zip(locations, encodings):
                name, is_known = "Desconocido", False
                if known_encodings:
                    matches = fr.compare_faces(known_encodings, enc, tolerance=TOLERANCE)
                    dists = fr.face_distance(known_encodings, enc)
                    best_idx = int(np.argmin(dists)) if len(dists) > 0 else -1
                    if best_idx >= 0 and matches[best_idx]:
                        name = known_names[best_idx]
                        is_known = True
                        slug = name.lower().replace(" ", "_")
                        now = time.time()
                        if now - last_notify.get(name, 0) > NOTIFY_COOLDOWN:
                            db.update_last_seen(slug)
                            last_notify[name] = now
                            if notify_callback:
                                notify_callback(name, True)
                            else:
                                print(f"   👤 IDENTIFICADO: {name}")
                face_results.append((loc, name, is_known))

        # Dibujar resultados en el frame actual
        for (loc, name, is_known) in face_results:
            top, right, bottom, left = [int(v / SCALE_FACTOR) for v in loc]
            _draw_hud_box(frame, top, right, bottom, left, name, is_known, cv2)

        # HUD overlay
        ts_str = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"ALBERTH VISION · {ts_str} · Conocidos: {len(set(known_names))}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_KNOWN, 1)
        cv2.putText(frame, "q=salir  r=registrar nuevo",
                    (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 120, 120), 1)

        cv2.imshow("Alberth Vision — Reconocimiento Facial", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            # Registro rápido en vivo: pedir nombre por consola
            cap_name = input("\n   Nombre de la persona: ").strip()
            if cap_name:
                # Capturar frame actual para registrar
                rgb_full = frame[:, :, ::-1]
                if locations:
                    encs = fr.face_encodings(rgb_full, [locations[0]])
                    if encs:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        photo_path = str(FACES_PHOTOS / f"{cap_name.lower().replace(' ','_')}_{ts}.jpg")
                        cv2.imwrite(photo_path, frame)
                        db.add_person(cap_name, encs[0].tolist(), photo_path)
                        known_encodings, known_names = db.get_all_encodings()
                        print(f"   ✅ {cap_name} registrado desde vivo.")

    cap.release()
    cv2.destroyAllWindows()


def cmd_identify(image_path: str):
    """Identifica personas en una imagen estática."""
    fr, cv2, np = _import_libs()
    db = FaceDatabase()
    known_encodings, known_names = db.get_all_encodings()

    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ No se pudo cargar: {image_path}")
        return

    rgb = img[:, :, ::-1]
    locations = fr.face_locations(rgb, model=DETECTION_MODEL)
    encodings = fr.face_encodings(rgb, locations)

    print(f"\n🔍 Analizando imagen: {image_path}")
    print(f"   Rostros detectados: {len(locations)}")

    results = []
    for i, (loc, enc) in enumerate(zip(locations, encodings)):
        name, confidence = "Desconocido", 0.0
        if known_encodings:
            dists = fr.face_distance(known_encodings, enc)
            best_idx = int(np.argmin(dists))
            confidence = float(1.0 - dists[best_idx])
            if dists[best_idx] <= TOLERANCE:
                name = known_names[best_idx]

        top, right, bottom, left = loc
        _draw_hud_box(img, top, right, bottom, left, name, name != "Desconocido", cv2)
        result = {"face_index": i, "name": name, "confidence": round(confidence, 3), "location": list(loc)}
        results.append(result)
        print(f"   Rostro {i+1}: {name} (confianza: {confidence:.1%})")

    # Mostrar imagen anotada
    out_path = str(Path(image_path).parent / f"alberth_id_{Path(image_path).stem}.jpg")
    cv2.imwrite(out_path, img)
    print(f"   💾 Imagen anotada: {out_path}")
    cv2.imshow("Alberth — Identificación", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    return results


def cmd_list():
    """Lista todas las personas registradas."""
    db = FaceDatabase()
    people = db.list_people()
    if not people:
        print("\n   ℹ️  No hay personas registradas todavía.")
        print("   Usa: python3 alberth_face_recognition.py register \"Nombre\"")
        return

    print(f"\n👥 Personas registradas en Alberth ({len(people)}):")
    print("   " + "─" * 65)
    for p in people:
        seen = p["last_seen"][:16] if p["last_seen"] else "nunca"
        print(f"   👤 {p['name']:25} | {p['encodings']} enc. | visto {p['seen_count']}x | último: {seen}")


def cmd_forget(name: str):
    """Elimina una persona de la base de datos."""
    db = FaceDatabase()
    if db.forget(name):
        print(f"   ✅ '{name}' eliminado de la memoria de Alberth.")
    else:
        print(f"   ⚠️  '{name}' no encontrado. Usa 'list' para ver los nombres exactos.")


def cmd_server(port: int = 8765):
    """
    Servidor WebSocket de reconocimiento facial continuo.
    Transmite JSON con las detecciones al panel de Alberth en tiempo real.
    
    Protocolo (mensaje saliente):
    {
      "type": "face_detection",
      "faces": [{"name": "...", "is_known": true, "confidence": 0.95, "bbox": [top,right,bottom,left]}],
      "timestamp": "..."
    }
    """
    try:
        import asyncio
        import websockets
    except ImportError:
        print("❌ websockets no instalado. Ejecuta: venv/bin/pip install websockets")
        sys.exit(1)

    fr, cv2, np = _import_libs()
    db = FaceDatabase()

    print(f"\n🌐 Alberth Vision Server — WebSocket en ws://localhost:{port}")
    print("   Conectar desde el panel con: new WebSocket('ws://localhost:{port}')")

    clients: set = set()
    face_cache: list = []
    running = True

    async def broadcast(msg: dict):
        if clients:
            data = json.dumps(msg, ensure_ascii=False)
            await asyncio.gather(*[c.send(data) for c in list(clients)], return_exceptions=True)

    async def handler(websocket):
        clients.add(websocket)
        try:
            async for _ in websocket:
                pass  # Solo enviamos, no recibimos
        finally:
            clients.discard(websocket)

    async def capture_loop():
        nonlocal face_cache
        loop = asyncio.get_event_loop()
        known_encodings, known_names = db.get_all_encodings()
        cap = cv2.VideoCapture(0)
        frame_count = 0

        while running:
            ret, frame = cap.read()
            if not ret:
                await asyncio.sleep(0.1)
                continue

            frame_count += 1
            if frame_count % 5 == 0:  # 1 de cada 5 frames
                small = cv2.resize(frame, (0, 0), fx=SCALE_FACTOR, fy=SCALE_FACTOR)
                rgb_small = small[:, :, ::-1]

                def _detect():
                    locs = fr.face_locations(rgb_small, model=DETECTION_MODEL)
                    encs = fr.face_encodings(rgb_small, locs)
                    results = []
                    for loc, enc in zip(locs, encs):
                        name, confidence, is_known = "Desconocido", 0.0, False
                        if known_encodings:
                            dists = fr.face_distance(known_encodings, enc)
                            best_idx = int(np.argmin(dists))
                            confidence = float(1.0 - dists[best_idx])
                            if dists[best_idx] <= TOLERANCE:
                                name = known_names[best_idx]
                                is_known = True
                        results.append({
                            "name": name,
                            "is_known": is_known,
                            "confidence": round(confidence, 3),
                            "bbox": [int(v / SCALE_FACTOR) for v in loc]
                        })
                    return results

                faces = await loop.run_in_executor(None, _detect)
                face_cache = faces

                if clients and faces:
                    await broadcast({
                        "type": "face_detection",
                        "faces": faces,
                        "timestamp": datetime.now().isoformat()
                    })

            await asyncio.sleep(0.05)

        cap.release()

    async def main():
        async with websockets.serve(handler, "localhost", port):
            await asyncio.gather(capture_loop())

    asyncio.run(main())


# ─── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="alberth_face_recognition",
        description="🔍 Alberth — Sistema de Reconocimiento Facial con Memoria"
    )
    sub = parser.add_subparsers(dest="cmd")

    p_reg = sub.add_parser("register", help="Registrar nueva persona desde webcam")
    p_reg.add_argument("name", help="Nombre completo de la persona")

    sub.add_parser("live", help="Reconocimiento en vivo desde webcam")

    p_id = sub.add_parser("identify", help="Identificar personas en imagen")
    p_id.add_argument("image", help="Ruta a la imagen")

    sub.add_parser("list", help="Listar personas registradas")

    p_fgt = sub.add_parser("forget", help="Eliminar persona de la memoria")
    p_fgt.add_argument("name", help="Nombre de la persona a eliminar")

    p_srv = sub.add_parser("server", help="Iniciar servidor WebSocket continuo")
    p_srv.add_argument("--port", type=int, default=8765, help="Puerto WebSocket (default: 8765)")

    args = parser.parse_args()

    if args.cmd == "register":
        cmd_register(args.name)
    elif args.cmd == "live":
        cmd_live()
    elif args.cmd == "identify":
        cmd_identify(args.image)
    elif args.cmd == "list":
        cmd_list()
    elif args.cmd == "forget":
        cmd_forget(args.name)
    elif args.cmd == "server":
        cmd_server(args.port)
    else:
        parser.print_help()
