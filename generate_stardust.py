#!/usr/bin/env python3
"""
generate_stardust.py
Sintetizador del Campo de Polvo Estelar Cuántico para Alberth (v6.0)
Inspirado en la obra canónica de Yuichiro Chino (Getty Images):
Rostro sereno de 14,000 micro-partículas estelares que se disuelve en el cosmos.
Cero cuellos cortados, cero maniquíes rígidos, cero 'valle inquietante'.
"""

import struct
import json
import math
import random
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
GLB_PATH = WORKSPACE / "panel" / "assets" / "identity" / "head.glb"
BIN_OUT = WORKSPACE / "panel" / "assets" / "identity" / "stardust_mesh.bin"

TOTAL_PARTICLES = 14000
FACE_PARTICLES = 8500
HALO_PARTICLES = 3500
COSMIC_PARTICLES = 2000

def load_glb_vertices(path):
    with open(path, "rb") as f:
        f.seek(12)
        chunk_len, _ = struct.unpack("<II", f.read(8))
        gltf = json.loads(f.read(chunk_len).decode("utf-8"))
        bin_chunk_len, _ = struct.unpack("<II", f.read(8))
        bin_data = f.read(bin_chunk_len)

    pos_acc = gltf["accessors"][1]
    pos_bv = gltf["bufferViews"][pos_acc["bufferView"]]
    pos_offset = pos_bv.get("byteOffset", 0) + pos_acc.get("byteOffset", 0)
    v_count = pos_acc["count"]

    raw_pos = []
    for i in range(v_count):
        x, y, z = struct.unpack_from("<fff", bin_data, pos_offset + i * 12)
        raw_pos.append((x, y, z))

    # Access indices
    idx_acc = gltf["accessors"][0]
    idx_bv = gltf["bufferViews"][idx_acc["bufferView"]]
    idx_offset = idx_bv.get("byteOffset", 0) + idx_acc.get("byteOffset", 0)
    i_count = idx_acc["count"]
    indices = [struct.unpack_from("<H", bin_data, idx_offset + i * 2)[0] for i in range(i_count)]

    return raw_pos, indices

def main():
    print(f"[*] Leyendo topología base desde {GLB_PATH}...")
    raw_pos, indices = load_glb_vertices(GLB_PATH)

    # Filtrar estrictamente solo la máscara facial anterior (sin nuca, sin cuello, sin hombros)
    # En el modelo original:
    # Nariz: z ~ 2.59, boca y = -0.11, ojos y = 1.67, frente y = 2.5 a 3.8
    # Descartamos todo lo que sea nuca (z < 0.2), cuello (y < -0.9), o partes laterales alejadas (|x| > 2.0)
    
    xs = [p[0] for p in raw_pos]
    ys = [p[1] for p in raw_pos]
    zs = [p[2] for p in raw_pos]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    cz = (min(zs) + max(zs)) / 2.0

    # Centrar modelo
    centered = [(p[0] - cx, p[1] - cy, p[2] - cz) for p in raw_pos]

    # Triángulos filtrados para la máscara facial
    face_triangles = []
    for i in range(0, len(indices), 3):
        i1, i2, i3 = indices[i], indices[i+1], indices[i+2]
        p1, p2, p3 = centered[i1], centered[i2], centered[i3]
        
        # Centroide del triángulo
        tx = (p1[0] + p2[0] + p3[0]) / 3.0
        ty = (p1[1] + p2[1] + p3[1]) / 3.0
        tz = (p1[2] + p2[2] + p3[2]) / 3.0

        # Máscara facial pura:
        # 1. Z frontal (sin cerebro posterior ni orejas profundas)
        # 2. Y por encima de -0.95 (corta antes del cuello y hombros)
        # 3. Ancho suave (|X| < 1.75 en barbilla, hasta 2.0 en pómulos/sien)
        if tz > 0.40 and ty > -0.95 and ty < 3.90:
            max_w = 1.4 + (ty + 1.0) * 0.25
            if abs(tx) < max_w:
                face_triangles.append((p1, p2, p3))

    print(f"[*] Triángulos faciales puros seleccionados: {len(face_triangles)}")

    # Calcular área de cada triángulo para muestreo de superficie uniforme
    def tri_area(p1, p2, p3):
        # Cross product
        v1 = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
        v2 = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
        cx = v1[1]*v2[2] - v1[2]*v2[1]
        cy = v1[2]*v2[0] - v1[0]*v2[2]
        cz = v1[0]*v2[1] - v1[1]*v2[0]
        return 0.5 * math.sqrt(cx*cx + cy*cy + cz*cz)

    areas = [tri_area(t[0], t[1], t[2]) for t in face_triangles]
    total_area = sum(areas)
    cum_areas = []
    c = 0.0
    for a in areas:
        c += a / total_area
        cum_areas.append(c)

    # Factor de escala para que la cara ocupe aprox 100 unidades de alto (radio ~50)
    # Centrado en el origen (0, 0, 0)
    face_y_coords = [p[1] for tri in face_triangles for p in tri]
    face_y_min, face_y_max = min(face_y_coords), max(face_y_coords)
    face_y_mid = (face_y_min + face_y_max) / 2.0
    face_scale = 96.0 / (face_y_max - face_y_min)

    # 1. Muestreo de las 8,500 partículas del rostro central
    random.seed(42)
    face_particles = []
    face_tags = []
    face_brightness = []
    face_sizes = []

    import bisect
    for _ in range(FACE_PARTICLES):
        r = random.random()
        idx = bisect.bisect_left(cum_areas, r)
        if idx >= len(face_triangles):
            idx = len(face_triangles) - 1
        p1, p2, p3 = face_triangles[idx]

        # Coordenadas baricéntricas aleatorias
        u = random.random()
        v = random.random()
        if u + v > 1.0:
            u = 1.0 - u
            v = 1.0 - v
        w = 1.0 - u - v

        x = p1[0]*u + p2[0]*v + p3[0]*w
        y = p1[1]*u + p2[1]*v + p3[1]*w
        z = p1[2]*u + p2[2]*v + p3[2]*w

        # Escalar y recentrar
        sx = x * face_scale
        sy = (y - face_y_mid) * face_scale
        sz = (z - 1.2) * face_scale

        # Leve jitter cuántico para sensación de polvo estelar continuo
        jitter = 0.45
        sx += (random.random() - 0.5) * jitter
        sy += (random.random() - 0.5) * jitter
        sz += (random.random() - 0.5) * jitter

        # Brillo basado en prominencia facial (puente nasal, labios, pómulos)
        # La nariz sobresale en z > 8.0, labios alrededor de y ~ -15
        dist_from_nose = math.sqrt(sx*sx + (sy - 2.0)*(sy - 2.0))
        is_center_face = dist_from_nose < 22.0
        is_nose_bridge = abs(sx) < 4.0 and -5.0 < sy < 16.0
        is_lips = abs(sx) < 11.0 and -18.0 < sy < -9.0

        tag = 1 # rostro base
        bright = 0.72 + random.random() * 0.28
        size = 1.8 + random.random() * 1.2

        if is_nose_bridge or is_lips:
            bright = 0.95 + random.random() * 0.35 # Resplandor focal
            size = 2.4 + random.random() * 1.4
            tag = 2
        elif is_center_face:
            bright = 0.85 + random.random() * 0.3
            tag = 3

        face_particles.append((sx, sy, sz))
        face_tags.append(tag)
        face_brightness.append(bright)
        face_sizes.append(size)

    # 2. Muestreo de las 3,500 partículas de disolución perimetral (Halo de transición cósmica)
    # Estas partículas se originan en el contorno del rostro y se dispersan hacia afuera
    for _ in range(HALO_PARTICLES):
        # Elegir un punto base del rostro aleatorio
        base = random.choice(face_particles)
        
        # Dispersión exponencial hacia el exterior (Gaussian dust)
        # Cuanto más lejos del centro, mayor dispersión
        dist_c = math.sqrt(base[0]*base[0] + base[1]*base[1])
        disp_radius = (dist_c / 48.0) ** 1.8 * 28.0 + random.random() * 18.0
        angle = random.random() * math.pi * 2
        
        hx = base[0] + math.cos(angle) * disp_radius
        hy = base[1] + math.sin(angle) * disp_radius
        hz = base[2] + (random.random() - 0.5) * (disp_radius * 0.8)

        # Brillo decrece con la distancia al centro
        fade = max(0.18, 1.0 - (math.sqrt(hx*hx + hy*hy) / 85.0))
        bright = (0.45 + random.random() * 0.45) * fade
        size = 1.2 + random.random() * 1.8

        face_particles.append((hx, hy, hz))
        face_tags.append(0) # polvo disperso
        face_brightness.append(bright)
        face_sizes.append(size)

    # 3. Muestreo de las 2,000 partículas cósmicas (Estrellas flotantes libres)
    for _ in range(COSMIC_PARTICLES):
        theta = random.random() * math.pi * 2
        phi = (random.random() - 0.5) * math.pi
        r = 55.0 + random.random() * 55.0
        
        cx = r * math.cos(phi) * math.cos(theta)
        cy = r * math.sin(phi)
        cz = r * math.cos(phi) * math.sin(theta)

        bright = 0.25 + random.random() * 0.70 # Estrellas parpadeantes
        size = 1.0 + random.random() * 2.2

        face_particles.append((cx, cy, cz))
        face_tags.append(0)
        face_brightness.append(bright)
        face_sizes.append(size)

    # 4. Generar Coordenadas de la Nebulosa Espiral Cósmica (Modo Reposo / Orbe)
    # Una espiral galáctica tridimensional que gira armónicamente
    nebula_particles = []
    for i in range(TOTAL_PARTICLES):
        # Distribución de galaxia espiral de 2 brazos con bulbo esférico central
        if i < 4000:
            # Bulbo nuclear de la nebulosa
            r = (random.random() ** 0.6) * 32.0
            theta = random.random() * math.pi * 2
            phi = (random.random() - 0.5) * math.pi * 0.75
            nx = r * math.cos(phi) * math.cos(theta)
            ny = r * math.sin(phi) * 0.85
            nz = r * math.cos(phi) * math.sin(theta)
        elif i < 11000:
            # Brazos espirales logarítmicos
            arm = random.choice([0, math.pi])
            t = random.random()
            r = 18.0 + t * 54.0
            spiral_angle = t * math.pi * 3.2 + arm
            disp = (random.random() - 0.5) * 8.0
            nx = math.cos(spiral_angle) * r + disp
            ny = (random.random() - 0.5) * (14.0 * (1.0 - t * 0.5))
            nz = math.sin(spiral_angle) * r + disp
        else:
            # Halo esférico exterior de micro-estrellas
            r = 60.0 + random.random() * 25.0
            theta = random.random() * math.pi * 2
            phi = (random.random() - 0.5) * math.pi
            nx = r * math.cos(phi) * math.cos(theta)
            ny = r * math.sin(phi)
            nz = r * math.cos(phi) * math.sin(theta)

        nebula_particles.append((nx, ny, nz))

    print(f"[*] Total de partículas sintetizadas: {len(face_particles)}")

    # 5. Empaquetar a binario de alta velocidad
    # Formato:
    # Header: "ALST" (4 bytes), count (uint32)
    # Sec 1: face_positions (count * 3 * float32)
    # Sec 2: nebula_positions (count * 3 * float32)
    # Sec 3: brightness (count * float32)
    # Sec 4: sizes (count * float32)
    # Sec 5: tags (count * uint8)
    out = bytearray()
    out.extend(b"ALST")
    out.extend(struct.pack("<IIII", TOTAL_PARTICLES, 0, 0, 0))

    # Face pos
    for p in face_particles:
        out.extend(struct.pack("<fff", p[0], p[1], p[2]))

    # Nebula pos
    for p in nebula_particles:
        out.extend(struct.pack("<fff", p[0], p[1], p[2]))

    # Brightness
    for b in face_brightness:
        out.extend(struct.pack("<f", b))

    # Sizes
    for s in face_sizes:
        out.extend(struct.pack("<f", s))

    # Tags
    for t in face_tags:
        out.append(t)

    # Alinear a 4 bytes
    while len(out) % 4 != 0:
        out.append(0)

    BIN_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(BIN_OUT, "wb") as f:
        f.write(out)

    print(f"[✓] Archivo binario generado con éxito: {BIN_OUT} ({len(out)/1024:.1f} KB)")

if __name__ == "__main__":
    main()
