#!/usr/bin/env python3
# =============================================================================
# ALBERTH GITHUB HELPER — Integración Avanzada con GitHub CLI (gh)
# Permite al Agente de Código inspeccionar repositorios, PRs, issues y commits.
# =============================================================================

import sys
import subprocess
import json

def run_gh_command(args: list[str]) -> str:
    """Ejecuta un comando gh CLI y retorna el resultado."""
    try:
        res = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            return res.stdout.strip()
        else:
            return f"Error ({res.returncode}): {res.stderr.strip()}"
    except Exception as e:
        return f"Excepción ejecutando gh CLI: {e}"

def list_repos():
    return run_gh_command(["repo", "list", "--limit", "10"])

def repo_status(repo_name: str = None):
    args = ["repo", "view"]
    if repo_name:
        args.append(repo_name)
    return run_gh_command(args)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--list-repos":
            print(list_repos())
        elif cmd == "--status" and len(sys.argv) > 2:
            print(repo_status(sys.argv[2]))
        else:
            print(run_gh_command(sys.argv[1:]))
    else:
        print("Uso: alberth_github_helper.py --list-repos | --status <repo> | <gh_args>")
