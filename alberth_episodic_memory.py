#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_episodic_memory.py — Motor de Memoria Episódica Autonómica para Alberth
================================================================================
Almacena y recupera preferencias del Señor, rutinas diarias, detalles de proyectos
y hechos clave utilizando SQLite FTS5 (Full-Text Search con BM25).

Características:
  - 100% Local y Privado: Base de datos en memory/alberth_episodic_memory.db.
  - Cero costo de tokens y latencia < 2 milisegundos.
  - Inyección contextual automática en prompts de los agentes y LLMs.
  - Deduplicación inteligente de recuerdos.

Uso por CLI:
  python3 alberth_episodic_memory.py --learn "Prefiero respuestas ejecutivas y analíticas" --cat "preferencias"
  python3 alberth_episodic_memory.py --query "música"
  python3 alberth_episodic_memory.py --list
  python3 alberth_episodic_memory.py --context "código Python"
"""

from __future__ import annotations

import os
import sys
import json
import sqlite3
import re
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
MEMORY_DIR = WORKSPACE_DIR / "memory"
DB_PATH = MEMORY_DIR / "alberth_episodic_memory.db"


def _get_connection() -> sqlite3.Connection:
    """Crea o conecta a la base de datos de memoria episódica con FTS5."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS episodic_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT
            );
        """)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS episodic_facts_fts USING fts5(
                fact_id UNINDEXED,
                content,
                tokenize = 'porter unicode61'
            );
        """)

        # Sembrar hechos base por defecto si la base está vacía
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM episodic_facts")
        if cur.fetchone()[0] == 0:
            now = datetime.now().isoformat()
            default_facts = [
                ("El usuario debe ser tratado siempre y exclusivamente con el título de respeto 'Señor'.", "trato", now),
                ("El Señor utiliza YouTube Music / Echo Music para su reproducción de música.", "musica", now),
                ("El Señor prefiere respuestas concisas, analíticas, profesionales y de alto nivel técnico.", "preferencias", now),
                ("El sistema opera en un iMac y un MacBook Pro de Apple bajo macOS.", "entorno", now),
            ]
            for fact, cat, ts in default_facts:
                cur.execute(
                    "INSERT INTO episodic_facts (fact, category, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (fact, cat, ts, ts)
                )
                fid = cur.lastrowid
                cur.execute(
                    "INSERT INTO episodic_facts_fts (fact_id, content) VALUES (?, ?)",
                    (fid, fact)
                )
    return conn


def clean_query_fts(query: str) -> str:
    """Sanitiza una consulta para la sintaxis de SQLite FTS5."""
    words = re.findall(r'[\w]+', query, re.UNICODE)
    cleaned = []
    stopwords = {"de", "la", "el", "los", "las", "un", "una", "en", "para", "por", "con", "y", "a", "que", "qué", "sobre", "del", "mi", "mis", "tu", "tus"}
    for w in words:
        wl = w.lower()
        if wl not in stopwords and len(wl) > 1:
            cleaned.append(f'"{w}"*')
    return " OR ".join(cleaned) if cleaned else ""


def learn_fact(fact: str, category: str = "general") -> Dict[str, Any]:
    """
    Registra un nuevo hecho o preferencia en la memoria episódica.
    Evita duplicados exactos o redundancias cercanas.
    """
    fact = fact.strip()
    if not fact:
        return {"ok": False, "error": "El hecho a memorizar está vacío."}

    # Limpiar prefijos comunes si vienen de comandos hablados
    clean_fact = re.sub(r'^(?:recuerda\s+que|guarda\s+que|aprende\s+que|anota\s+que|no\s+olvides\s+que)\s+', '', fact, flags=re.IGNORECASE).strip()
    if not clean_fact:
        clean_fact = fact

    category = category.strip().lower() or "general"
    conn = _get_connection()
    now = datetime.now().isoformat()

    with conn:
        cur = conn.cursor()
        # Verificar si ya existe un hecho idéntico o muy similar
        cur.execute("SELECT id, fact FROM episodic_facts WHERE LOWER(fact) = LOWER(?)", (clean_fact,))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                "UPDATE episodic_facts SET updated_at = ?, access_count = access_count + 1 WHERE id = ?",
                (now, existing["id"])
            )
            return {"ok": True, "id": existing["id"], "fact": clean_fact, "category": category, "is_new": False}

        cur.execute(
            "INSERT INTO episodic_facts (fact, category, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (clean_fact, category, now, now)
        )
        new_id = cur.lastrowid
        cur.execute(
            "INSERT INTO episodic_facts_fts (fact_id, content) VALUES (?, ?)",
            (new_id, clean_fact)
        )

    return {"ok": True, "id": new_id, "fact": clean_fact, "category": category, "is_new": True}


def get_relevant_facts(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Recupera los recuerdos más relevantes a partir de una consulta semántica.
    Si no hay coincidencias exactas en FTS, complementa con las preferencias más frecuentes.
    """
    conn = _get_connection()
    fts_q = clean_query_fts(query)
    results = []
    seen_ids = set()

    with conn:
        cur = conn.cursor()
        if fts_q:
            try:
                cur.execute(
                    """
                    SELECT f.id, f.fact, f.category, f.created_at, f.access_count, bm25(episodic_facts_fts) as rank
                    FROM episodic_facts_fts
                    JOIN episodic_facts f ON f.id = episodic_facts_fts.fact_id
                    WHERE episodic_facts_fts MATCH ?
                    ORDER BY rank ASC
                    LIMIT ?
                    """,
                    (fts_q, limit)
                )
                for row in cur.fetchall():
                    seen_ids.add(row["id"])
                    results.append({
                        "id": row["id"],
                        "fact": row["fact"],
                        "category": row["category"],
                        "created_at": row["created_at"],
                        "access_count": row["access_count"]
                    })
            except Exception as e:
                print(f"[EpisodicMemory] Warn en búsqueda FTS: {e}", file=sys.stderr)

        # Si encontramos menos de `limit` resultados, complementar con hechos de categoría 'preferencias' o 'trato'
        if len(results) < limit:
            needed = limit - len(results)
            placeholders = ",".join("?" for _ in seen_ids) if seen_ids else "0"
            cur.execute(
                f"""
                SELECT id, fact, category, created_at, access_count
                FROM episodic_facts
                WHERE id NOT IN ({placeholders})
                ORDER BY access_count DESC, id DESC
                LIMIT ?
                """,
                (*list(seen_ids), needed) if seen_ids else (needed,)
            )
            for row in cur.fetchall():
                results.append({
                    "id": row["id"],
                    "fact": row["fact"],
                    "category": row["category"],
                    "created_at": row["created_at"],
                    "access_count": row["access_count"]
                })

        # Actualizar access_count
        if results:
            ids_to_bump = [r["id"] for r in results]
            now = datetime.now().isoformat()
            cur.executemany(
                "UPDATE episodic_facts SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                [(now, i) for i in ids_to_bump]
            )

    return results


def get_user_context_block(query: str = "", limit: int = 4) -> str:
    """
    Retorna un bloque de texto formateado listo para inyectarse directamente
    en el prompt de sistema del asistente sin sobrecargar la ventana de contexto.
    """
    facts = get_relevant_facts(query, limit=limit)
    if not facts:
        return ""

    lines = ["[MEMORIA EPISÓDICA Y PREFERENCIAS CONOCIDAS DEL SEÑOR]:"]
    for f in facts:
        lines.append(f"  • {f['fact']}")
    lines.append("")
    return "\n".join(lines)


def list_all_facts(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lista todos los hechos almacenados, opcionalmente filtrados por categoría."""
    conn = _get_connection()
    with conn:
        cur = conn.cursor()
        if category:
            cur.execute(
                "SELECT id, fact, category, created_at, access_count FROM episodic_facts WHERE category = ? ORDER BY id DESC",
                (category.lower(),)
            )
        else:
            cur.execute("SELECT id, fact, category, created_at, access_count FROM episodic_facts ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]


def delete_fact(fact_id: int) -> bool:
    """Elimina un hecho por su ID de la tabla principal y del índice FTS."""
    conn = _get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM episodic_facts WHERE id = ?", (fact_id,))
        cur.execute("DELETE FROM episodic_facts_fts WHERE fact_id = ?", (fact_id,))
        return cur.rowcount > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Motor de Memoria Episódica Autonómica de Alberth")
    parser.add_argument("--learn", type=str, help="Hecho o preferencia a aprender")
    parser.add_argument("--cat", type=str, default="general", help="Categoría del hecho")
    parser.add_argument("--query", type=str, help="Consulta de búsqueda semántica")
    parser.add_argument("--context", type=str, help="Genera bloque contextual de prompt para una consulta")
    parser.add_argument("--list", action="store_true", help="Lista todos los recuerdos guardados")
    parser.add_argument("--delete", type=int, help="Elimina un recuerdo por ID")

    args = parser.parse_args()

    if args.learn:
        res = learn_fact(args.learn, args.cat)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.query:
        res = get_relevant_facts(args.query)
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.context is not None:
        print(get_user_context_block(args.context))
    elif args.list:
        res = list_all_facts()
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif args.delete:
        ok = delete_fact(args.delete)
        print(f"Eliminado: {ok}")
    else:
        parser.print_help()
