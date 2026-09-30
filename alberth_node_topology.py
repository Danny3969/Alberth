#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_node_topology.py — Gestor de Topología de Nodos Distribuidos para Alberth (R9)
======================================================================================
Permite gestionar la arquitectura multi-nodo descrita en SOUL.md:
- Nodo Maestro (MacBook Pro / Servidor AI)
- Nodo Periférico (iMac / Cámara / Sensores)
- Nodos Edge (Dispositivos móviles / PWA)

Verifica latencias, disponibilidad de puertos y orquesta la distribución de carga.
"""

from __future__ import annotations

import os
import sys
import json
import socket
import time
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())
CONFIG_PATH = WORKSPACE_DIR / "alberth_gateway_config.json"


def load_topology() -> Dict[str, Any]:
    """Carga la configuración de nodos del gateway."""
    if not CONFIG_PATH.exists():
        return {"nodes": [], "active_node": {"role": "standalone"}}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e), "nodes": []}


def check_node_health(ip: str, port: int, timeout: float = 1.0) -> Dict[str, Any]:
    """Evalúa la latencia y disponibilidad de un nodo remoto."""
    t_start = time.time()
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            elapsed_ms = round((time.time() - t_start) * 1000, 2)
            return {"online": True, "ping_ms": elapsed_ms}
    except Exception:
        return {"online": False, "ping_ms": None}


def get_topology_status() -> Dict[str, Any]:
    """Genera un reporte del estado de todos los nodos configurados."""
    topo = load_topology()
    nodes = topo.get("nodes", [])
    report = []

    for n in nodes:
        ip = n.get("ip")
        port = n.get("port")
        health = {"online": True, "ping_ms": 0.5} if ip in ("127.0.0.1", "localhost") else check_node_health(ip, port) if ip and port else {"online": False, "ping_ms": None}
        report.append({
            "id": n.get("id"),
            "name": n.get("name"),
            "role": n.get("role"),
            "services": n.get("services", []),
            "status": "ONLINE" if health.get("online") else "OFFLINE",
            "ping_ms": health.get("ping_ms")
        })

    return {
        "active_role": topo.get("active_node", {}).get("role", "master"),
        "nodes_status": report
    }


if __name__ == "__main__":
    print("🌐 Evaluando Topología Distribuida de Alberth (R9)...")
    status = get_topology_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
