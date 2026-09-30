#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_hindsight.py — Motor de Memoria Evolutiva (Inspirado en Hindsight de Vectorize.io)
=========================================================================================
Implementa el ciclo cognitivo:
  1. RETAIN:  Ingiere recuerdos estructurados clasificándolos en 4 redes lógicas:
              - 'world': Hechos objetivos sobre el entorno o proyectos.
              - 'experience': Tareas ejecutadas (qué se intentó y si falló/funcionó).
              - 'observation': Preferencias observadas del Señor.
              - 'opinion': Modelos mentales y directivas destiladas por reflexión.
  2. RECALL:  Recuperación semántica híbrida (BM25 FTS5 + filtros temporales y de red).
  3. REFLECT: Proceso de síntesis donde un modelo analiza experiencias y destila
              opiniones y modelos mentales para evitar repetir errores y aprender continuamente.
"""

from __future__ import annotations

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
MEMORY_DIR = WORKSPACE_DIR / "memory"
DB_PATH = MEMORY_DIR / "alberth_hindsight.db"

VALID_TYPES = ("world", "experience", "observation", "opinion")


def _get_connection() -> sqlite3.Connection:
    """Crea la base de datos de Hindsight con FTS5 para búsqueda ultrarrápida."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hindsight_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                context TEXT DEFAULT '',
                outcome TEXT DEFAULT '',
                reflected INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS hindsight_fts USING fts5(
                memory_id UNINDEXED,
                content,
                context,
                memory_type
            );
        """)
    return conn


def retain(content: str, memory_type: str = "world", context: str = "", outcome: str = "") -> int:
    """
    Guarda una unidad de memoria en la red adecuada.
    memory_type debe ser: 'world', 'experience', 'observation' u 'opinion'.
    """
    m_type = memory_type.lower()
    if m_type not in VALID_TYPES:
        m_type = "world"

    now = datetime.now().isoformat()
    conn = _get_connection()
    try:
        with conn:
            cur = conn.execute("""
                INSERT INTO hindsight_memories (memory_type, content, context, outcome, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (m_type, content.strip(), context.strip(), outcome.strip(), now))
            mem_id = cur.lastrowid
            conn.execute("""
                INSERT INTO hindsight_fts (memory_id, content, context, memory_type)
                VALUES (?, ?, ?, ?)
            """, (mem_id, content.strip(), context.strip(), m_type))
            return mem_id
    finally:
        conn.close()


def recall(query: str, memory_type: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Recupera recuerdos relevantes mediante búsqueda en FTS5 y filtrado por red.
    """
    conn = _get_connection()
    try:
        # Sanitizar query para FTS5
        clean_q = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_q:
            clean_q = query.strip()

        terms = [t for t in clean_q.split() if len(t) > 2]
        fts_query = " OR ".join(terms) if terms else clean_q

        if memory_type and memory_type in VALID_TYPES:
            sql = """
                SELECT m.id, m.memory_type, m.content, m.context, m.outcome, m.created_at
                FROM hindsight_memories m
                JOIN hindsight_fts f ON m.id = f.memory_id
                WHERE hindsight_fts MATCH ? AND m.memory_type = ?
                ORDER BY rank
                LIMIT ?
            """
            cur = conn.execute(sql, (fts_query, memory_type, limit))
        else:
            sql = """
                SELECT m.id, m.memory_type, m.content, m.context, m.outcome, m.created_at
                FROM hindsight_memories m
                JOIN hindsight_fts f ON m.id = f.memory_id
                WHERE hindsight_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            cur = conn.execute(sql, (fts_query, limit))

        results = []
        for row in cur.fetchall():
            results.append({
                "id": row["id"],
                "type": row["memory_type"],
                "content": row["content"],
                "context": row["context"],
                "outcome": row["outcome"],
                "created_at": row["created_at"]
            })
            # Actualizar conteo de acceso
            conn.execute("UPDATE hindsight_memories SET access_count = access_count + 1 WHERE id = ?", (row["id"],))
        conn.commit()
        return results
    except Exception:
        # Fallback si FTS5 no encuentra coincidencia sintáctica exacta
        cur = conn.execute("SELECT id, memory_type, content, context, outcome, created_at FROM hindsight_memories ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def reflect(topic: str = "") -> Dict[str, Any]:
    """
    Ciclo REFLECT: Analiza experiencias y observaciones no consolidadas,
    sintetiza modelos mentales ('opinion') y directivas de comportamiento.
    """
    conn = _get_connection()
    try:
        # Extraer experiencias no reflejadas
        cur = conn.execute("""
            SELECT id, memory_type, content, context, outcome 
            FROM hindsight_memories 
            WHERE reflected = 0 AND memory_type IN ('experience', 'observation')
            ORDER BY id DESC LIMIT 10
        """)
        rows = cur.fetchall()
        if not rows:
            return {"status": "skipped", "message": "No hay nuevas experiencias pendientes de reflexión."}

        exp_ids = [r["id"] for r in rows]
        exp_text = "\n".join([f"- [{r['memory_type']}] {r['content']} (Resultado: {r['outcome']})" for r in rows])

        prompt = (
            f"Tema de Reflexión: {topic or 'Evolución general de conducta'}\n\n"
            f"Experiencias recientes acumuladas por Alberth:\n{exp_text}\n\n"
            "Eres el Subconsciente Analítico de Alberth (Hindsight Engine). Tu labor es destilar 1 a 3 LECCIONES APRENDIDAS "
            "o MODELOS MENTALES sobre las preferencias del Señor y mejores prácticas para no repetir errores.\n"
            "Devuelve un resumen conciso en español de las lecciones aprendidas en formato de directiva."
        )

        try:
            import alberth_foundation_models as models
            synthesis, model_used = models.query_deepseek_reasoning(prompt=prompt, max_tokens=300)
        except Exception as e:
            synthesis = f"Consolidación heurística: {exp_text[:200]}"
            model_used = "heuristic_fallback"

        # Guardar la síntesis como un recuerdo de tipo 'opinion'
        op_id = retain(
            content=f"Modelo Mental Destilado: {synthesis.strip()}",
            memory_type="opinion",
            context=f"Reflexión sobre {len(exp_ids)} eventos ({model_used})"
        )

        # Marcar experiencias como reflejadas
        with conn:
            conn.execute(f"UPDATE hindsight_memories SET reflected = 1 WHERE id IN ({','.join('?' for _ in exp_ids)})", exp_ids)

        return {
            "status": "reflected",
            "new_opinion_id": op_id,
            "events_processed": len(exp_ids),
            "model_used": model_used,
            "synthesized_mental_model": synthesis.strip()
        }
    finally:
        conn.close()


def get_stats() -> Dict[str, Any]:
    """Retorna estadísticas del banco de memorias Hindsight."""
    conn = _get_connection()
    try:
        cur = conn.execute("SELECT memory_type, COUNT(*) as cnt FROM hindsight_memories GROUP BY memory_type")
        counts = {r["memory_type"]: r["cnt"] for r in cur.fetchall()}
        cur_total = conn.execute("SELECT COUNT(*) FROM hindsight_memories")
        total = cur_total.fetchone()[0]
        return {"total_memories": total, "by_type": counts}
    finally:
        conn.close()


if __name__ == "__main__":
    print("🧠 Probando Alberth Hindsight Engine (Retain / Recall / Reflect)...")
    
    # 1. Retain
    r1 = retain("El Señor prefiere respuestas ejecutivas sin introducciones largas.", "observation")
    r2 = retain("Auditoría de seguridad en servidor local falló al no verificar puerto 8765 primero.", "experience", outcome="fallo de timeout superado")
    r3 = retain("El proyecto Drivo es la plataforma de movilidad y alquiler.", "world")
    print(f"✅ Recuerdos guardados: IDs [{r1}, {r2}, {r3}]")

    # 2. Recall
    recalled = recall("seguridad puerto")
    print(f"\n🔍 Recall para 'seguridad puerto': {len(recalled)} coincidencia(s)")
    for m in recalled:
        print(f"   [{m['type']}] {m['content']}")

    # 3. Reflect
    refl = reflect(topic="Optimización de Auditorías y Trato al Señor")
    print("\n💡 Ciclo Reflect ejecutado:")
    print(json.dumps(refl, ensure_ascii=False, indent=2))

    # 4. Stats
    print("\n📊 Estadísticas de Memoria Hindsight:")
    print(get_stats())
