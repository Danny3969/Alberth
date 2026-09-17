#!/usr/bin/env python3
"""
ag-console.py – Consola de Desarrollo & Operaciones de Alberth (AGC)
Integrada con Antigravity IDE, terminal de macOS y el Quantum HUD de Novasyscom.
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

# ── Localización de Archivos ──────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "ag-config.yaml"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── Colores ANSI para Terminal ────────────────────────────────────────────────
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_BLUE = "\033[94m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def banner():
    print(f"{C_CYAN}{C_BOLD}┌──────────────────────────────────────────────────────────┐{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}│  ⚡ ALBERTH DEV CONSOLE (AGC) · ANTIGRAVITY ENGINE v1.0   │{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}│  Novasyscom Corporate Suite · Drivo | Alberth | Valex    │{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}└──────────────────────────────────────────────────────────┘{C_RESET}")

# ── Carga de Configuración (YAML con fallback) ─────────────────────────────────
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {
            "hud": {"api_url": "http://localhost:8080/api/console/event", "browser_url": "http://localhost:8080"},
            "antigravity": {
                "bin_path": "/Users/contabilidad/.antigravity-ide/antigravity-ide/bin/agy-ide",
                "app_name": "Antigravity IDE"
            },
            "projects": {}
        }
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        # Fallback simple si pyyaml no está en el python3 del sistema
        # Intentamos usar el venv de Alberth
        venv_py = BASE_DIR.parent / "venv" / "bin" / "python3"
        if venv_py.exists():
            cmd = [str(venv_py), "-c", "import yaml, json, sys; print(json.dumps(yaml.safe_load(open(sys.argv[1]))))", str(CONFIG_PATH)]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return json.loads(res.stdout)
        print(f"{C_YELLOW}[!] Advertencia: PyYAML no disponible en este intérprete.{C_RESET}")
        return {}

# ── Telemetría al Quantum HUD ─────────────────────────────────────────────────
def notify_hud(config: dict, event: dict):
    api_url = config.get("hud", {}).get("api_url", "http://localhost:8080/api/console/event")
    try:
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "AlberthAGC/1.0"}
        )
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            pass
    except Exception:
        # Silencioso si el servidor HUD está temporalmente apagado
        pass

# ── Persistencia de Logs ──────────────────────────────────────────────────────
def log_execution(project: str, command: str, status: str, output: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOGS_DIR / f"{project or 'system'}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n[{ts}] [CMD: {command}] [STATUS: {status}]\n")
        f.write(output.strip() + "\n" + ("─" * 60) + "\n")

# ── Acciones Principales ──────────────────────────────────────────────────────
def action_list(config: dict):
    banner()
    projects = config.get("projects", {})
    print(f"\n{C_BOLD}Proyectos Registrados en Novasyscom:{C_RESET}\n")
    print(f" {'ALIAS':<14} {'CATEGORÍA':<16} {'PUERTO':<8} {'ESTADO GIT':<15} {'DESCRIPCIÓN'}")
    print(f" {('─'*14)} {('─'*16)} {('─'*8)} {('─'*15)} {('─'*30)}")

    for key, p in projects.items():
        path = Path(p.get("path", "")).expanduser()
        exists = path.exists()
        git_state = "No git"
        if exists and (path / ".git").exists():
            branch = subprocess.run(["git", "branch", "--show-current"], cwd=path, capture_output=True, text=True).stdout.strip()
            diff = subprocess.run(["git", "status", "-s"], cwd=path, capture_output=True, text=True).stdout.strip()
            modified = len(diff.splitlines()) if diff else 0
            git_state = f"{C_GREEN}{branch}{C_RESET}" if modified == 0 else f"{C_YELLOW}{branch} (+{modified}){C_RESET}"
        elif not exists:
            git_state = f"{C_RED}No existe{C_RESET}"

        port = str(p.get("port", "-"))
        cat = p.get("category", "General")
        desc = p.get("description", "")
        print(f" {C_CYAN}{C_BOLD}{key:<14}{C_RESET} {cat:<16} {port:<8} {git_state:<24} {desc}")
    print()

def action_open(config: dict, project_key: str):
    projects = config.get("projects", {})
    if project_key not in projects:
        print(f"{C_RED}[ERROR] Proyecto '{project_key}' no reconocido. Ejecuta 'agc list'.{C_RESET}")
        return 1

    p = projects[project_key]
    path = Path(p.get("path", "")).expanduser()
    if not path.exists():
        print(f"{C_RED}[ERROR] La ruta del proyecto no existe: {path}{C_RESET}")
        return 1

    print(f"\n{C_CYAN}🚀 Abriendo {C_BOLD}{p.get('name', project_key)}{C_RESET}{C_CYAN} en Antigravity IDE...{C_RESET}")
    agy_bin = config.get("antigravity", {}).get("bin_path", "/Users/contabilidad/.antigravity-ide/antigravity-ide/bin/agy-ide")
    app_name = config.get("antigravity", {}).get("app_name", "Antigravity IDE")

    # 1. Intentar abrir con el binario CLI
    opened = False
    if Path(agy_bin).exists():
        res = subprocess.run([agy_bin, str(path)], capture_output=True, text=True)
        if res.returncode == 0:
            opened = True

    # 2. Fallback con comando open de macOS
    if not opened:
        res = subprocess.run(["open", "-a", app_name, str(path)], capture_output=True, text=True)
        if res.returncode != 0:
            # Probar nombre genérico Antigravity
            res = subprocess.run(["open", "-a", "Antigravity", str(path)], capture_output=True, text=True)
        opened = (res.returncode == 0)

    status = "SUCCESS" if opened else "ERROR"
    msg = f"Proyecto {p.get('name', project_key)} abierto en Antigravity ({path})" if opened else f"Error al abrir en Antigravity: {path}"
    print(f"[{C_GREEN}✓{C_RESET}] {msg}" if opened else f"[{C_RED}✗{C_RESET}] {msg}")

    # Notificar HUD
    notify_hud(config, {
        "project": project_key,
        "action": "open",
        "command": f"agc open {project_key}",
        "status": status,
        "output": msg,
        "timestamp": time.time()
    })
    log_execution(project_key, "open", status, msg)
    return 0 if opened else 1

def action_status(config: dict, project_key: str = None):
    projects = config.get("projects", {})
    keys = [project_key] if project_key else list(projects.keys())

    all_outputs = []
    for k in keys:
        if k not in projects:
            print(f"{C_RED}[ERROR] Proyecto '{k}' no reconocido.{C_RESET}")
            continue
        p = projects[k]
        path = Path(p.get("path", "")).expanduser()
        print(f"\n{C_CYAN}{C_BOLD}=== ESTADO: {p.get('name', k)} ==={C_RESET}")
        print(f"{C_DIM}Ruta:{C_RESET} {path}")

        if not path.exists():
            print(f"{C_RED}Ruta no encontrada en el sistema.{C_RESET}")
            continue

        # Git status
        git_res = subprocess.run(["git", "status", "-s"], cwd=path, capture_output=True, text=True)
        branch_res = subprocess.run(["git", "branch", "--show-current"], cwd=path, capture_output=True, text=True)
        log_res = subprocess.run(["git", "log", "-1", "--oneline"], cwd=path, capture_output=True, text=True)
        remote_res = subprocess.run(["git", "status", "-uno"], cwd=path, capture_output=True, text=True)

        branch = branch_res.stdout.strip() or "HEAD"
        last_commit = log_res.stdout.strip() or "Sin commits"
        diff_lines = [l for l in git_res.stdout.splitlines() if l.strip()]

        print(f"{C_BOLD}Rama Git:{C_RESET} {C_GREEN}{branch}{C_RESET}")
        print(f"{C_BOLD}Último Commit:{C_RESET} {last_commit}")

        if "ahead" in remote_res.stdout:
            print(f"{C_YELLOW}⚠ Tienes commits locales pendientes de subir (git push).{C_RESET}")
        elif "up to date" in remote_res.stdout:
            print(f"{C_GREEN}✓ Al día con el repositorio remoto en GitHub.{C_RESET}")

        if diff_lines:
            print(f"{C_YELLOW}Archivos modificados ({len(diff_lines)}):{C_RESET}")
            for l in diff_lines[:8]:
                print(f"  {l}")
            if len(diff_lines) > 8:
                print(f"  ... y {len(diff_lines)-8} archivos más.")
        else:
            print(f"{C_GREEN}✓ Área de trabajo limpia (sin cambios pendientes).{C_RESET}")

        report = f"[{k}] Rama: {branch} | Commit: {last_commit} | Cambios: {len(diff_lines)}"
        all_outputs.append(report)

    output_summary = "\n".join(all_outputs)
    notify_hud(config, {
        "project": project_key or "all",
        "action": "status",
        "command": f"agc status {project_key or ''}".strip(),
        "status": "SUCCESS",
        "output": output_summary,
        "timestamp": time.time()
    })
    log_execution(project_key or "all", "status", "SUCCESS", output_summary)
    return 0

def action_git(config: dict, project_key: str, git_args: list):
    projects = config.get("projects", {})
    if project_key not in projects:
        print(f"{C_RED}[ERROR] Proyecto '{project_key}' no reconocido.{C_RESET}")
        return 1

    path = Path(projects[project_key].get("path", "")).expanduser()
    if not path.exists():
        print(f"{C_RED}[ERROR] La ruta no existe: {path}{C_RESET}")
        return 1

    cmd = ["git"] + git_args
    cmd_str = " ".join(cmd)
    print(f"\n{C_CYAN}Ejecutando en {project_key}: {C_BOLD}{cmd_str}{C_RESET}\n")

    res = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
    out = (res.stdout or res.stderr or "").strip()
    print(out)

    status = "SUCCESS" if res.returncode == 0 else "ERROR"
    notify_hud(config, {
        "project": project_key,
        "action": "git",
        "command": f"agc git {project_key} {' '.join(git_args)}",
        "status": status,
        "output": out,
        "timestamp": time.time()
    })
    log_execution(project_key, f"git {' '.join(git_args)}", status, out)
    return res.returncode

def action_run(config: dict, project_key: str, script_name: str, extra_args: list = None):
    projects = config.get("projects", {})
    if project_key not in projects:
        print(f"{C_RED}[ERROR] Proyecto '{project_key}' no reconocido.{C_RESET}")
        return 1

    p = projects[project_key]
    scripts = p.get("scripts", {})
    if script_name not in scripts:
        print(f"{C_RED}[ERROR] Script '{script_name}' no definido para {project_key}. Scripts disponibles: {list(scripts.keys())}{C_RESET}")
        return 1

    cmd_script = scripts[script_name]
    path = Path(p.get("path", "")).expanduser()
    full_cmd = f"{cmd_script} {' '.join(extra_args or [])}".strip()

    print(f"\n{C_CYAN}Ejecutando script [{script_name}] en {project_key}: {C_BOLD}{full_cmd}{C_RESET}\n")
    res = subprocess.run(full_cmd, cwd=path, shell=True, capture_output=True, text=True)
    out = (res.stdout or res.stderr or "").strip()
    print(out)

    status = "SUCCESS" if res.returncode == 0 else "ERROR"
    notify_hud(config, {
        "project": project_key,
        "action": "run",
        "command": f"agc run {project_key} {script_name}",
        "status": status,
        "output": out,
        "timestamp": time.time()
    })
    log_execution(project_key, f"run {script_name}", status, out)
    return res.returncode

def save_config(config: dict):
    try:
        import yaml
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        print(f"{C_YELLOW}[!] Error guardando config yaml: {e}{C_RESET}")

def action_new(config: dict, name: str, template: str = "blank", category: str = "General", description: str = ""):
    banner()
    project_slug = name.lower().strip().replace(" ", "-")
    scratch_dir = Path("/Users/contabilidad/.gemini/antigravity-ide/scratch")
    project_path = scratch_dir / project_slug

    if project_path.exists():
        print(f"{C_RED}[ERROR] La carpeta ya existe: {project_path}{C_RESET}")
        return 1

    print(f"\n{C_CYAN}📁 Creando nuevo proyecto: {C_BOLD}{name}{C_RESET} (Plantilla: {template})")
    project_path.mkdir(parents=True, exist_ok=True)

    # 1. Inicializar Git
    subprocess.run(["git", "init"], cwd=project_path, capture_output=True)

    # 2. Scaffolding básico
    readme_content = f"# {name.upper()}\n\nProyecto de Novasyscom.\nCategoría: {category}\nPlantilla: {template}\n"
    (project_path / "README.md").write_text(readme_content, encoding="utf-8")

    gitignore_content = ".DS_Store\nnode_modules/\nbuild/\n*.log\n.env\n"
    (project_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")

    if template == "flutter":
        (project_path / "pubspec.yaml").write_text(f"name: {project_slug}\ndescription: {description or name}\nversion: 1.0.0+1\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\n", encoding="utf-8")
        (project_path / "lib").mkdir(exist_ok=True)
        (project_path / "lib" / "main.dart").write_text("// Entry point Flutter\nvoid main() {\n  print('Hola Novasyscom');\n}\n", encoding="utf-8")
    elif template in ["react", "node"]:
        pkg_json = {
            "name": project_slug,
            "version": "1.0.0",
            "private": True,
            "scripts": {"dev": "vite", "build": "vite build"} if template == "react" else {"start": "node index.js"}
        }
        (project_path / "package.json").write_text(json.dumps(pkg_json, indent=2), encoding="utf-8")
    elif template == "fastapi":
        (project_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root(): return {'status': 'ok'}\n", encoding="utf-8")
        (project_path / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", f"feat: inicializar proyecto {name} ({template})"], cwd=project_path, capture_output=True)

    # 3. Registrar en ag-config.yaml
    if "projects" not in config:
        config["projects"] = {}
    config["projects"][project_slug] = {
        "name": name.upper(),
        "path": str(project_path),
        "category": category,
        "description": description or f"Proyecto {name}",
        "port": 0,
        "scripts": {
            "dev": "npm run dev" if template in ["react", "node"] else ("flutter run" if template == "flutter" else "python3 main.py")
        }
    }
    save_config(config)

    print(f"[{C_GREEN}✓{C_RESET}] Repositorio inicializado en {project_path}")
    print(f"[{C_GREEN}✓{C_RESET}] Registrado exitosamente en ag-config.yaml")

    notify_hud(config, {
        "project": project_slug,
        "action": "new",
        "command": f"agc new {name}",
        "status": "SUCCESS",
        "output": f"Nuevo proyecto {name} creado en {project_path}",
        "timestamp": time.time()
    })

    # Abrir en Antigravity IDE
    action_open(config, project_slug)
    return 0

def action_hud(config: dict):
    url = config.get("hud", {}).get("browser_url", "http://localhost:8080")
    print(f"{C_CYAN}Abriendo Quantum HUD en Google Chrome: {C_BOLD}{url}{C_RESET}")
    subprocess.run(["open", "-a", "Google Chrome", url])
    return 0

def action_obsidian(config: dict):
    banner()
    vault_path = Path("/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth")
    print(f"\n{C_CYAN}🧠 Abriendo Bóveda de Conocimiento Novasyscom en Obsidian...{C_RESET}")
    print(f"{C_DIM}Ruta de Bóveda:{C_RESET} {vault_path}\n")
    res = subprocess.run(["open", "-a", "Obsidian", str(vault_path)], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"[{C_GREEN}✓{C_RESET}] Bóveda abierta exitosamente en Obsidian.app")
        notify_hud(config, {
            "project": "alberth",
            "action": "obsidian",
            "command": "agc obsidian",
            "status": "SUCCESS",
            "output": f"Bóveda Obsidian abierta en {vault_path}",
            "timestamp": time.time()
        })
        log_execution("alberth", "obsidian", "SUCCESS", f"Bóveda abierta en {vault_path}")
        return 0
    else:
        print(f"[{C_RED}✗{C_RESET}] Error al abrir Obsidian: {res.stderr}")
        return 1

# ── Argument Normalizer (Sintaxis Flexible) ───────────────────────────────────
def normalize_args(args: list, valid_projects: list) -> tuple:
    if not args:
        return ("list", None, [])

    first = args[0].lower()
    rest = args[1:]

    # Casos sin proyecto:
    if first in ["list", "hud", "obsidian", "vault", "-h", "--help", "help"]:
        return (first, None, rest)

    if first == "new":
        proj_name = rest[0] if rest else None
        return ("new", proj_name, rest[1:] if len(rest) > 1 else [])

    # Si el primer argumento es un proyecto: agc drivo open -> acción='open', proyecto='drivo'
    if first in valid_projects:
        proj = first
        act = rest[0].lower() if rest else "status"
        sub_args = rest[1:] if len(rest) > 1 else []
        return (act, proj, sub_args)

    # Si el primer argumento es una acción: agc open drivo -> acción='open', proyecto='drivo'
    act = first
    proj = rest[0].lower() if rest else None
    sub_args = rest[1:] if len(rest) > 1 else []
    return (act, proj, sub_args)

# ── Entry Point ───────────────────────────────────────────────────────────────
def main():
    config = load_config()
    valid_projects = list(config.get("projects", {}).keys())

    raw_args = sys.argv[1:]
    action, project, extra = normalize_args(raw_args, valid_projects)

    if action in ["help", "-h", "--help"]:
        banner()
        print("""
Uso:
  agc list                         → Lista todos los proyectos corporativos y su estado
  agc open <proyecto>              → Abre el proyecto en Antigravity IDE (o: agc <proyecto> open)
  agc status [proyecto]            → Muestra la rama git, commits pendientes y cambios
  agc git <proyecto> <args...>     → Ejecuta comandos git en el proyecto seleccionado
  agc run <proyecto> <script>      → Ejecuta scripts definidos (dev, build, status, etc.)
  agc new <nombre> [--template X]  → Crea e inicializa un nuevo proyecto en Antigravity
  agc obsidian                     → Abre la Bóveda de Conocimiento y Canvas en Obsidian
  agc hud                          → Abre el Quantum HUD en Google Chrome

Proyectos disponibles:
  drivo | drivo-one | alberth | globalmarket | valex
        """)
        sys.exit(0)

    if action == "list":
        sys.exit(action_list(config))

    if action == "hud":
        sys.exit(action_hud(config))

    if action in ["obsidian", "vault"]:
        sys.exit(action_obsidian(config))

    if action == "new":
        if not project:
            print(f"{C_RED}[ERROR] Especifica el nombre del nuevo proyecto. Ej: agc new mi-app{C_RESET}")
            sys.exit(1)
        template = "blank"
        if "--template" in extra:
            idx = extra.index("--template")
            if idx + 1 < len(extra):
                template = extra[idx + 1]
        sys.exit(action_new(config, project, template=template))

    if action == "open":
        if not project:
            print(f"{C_RED}[ERROR] Debes especificar un proyecto para abrir. Ej: agc open drivo{C_RESET}")
            sys.exit(1)
        sys.exit(action_open(config, project))

    if action == "status":
        sys.exit(action_status(config, project))

    if action == "git":
        if not project:
            print(f"{C_RED}[ERROR] Especifica el proyecto. Ej: agc git drivo status{C_RESET}")
            sys.exit(1)
        if not extra:
            extra = ["status"]
        sys.exit(action_git(config, project, extra))

    if action == "run":
        if not project or not extra:
            print(f"{C_RED}[ERROR] Uso: agc run <proyecto> <script>. Ej: agc run alberth status{C_RESET}")
            sys.exit(1)
        script_name = extra[0]
        script_args = extra[1:]
        sys.exit(action_run(config, project, script_name, script_args))

    print(f"{C_RED}[ERROR] Comando no reconocido: '{action}'. Ejecuta 'agc help'.{C_RESET}")
    sys.exit(1)

if __name__ == "__main__":
    main()
