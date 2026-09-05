#!/usr/bin/env python3
# =============================================================================
# ALBERTH LEARN — Script CLI para aprendizaje directo y corrección continua
# Uso: python3 alberth_learn.py "Recuerda que para la firma de DAI usamos Vista Previa"
# =============================================================================

import os
import sys
import argparse

# Asegurar import de alberth_memory
WORKSPACE_DIR = os.environ.get("OPENCLAW_WORKSPACE") or os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORKSPACE_DIR)

from alberth_memory import save_conversation, audit_log, get_current_mode

def main():
    parser = argparse.ArgumentParser(description="Alberth Learn — CLI Feedback & Learning")
    parser.add_argument("text", type=str, help="Texto de instrucción o corrección para Alberth")
    parser.add_argument("--category", default="feedback", help="Categoría de aprendizaje")
    args = parser.parse_args()

    mode = get_current_mode()
    query = f"[FEEDBACK / APRENDIZAJE MANUALLY ADDED - Modo: {mode.upper()}] {args.text}"
    response = f"Entendido Señor. Aprendizaje registrado en memoria ({mode.upper()}): {args.text}"

    save_conversation(query=query, response=response, tags=f"learn,{mode}", importance=5)
    audit_log(agente="user_cli_learn", query=args.text, modelo="manual_input", latencia_ms=0)

    print(f"✅ Aprendizaje guardado exitosamente en modo [{mode.upper()}]:")
    print(f"   \"{args.text}\"")

if __name__ == "__main__":
    main()
