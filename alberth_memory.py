#!/usr/bin/env python3
# =============================================================================
# ALBERTH MEMORY ENGINE — Sistema de Memoria Persistente con SQLite
# 
# Alberth recuerda conversaciones anteriores entre sesiones.
# Cada intercambio se guarda, resume y recupera automáticamente.
#
# Modos de uso:
#   python3 alberth_memory.py --save "query" "response"  → guarda un intercambio
#   python3 alberth_memory.py --context "query actual"   → recupera contexto relevante
#   python3 alberth_memory.py --summary                  → resumen de memoria activa
#   python3 alberth_memory.py --stats                    → estadísticas de uso
#   python3 alberth_memory.py --clear-old 30             → elimina entradas > 30 días
#
# La memoria se guarda en: ~/.openclaw/alberth_memory.db
# =============================================================================

import os
import sys
import json
import sqlite3
import hashlib
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# ── Configuración ─────────────────────────────────────────────────────────────
DB_PATH         = os.path.expanduser("~/.openclaw/alberth_memory.db")
CONFIG_PATH     = os.path.expanduser("~/.openclaw/openclaw.json")
WORKSPACE_DIR   = os.path.expanduser("~/.openclaw/workspace")

# Cuántas entradas de contexto recuperar para el prompt (balance memoria/tokens)
MAX_CONTEXT_ENTRIES = 5
# Cuántos caracteres de respuesta guardar por entrada (para no saturar la DB)
MAX_RESPONSE_CHARS  = 800
# Días de retención por defecto
DEFAULT_RETENTION_DAYS = 60


def log(msg: str):
    print(f"[Memory] {msg}", file=sys.stderr, flush=True)


def get_db() -> sqlite3.Connection:
    """Abre (o crea) la base de datos de memoria de Alberth."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


# ── Gestión de Modo de Contexto (Personal / Laboral) ─────────────────────────
MODE_FILE = os.path.join(WORKSPACE_DIR, ".context_mode")
LOGS_DIR  = os.path.join(WORKSPACE_DIR, "logs")
AUDIT_LOG_FILE = os.path.join(LOGS_DIR, "audit_logs.jsonl")


def get_current_mode() -> str:
    """Retorna el modo de contexto activo ('laboral' o 'personal')."""
    if os.path.exists(MODE_FILE):
        try:
            with open(MODE_FILE, "r") as f:
                mode = f.read().strip().lower()
                if mode in ["personal", "laboral"]:
                    return mode
        except Exception:
            pass
    return "laboral"


def set_current_mode(mode: str) -> str:
    """Establece el modo de contexto activo ('laboral' o 'personal')."""
    mode = mode.lower().strip()
    if mode not in ["personal", "laboral"]:
        mode = "laboral"
    try:
        os.makedirs(os.path.dirname(MODE_FILE), exist_ok=True)
        with open(MODE_FILE, "w") as f:
            f.write(mode)
        log(f"🔄 Modo de contexto cambiado a: {mode.upper()}")
    except Exception as e:
        log(f"Error al cambiar modo: {e}")
    return mode


def audit_log(agente: str, query: str, modelo: str, latencia_ms: int = 0, status: str = "ok"):
    """Registra eventos de auditoría y trazabilidad en logs/audit_logs.jsonl."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        record = {
            "timestamp": datetime.now().isoformat(),
            "modo": get_current_mode(),
            "agente": agente,
            "query": query[:300],
            "modelo": modelo,
            "latencia_ms": latencia_ms,
            "status": status
        }
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"Error registrando auditoría: {e}")


def _init_schema(conn: sqlite3.Connection):
    """Crea las tablas si no existen."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            query       TEXT    NOT NULL,
            response    TEXT    NOT NULL,
            query_hash  TEXT,
            tags        TEXT    DEFAULT '',
            importance  INTEGER DEFAULT 1,
            mode        TEXT    DEFAULT 'laboral'
        );

        CREATE TABLE IF NOT EXISTS user_facts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL,
            fact        TEXT    NOT NULL UNIQUE,
            first_seen  TEXT    DEFAULT (datetime('now', 'localtime')),
            last_seen   TEXT    DEFAULT (datetime('now', 'localtime')),
            frequency   INTEGER DEFAULT 1,
            mode        TEXT    DEFAULT 'laboral'
        );

        CREATE TABLE IF NOT EXISTS daily_summaries (
            date        TEXT    PRIMARY KEY,
            summary     TEXT    NOT NULL,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger_at  TEXT    NOT NULL,
            message     TEXT    NOT NULL,
            status      TEXT    DEFAULT 'pending',
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversations(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_conv_hash      ON conversations(query_hash);
        CREATE INDEX IF NOT EXISTS idx_rem_trigger    ON reminders(trigger_at) WHERE status = 'pending';
    """)
    conn.commit()


def add_reminder(trigger_at: str, message: str):
    """Guarda un nuevo recordatorio en la base de datos."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO reminders (trigger_at, message) VALUES (?, ?)",
            (trigger_at, message)
        )
        conn.commit()
        log(f"Recordatorio guardado para {trigger_at}: {message}")
    except Exception as e:
        log(f"Error al guardar recordatorio: {e}")
    finally:
        conn.close()


def get_pending_reminders() -> list:
    """Retorna todos los recordatorios pendientes que deben activarse."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT id, trigger_at, message 
            FROM reminders 
            WHERE status = 'pending' AND trigger_at <= datetime('now', 'localtime')
            ORDER BY trigger_at ASC
        """).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log(f"Error al buscar recordatorios pendientes: {e}")
        return []
    finally:
        conn.close()


def mark_reminder_done(reminder_id: int):
    """Marca un recordatorio como completado."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE reminders SET status = 'completed' WHERE id = ?",
            (reminder_id,)
        )
        conn.commit()
        log(f"Recordatorio {reminder_id} marcado como completado.")
    except Exception as e:
        log(f"Error al marcar recordatorio como completado: {e}")
    finally:
        conn.close()



def _hash_query(query: str) -> str:
    return hashlib.md5(query.lower().strip()[:200].encode()).hexdigest()


# ── Operaciones principales ───────────────────────────────────────────────────

def save_conversation(query: str, response: str, tags: str = "", importance: int = 1):
    """
    Guarda un intercambio query/response en la base de datos.
    Trunca la respuesta si es muy larga para no saturar la DB.
    """
    conn = get_db()
    try:
        # Truncar respuesta para mantener la DB liviana
        resp_trunc = response[:MAX_RESPONSE_CHARS]
        if len(response) > MAX_RESPONSE_CHARS:
            resp_trunc += "..."

        query_hash = _hash_query(query)

        conn.execute(
            "INSERT INTO conversations (query, response, query_hash, tags, importance) VALUES (?, ?, ?, ?, ?)",
            (query.strip(), resp_trunc, query_hash, tags, importance)
        )
        conn.commit()
        log(f"Conversación guardada (ID: {conn.execute('SELECT last_insert_rowid()').fetchone()[0]})")
        
        # Extraer y guardar hechos del usuario si hay patrones reconocibles
        _extract_user_facts(conn, query, response)
    except Exception as e:
        log(f"Error al guardar conversación: {e}")
    finally:
        conn.close()


def get_context(current_query: str, max_entries: int = MAX_CONTEXT_ENTRIES) -> str:
    """
    Recupera contexto relevante de la memoria para la query actual.
    Retorna un bloque de texto listo para insertar en el prompt del agente.
    """
    conn = get_db()
    try:
        context_parts = []

        # 1. Hechos persistentes del usuario (siempre relevantes)
        facts = conn.execute(
            "SELECT category, fact FROM user_facts ORDER BY frequency DESC LIMIT 10"
        ).fetchall()
        if facts:
            facts_text = "\n".join(f"  [{r['category']}] {r['fact']}" for r in facts)
            context_parts.append(f"HECHOS CONOCIDOS SOBRE EL SEÑOR:\n{facts_text}")

        # 2. Conversaciones recientes (últimas 48h, máx max_entries)
        recent = conn.execute("""
            SELECT timestamp, query, response 
            FROM conversations 
            WHERE timestamp > datetime('now', '-2 days', 'localtime')
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (max_entries,)).fetchall()

        if recent:
            recent_text = ""
            for r in reversed(recent):  # Orden cronológico
                ts = r["timestamp"][:16]  # Solo fecha y hora
                recent_text += f"\n  [{ts}] Señor: {r['query'][:100]}\n  Alberth: {r['response'][:150]}\n"
            context_parts.append(f"CONVERSACIONES RECIENTES (últimas 48h):{recent_text}")

        # 3. Resumen del día anterior si existe
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        summary_row = conn.execute(
            "SELECT summary FROM daily_summaries WHERE date = ?", (yesterday,)
        ).fetchone()
        if summary_row:
            context_parts.append(f"RESUMEN DE AYER ({yesterday}):\n  {summary_row['summary']}")

        if not context_parts:
            return ""

        full_context = (
            "\n[MEMORIA PERSISTENTE DE ALBERTH — Contexto de sesiones anteriores]\n"
            + "\n\n".join(context_parts)
            + "\n[FIN DE CONTEXTO DE MEMORIA]\n"
        )
        return full_context

    except Exception as e:
        log(f"Error al recuperar contexto: {e}")
        return ""
    finally:
        conn.close()


def _extract_user_facts(conn: sqlite3.Connection, query: str, response: str):
    """
    Detecta y guarda hechos sobre el usuario a partir de patrones en la query.
    Ejemplos: preferencias musicales, nombre, proyectos mencionados.
    """
    patterns = [
        # (categoría, palabras_clave_trigger, extractor)
        ("musica", ["echo music", "yt music", "youtube music"], 
         lambda q: "Usa Echo Music, YT Music Premium y YouTube Pro como apps de música"),
        ("identidad", ["arquitecto", "diseñador", "ingeniero"],
         lambda q: f"El Señor trabaja como arquitecto/diseñador"),
        ("sistema_operativo", ["mac", "macos", "macbook"],
         lambda q: "Usa macOS como sistema operativo principal"),
        ("asistente", ["alberth", "asistente"],
         lambda q: "El asistente se llama Alberth"),
    ]

    query_lower = query.lower()
    for category, keywords, extractor in patterns:
        if any(kw in query_lower for kw in keywords):
            fact_text = extractor(query_lower)
            try:
                # Insertar o actualizar frecuencia si ya existe
                existing = conn.execute(
                    "SELECT id, frequency FROM user_facts WHERE fact = ?", (fact_text,)
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE user_facts SET frequency = ?, last_seen = datetime('now', 'localtime') WHERE id = ?",
                        (existing["frequency"] + 1, existing["id"])
                    )
                else:
                    conn.execute(
                        "INSERT INTO user_facts (category, fact) VALUES (?, ?)",
                        (category, fact_text)
                    )
                conn.commit()
            except Exception:
                pass


def save_daily_summary(summary: str, date: str | None = None):
    """Guarda o actualiza el resumen del día."""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO daily_summaries (date, summary) VALUES (?, ?)",
            (target_date, summary)
        )
        conn.commit()
        log(f"Resumen diario guardado para {target_date}")
    finally:
        conn.close()


def get_stats() -> dict:
    """Retorna estadísticas de la base de datos de memoria."""
    conn = get_db()
    try:
        total_convs  = conn.execute("SELECT COUNT(*) as n FROM conversations").fetchone()["n"]
        total_facts  = conn.execute("SELECT COUNT(*) as n FROM user_facts").fetchone()["n"]
        oldest       = conn.execute("SELECT MIN(timestamp) as d FROM conversations").fetchone()["d"]
        newest       = conn.execute("SELECT MAX(timestamp) as d FROM conversations").fetchone()["d"]
        today_count  = conn.execute(
            "SELECT COUNT(*) as n FROM conversations WHERE timestamp > datetime('now', 'start of day', 'localtime')"
        ).fetchone()["n"]
        return {
            "total_conversaciones": total_convs,
            "total_hechos": total_facts,
            "primera_conversacion": oldest,
            "ultima_conversacion": newest,
            "conversaciones_hoy": today_count,
            "db_path": DB_PATH,
            "db_size_kb": os.path.getsize(DB_PATH) // 1024 if os.path.exists(DB_PATH) else 0
        }
    finally:
        conn.close()


def clear_old_entries(days: int = DEFAULT_RETENTION_DAYS):
    """Elimina conversaciones más antiguas que `days` días."""
    conn = get_db()
    try:
        cursor = conn.execute(
            f"DELETE FROM conversations WHERE timestamp < datetime('now', '-{days} days', 'localtime')"
        )
        deleted = cursor.rowcount
        conn.commit()
        log(f"Limpieza: {deleted} conversaciones eliminadas (>{days} días)")
        return deleted
    finally:
        conn.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Alberth Memory Engine — Sistema de memoria persistente"
    )
    parser.add_argument("--save",    nargs=2, metavar=("QUERY", "RESPONSE"),
                        help="Guarda un intercambio en la memoria")
    parser.add_argument("--context", metavar="QUERY",
                        help="Recupera contexto relevante para una query")
    parser.add_argument("--summary", action="store_true",
                        help="Muestra un resumen de la memoria activa")
    parser.add_argument("--stats",   action="store_true",
                        help="Muestra estadísticas de la base de datos")
    parser.add_argument("--clear-old", type=int, metavar="DIAS",
                        help="Elimina entradas más viejas que N días")
    parser.add_argument("--save-daily", metavar="TEXTO",
                        help="Guarda el resumen del día")
    parser.add_argument("--add-reminder", nargs=2, metavar=("TRIGGER_AT", "MESSAGE"),
                        help="Añade un recordatorio (TRIGGER_AT formato YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--pending-reminders", action="store_true",
                        help="Lista recordatorios pendientes listos para disparar")
    parser.add_argument("--mark-reminder-done", type=int, metavar="ID",
                        help="Marca un recordatorio como completado por su ID")
    parser.add_argument("--get-mode", action="store_true",
                        help="Muestra el modo de contexto activo (laboral/personal)")
    parser.add_argument("--set-mode", choices=["personal", "laboral"],
                        help="Cambia el modo de contexto activo (personal/laboral)")
    parser.add_argument("--audit", nargs=4, metavar=("AGENTE", "QUERY", "MODELO", "LATENCIA_MS"),
                        help="Registra una entrada de auditoría")
    parser.add_argument("--tags",    default="",
                        help="Tags para categorizar la entrada (con --save)")
    parser.add_argument("--importance", type=int, default=1,
                        help="Importancia 1-5 de la conversación (con --save)")
    args = parser.parse_args()

    if args.get_mode:
        print(get_current_mode())

    elif args.set_mode:
        m = set_current_mode(args.set_mode)
        print(f"Modo cambiado a {m}")

    elif args.audit:
        agente, query, modelo, latencia = args.audit
        audit_log(agente, query, modelo, int(latencia))
        print("OK")

    elif args.save:
        query, response = args.save
        save_conversation(query, response, args.tags, args.importance)
        print("OK")

    elif args.context:
        ctx = get_context(args.context)
        print(ctx if ctx else "")

    elif args.summary:
        stats = get_stats()
        print(f"\n📊 MEMORIA DE ALBERTH")
        print(f"  Modo Activo            : {get_current_mode().upper()}")
        print(f"  Conversaciones totales : {stats['total_conversaciones']}")
        print(f"  Hechos del usuario     : {stats['total_hechos']}")
        print(f"  Conversaciones hoy     : {stats['conversaciones_hoy']}")
        print(f"  Primera conversación   : {stats['primera_conversacion'] or 'N/A'}")
        print(f"  Última conversación    : {stats['ultima_conversacion'] or 'N/A'}")
        print(f"  Tamaño de base de datos: {stats['db_size_kb']} KB")
        print(f"  Ruta                   : {stats['db_path']}\n")

    elif args.stats:
        res = get_stats()
        res["modo_activo"] = get_current_mode()
        print(json.dumps(res, ensure_ascii=False, indent=2))

    elif args.clear_old is not None:
        deleted = clear_old_entries(args.clear_old)
        print(f"Eliminadas {deleted} conversaciones.")

    elif args.save_daily:
        save_daily_summary(args.save_daily)
        print("OK")

    elif args.add_reminder:
        trigger_at, message = args.add_reminder
        add_reminder(trigger_at, message)
        print("OK")

    elif args.pending_reminders:
        reminders = get_pending_reminders()
        print(json.dumps(reminders, ensure_ascii=False))

    elif args.mark_reminder_done is not None:
        mark_reminder_done(args.mark_reminder_done)
        print("OK")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

