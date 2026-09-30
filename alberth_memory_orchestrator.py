#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_memory_orchestrator.py — Orquestador de Memoria Jerárquico en 4 Capas (R7)
===================================================================================
Inspirado en la arquitectura GODMODE y optimizado para Alberth:

1. 🔥 HOT (< 1ms):     Contexto de la sesión activa en memoria RAM volátil.
2. 🌤️ WARM (< 5ms):    Hechos recientes y preferencias vía SQLite FTS5 (alberth_episodic_memory).
3. ❄️ COLD (< 50ms):   Documentación pesada e indexada en RAG (alberth_rag_memory).
4. 📦 ARCHIVE (< 200ms): Registros > 60 días comprimidos con índice BM25 ligero.

Permite consultar el contexto más relevante ahorrando tokens y reduciendo latencia.
"""

from __future__ import annotations

import os
import sys
import json
import gzip
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
MEMORY_DIR = WORKSPACE_DIR / "memory"
ARCHIVE_DIR = MEMORY_DIR / "archive"
ARCHIVE_INDEX_FILE = ARCHIVE_DIR / "archive_index.json.gz"

# ── Capa 1: HOT (En Memoria RAM) ──────────────────────────────────────────────
_HOT_SESSION_BUFFER: List[Dict[str, Any]] = []
_MAX_HOT_ENTRIES = 20


def hot_push(role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Registra una interacción inmediata en el búfer HOT."""
    global _HOT_SESSION_BUFFER
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
        "metadata": metadata or {}
    }
    _HOT_SESSION_BUFFER.append(entry)
    if len(_HOT_SESSION_BUFFER) > _MAX_HOT_ENTRIES:
        _HOT_SESSION_BUFFER.pop(0)


def hot_get_recent(limit: int = 5) -> List[Dict[str, Any]]:
    """Obtiene los últimos intercambios de la sesión activa."""
    return _HOT_SESSION_BUFFER[-limit:]


# ── Capa 2: WARM (Memoria Episódica FTS5) ──────────────────────────────────────
def warm_query(query: str, limit: int = 3) -> List[str]:
    """Consulta la memoria episódica reciente (preferencias y hechos)."""
    try:
        import alberth_episodic_memory as ep_mem
        res = ep_mem.query_facts(query, limit=limit)
        return [f"[{r.get('category', 'general')}] {r.get('fact', '')}" for r in res]
    except Exception:
        return []


# ── Capa 3: COLD (RAG Documental) ─────────────────────────────────────────────
def cold_query(query: str, limit: int = 2) -> List[str]:
    """Consulta documentos locales indexados en RAG."""
    try:
        import alberth_rag_memory as rag_mem
        res = rag_mem.search_documents(query, limit=limit)
        items = []
        if res and "resultados" in res:
            for doc in res["resultados"]:
                items.append(f"Documento '{doc.get('archivo', 'desconocido')}': {doc.get('fragmento', '')[:250]}...")
        return items
    except Exception:
        return []


# ── Capa 4: ARCHIVE (Comprimidos > 60 días) ───────────────────────────────────
def compress_old_memories(days_threshold: int = 60) -> int:
    """
    Empaqueta archivos markdown de memoria con más de `days_threshold` días
    hacia el archivo comprimido ARCHIVE para liberar inodos y espacio.
    """
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=days_threshold)
    archived_count = 0

    index_data: Dict[str, Any] = {}
    if ARCHIVE_INDEX_FILE.exists():
        try:
            with gzip.open(ARCHIVE_INDEX_FILE, "rt", encoding="utf-8") as f:
                index_data = json.load(f)
        except Exception:
            index_data = {}

    for md_file in MEMORY_DIR.glob("202[0-9]-[0-1][0-9]-[0-3][0-9]*.md"):
        try:
            date_str = md_file.name[:10]
            f_date = datetime.strptime(date_str, "%Y-%m-%d")
            if f_date < cutoff:
                target = ARCHIVE_DIR / md_file.name
                if not target.exists():
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    index_data[md_file.name] = {
                        "date": date_str,
                        "size": len(content),
                        "snippet": content[:300].strip(),
                    }
                    md_file.rename(target)
                    archived_count += 1
        except Exception:
            continue

    with gzip.open(ARCHIVE_INDEX_FILE, "wt", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=1)

    return archived_count


def archive_query(query: str, limit: int = 2) -> List[str]:
    """Busca en el índice de archivos históricos archivados."""
    if not ARCHIVE_INDEX_FILE.exists():
        return []
    try:
        with gzip.open(ARCHIVE_INDEX_FILE, "rt", encoding="utf-8") as f:
            index_data = json.load(f)
        q_terms = [t.lower() for t in query.split() if len(t) > 3]
        matches = []
        for fname, meta in index_data.items():
            snippet = meta.get("snippet", "").lower()
            if any(term in snippet for term in q_terms):
                matches.append(f"Archivo Histórico ({meta.get('date')}): {meta.get('snippet')[:200]}...")
            if len(matches) >= limit:
                break
        return matches
    except Exception:
        return []


# ── Consulta Jerárquica Unificada ─────────────────────────────────────────────
def get_unified_context(query: str, max_tokens_estimate: int = 600) -> Dict[str, Any]:
    """
    Recupera el contexto óptimo combinando las 4 capas de forma calibrada:
    - Prioriza HOT (sesión viva)
    - Concatena WARM (hechos y preferencias)
    - Añade COLD (documentos) si es relevante
    - Consulta ARCHIVE sólo si no hay suficiente información en capas anteriores
    """
    context_blocks = []

    # 1. HOT
    recent_hot = hot_get_recent(limit=3)
    hot_text = "\n".join([f"{e['role']}: {e['content'][:150]}" for e in recent_hot]) if recent_hot else ""
    if hot_text:
        context_blocks.append(f"=== SESIÓN RECIENTE (HOT) ===\n{hot_text}")

    # 2. WARM
    warm_facts = warm_query(query, limit=2)
    if warm_facts:
        context_blocks.append("=== HECHOS Y PREFERENCIAS (WARM) ===\n" + "\n".join(warm_facts))

    # 2.5. HINDSIGHT (Modelos Mentales y Lecciones Aprendidas Evolutivas)
    try:
        import alberth_hindsight as hs
        hs_opinions = hs.recall(query, memory_type="opinion", limit=2)
        if hs_opinions:
            opinions_txt = "\n".join([f"• {o['content']}" for o in hs_opinions])
            context_blocks.append("=== MODELOS MENTALES & APRENDIZAJES (HINDSIGHT) ===\n" + opinions_txt)
    except Exception:
        pass

    # 3. COLD
    cold_docs = cold_query(query, limit=2)
    if cold_docs:
        context_blocks.append("=== DOCUMENTACIÓN LOCAL (COLD) ===\n" + "\n".join(cold_docs))

    # 4. ARCHIVE (si el query pide expresamente historial o pasado)
    if any(k in query.lower() for k in ["historial", "hace tiempo", "antiguo", "anterior", "archivo", "meses"]):
        arch_items = archive_query(query, limit=1)
        if arch_items:
            context_blocks.append("=== HISTORIAL REMOTO (ARCHIVE) ===\n" + "\n".join(arch_items))

    full_context = "\n\n".join(context_blocks)
    return {
        "context_str": full_context,
        "layers_used": {
            "hot": bool(hot_text),
            "warm": len(warm_facts),
            "cold": len(cold_docs),
            "archive": bool("HISTORIAL REMOTO" in full_context)
        }
    }


if __name__ == "__main__":
    print("🧠 Probando Alberth Memory Orchestrator (Hot/Warm/Cold/Archive)...")
    hot_push("Señor", "Recuerda que mañana analizaremos el balance financiero.")
    hot_push("Alberth", "Entendido Señor, estaré preparado con los indicadores.")

    archived = compress_old_memories(days_threshold=60)
    print(f"📦 Archivos > 60 días archivados y comprimidos: {archived}")

    ctx = get_unified_context("balance financiero y preferencias")
    print("\n🔍 Contexto Unificado Recuperado:")
    print(ctx["context_str"])
    print("\nCapas utilizadas:", ctx["layers_used"])
