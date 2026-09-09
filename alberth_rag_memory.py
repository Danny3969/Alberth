#!/usr/bin/env python3
# =============================================================================
# ALBERTH RAG MEMORY — Motor de Búsqueda Semántica Documental Local (BM25 RAG)
#
# 100% Gratuito, Privado y Cero Costo de Tokens:
#   - Indexa PDFs, Markdown, Textos y Código en base de datos SQLite FTS5.
#   - Algoritmo Okapi BM25 de alta precisión para encontrar respuestas exactas.
#   - Devuelve fragmentos relevantes y citas de archivo en < 5 milisegundos.
#
# Uso:
#   python3 alberth_rag_memory.py --index <archivo_o_directorio>
#   python3 alberth_rag_memory.py "<consulta>"
#   python3 alberth_rag_memory.py --status
# =============================================================================

from __future__ import annotations
import sys
import os
import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Any

WORKSPACE_DIR = os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WORKSPACE_DIR, "memory", "rag_documents.db")


def get_db() -> sqlite3.Connection:
    """Inicializa la base de datos FTS5 si no existe."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indexed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE,
            filename TEXT,
            mtime REAL,
            total_chunks INTEGER
        );
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks USING fts5(
            filepath,
            filename,
            chunk_index,
            content,
            tokenize = 'porter unicode61'
        );
    """)
    conn.commit()
    return conn


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """Divide un texto en bloques superpuestos para mantener coherencia semántica."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - overlap)
    return chunks


def extract_file_text(filepath: str) -> str:
    """Extrae texto de archivos PDF, TXT, MD o código fuente."""
    p = Path(filepath)
    if not p.exists():
        return ""

    ext = p.suffix.lower()
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(p))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        except Exception as e:
            print(f"[RAG Warn] Error al leer PDF {p.name}: {e}", file=sys.stderr)
            return ""
    else:
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[RAG Warn] Error al leer texto de {p.name}: {e}", file=sys.stderr)
            return ""


def index_file(filepath: str, conn: sqlite3.Connection = None) -> int:
    """Indexa un archivo en la base de datos RAG."""
    should_close = False
    if conn is None:
        conn = get_db()
        should_close = True

    p = Path(filepath).resolve()
    if not p.exists() or p.name.startswith("."):
        return 0

    mtime = p.stat().st_mtime
    # Verificar si ya está indexado con la misma fecha de modificación
    row = conn.execute("SELECT mtime FROM indexed_files WHERE filepath = ?", (str(p),)).fetchone()
    if row and row["mtime"] == mtime:
        return 0  # Ya está al día

    text = extract_file_text(str(p))
    if not text.strip():
        return 0

    chunks = chunk_text(text)

    # Eliminar chunks antiguos si ya existía
    conn.execute("DELETE FROM document_chunks WHERE filepath = ?", (str(p),))
    conn.execute("DELETE FROM indexed_files WHERE filepath = ?", (str(p),))

    # Insertar nuevos chunks en FTS5
    for idx, c in enumerate(chunks):
        conn.execute(
            "INSERT INTO document_chunks (filepath, filename, chunk_index, content) VALUES (?, ?, ?, ?)",
            (str(p), p.name, idx, c)
        )

    conn.execute(
        "INSERT OR REPLACE INTO indexed_files (filepath, filename, mtime, total_chunks) VALUES (?, ?, ?, ?)",
        (str(p), p.name, mtime, len(chunks))
    )
    conn.commit()

    if should_close:
        conn.close()
    return len(chunks)


def index_directory(dirpath: str) -> Dict[str, Any]:
    """Indexa recursivamente una carpeta de documentos."""
    conn = get_db()
    total_files = 0
    total_chunks = 0
    valid_exts = {".pdf", ".txt", ".md", ".json", ".py", ".sh", ".yaml", ".yml"}

    for root, _, files in os.walk(dirpath):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in valid_exts and not p.name.startswith("."):
                num = index_file(str(p), conn)
                if num > 0:
                    total_files += 1
                    total_chunks += num

    conn.close()
    return {
        "exito": True,
        "archivos_indexados": total_files,
        "fragmentos_totales": total_chunks
    }


def query_rag(query: str, limit: int = 3) -> Dict[str, Any]:
    """Busca fragmentos relevantes en los documentos usando Okapi BM25 nativo."""
    conn = get_db()

    # Limpiar query para FTS5
    clean_q = re.sub(r'[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]', ' ', query)
    tokens = [t for t in clean_q.split() if len(t) > 2]
    if not tokens:
        conn.close()
        return {"exito": False, "resultado": "Consulta demasiado corta para buscar en documentos.", "citas": []}

    match_expr = " OR ".join(f'"{t}"*' for t in tokens)

    try:
        sql = """
            SELECT filepath, filename, chunk_index, content, bm25(document_chunks) as rank
            FROM document_chunks
            WHERE document_chunks MATCH ?
            ORDER BY rank
            LIMIT ?;
        """
        rows = conn.execute(sql, (match_expr, limit)).fetchall()
        results = []
        for r in rows:
            results.append({
                "archivo": r["filename"],
                "ruta": r["filepath"],
                "fragmento": r["content"],
                "relevancia": round(float(r["rank"]), 3)
            })
        conn.close()

        if not results:
            return {
                "exito": False,
                "query": query,
                "resultado": f"No se encontró información relevante sobre '{query}' en los documentos indexados.",
                "citas": []
            }

        lines = [f"Información relevante encontrada en los documentos del usuario:"]
        for idx, item in enumerate(results, 1):
            lines.append(f"{idx}. [Fuente: {item['archivo']}]\n   \"{item['fragmento']}\"")

        return {
            "exito": True,
            "query": query,
            "resultado": "\n\n".join(lines),
            "citas": results
        }
    except Exception as e:
        conn.close()
        return {"exito": False, "error": f"Error en búsqueda RAG: {e}", "citas": []}


def get_status() -> Dict[str, Any]:
    """Devuelve estadísticas de la base de datos RAG."""
    conn = get_db()
    files_count = conn.execute("SELECT COUNT(*) as c FROM indexed_files").fetchone()["c"]
    chunks_count = conn.execute("SELECT COUNT(*) as c FROM document_chunks").fetchone()["c"]
    conn.close()
    return {
        "base_de_datos": DB_PATH,
        "documentos_indexados": files_count,
        "fragmentos_totales": chunks_count
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Uso: --index <ruta> | --status | '<consulta>'"}))
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "--status":
        print(json.dumps(get_status(), ensure_ascii=False, indent=2))
    elif arg == "--index" and len(sys.argv) > 2:
        target = sys.argv[2]
        if os.path.isdir(target):
            res = index_directory(target)
        else:
            num = index_file(target)
            res = {"exito": True, "fragmentos": num, "archivo": target}
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        q = " ".join(sys.argv[1:])
        res = query_rag(q)
        print(json.dumps(res, ensure_ascii=False, indent=2))
