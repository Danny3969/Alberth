#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
ALBERTH REA ENGINE (Reverse Engineering & Architecture Engine)
Módulo nativo de Alberth para inspección estructural de software,
auditoría de dependencias, desensamblado de paquetes (APK/Bundles)
y Recreación de Funcionalidades en Ingeniería Limpia (Clean-Room Engineering).
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import os
import re
import ast
import json
import time
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

WORKSPACE = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).resolve().parent)
REA_REPORTS_DIR = WORKSPACE / "memory" / "rea_reports"
REA_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class AlberthREAEngine:
    """Motor de Ingeniería Inversa y Análisis de Arquitectura para Alberth."""

    @staticmethod
    def inspect_code_architecture(target_path_str: str) -> Dict[str, Any]:
        """
        Inspecciona a fondo un archivo, repositorio o directorio de código.
        Detecta lenguajes, frameworks, puntos de entrada, dependencias,
        rutas de API y complejidad estructural.
        """
        p = Path(target_path_str)
        if not p.is_absolute():
            p = (WORKSPACE / p).resolve()

        if not p.exists():
            return {
                "ok": False,
                "error": f"La ruta indicada no existe: {target_path_str}",
                "target": str(p)
            }

        start_time = time.time()

        if p.is_file():
            res = AlberthREAEngine._inspect_single_file(p)
        else:
            res = AlberthREAEngine._inspect_directory(p)

        res["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        res["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Guardar reporte en memoria
        report_file = REA_REPORTS_DIR / f"rea_audit_{int(time.time())}.json"
        try:
            report_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
            res["report_path"] = str(report_file)
        except Exception:
            pass

        return res

    @staticmethod
    def _inspect_single_file(f: Path) -> Dict[str, Any]:
        """Analiza un único archivo de código o script."""
        ext = f.suffix.lower()
        size_bytes = f.stat().st_size
        text = ""
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return {"ok": False, "error": f"No se pudo leer el archivo: {e}"}

        lines = text.splitlines()
        line_count = len(lines)

        analysis = {
            "ok": True,
            "type": "single_file",
            "name": f.name,
            "path": str(f),
            "size_kb": round(size_bytes / 1024, 2),
            "lines": line_count,
            "language": AlberthREAEngine._detect_language(ext),
            "components": [],
            "imports": [],
            "endpoints": [],
            "secrets_detected": [],
            "summary": ""
        }

        # Detección de endpoints / URLs
        endpoints = re.findall(r'[\'"`](https?://[^\s\'"`]+|/(?:api|v[0-9]|ws)/[^\s\'"`]*)[\'"`]', text)
        analysis["endpoints"] = list(set(endpoints))[:25]

        # Detección de posibles tokens o claves en texto duro
        secret_patterns = [
            (r'(?i)(?:api_key|token|secret|password|bearer)\s*[:=]\s*[\'"`]([a-zA-Z0-9_\-\.]{12,})[\'"`]', "Posible Token/API Key"),
        ]
        for pat, label in secret_patterns:
            matches = re.findall(pat, text)
            for m in matches[:5]:
                analysis["secrets_detected"].append(f"{label}: {m[:4]}***{m[-4:]}")

        # Análisis específico según lenguaje
        if ext == ".py":
            analysis.update(AlberthREAEngine._parse_python_ast(text))
        elif ext in [".js", ".jsx", ".ts", ".tsx"]:
            analysis.update(AlberthREAEngine._parse_js_ts(text))

        analysis["summary"] = (
            f"Archivo {f.name} ({analysis['language']}): {line_count} líneas, "
            f"{len(analysis.get('functions', []))} funciones, "
            f"{len(analysis.get('classes', []))} clases, "
            f"{len(analysis['endpoints'])} rutas/endpoints detectados."
        )
        return analysis

    @staticmethod
    def _inspect_directory(dir_path: Path) -> Dict[str, Any]:
        """Analiza un árbol completo de proyecto o repositorio."""
        ext_counter = {}
        total_files = 0
        total_lines = 0
        dependencies = []
        frameworks = set()
        entry_points = []
        endpoints_all = set()

        ignored_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".gradle", "ios/Pods"}

        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                fpath = Path(root) / file
                ext = fpath.suffix.lower()
                ext_counter[ext] = ext_counter.get(ext, 0) + 1
                total_files += 1

                # Detectar dependencias clave
                if file == "package.json":
                    frameworks.add("Node.js/JavaScript")
                    try:
                        pkg = json.loads(fpath.read_text(encoding="utf-8", errors="ignore"))
                        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                        for dep in deps.keys():
                            dependencies.append(dep)
                            if "react-native" in dep: frameworks.add("React Native")
                            elif "react" in dep: frameworks.add("React")
                            elif "vue" in dep: frameworks.add("Vue")
                            elif "next" in dep: frameworks.add("Next.js")
                            elif "express" in dep: frameworks.add("Express")
                            elif "expo" in dep: frameworks.add("Expo Mobile")
                    except Exception:
                        pass
                elif file == "requirements.txt":
                    frameworks.add("Python")
                    try:
                        for l in fpath.read_text(encoding="utf-8", errors="ignore").splitlines():
                            l = l.strip()
                            if l and not l.startswith("#"):
                                dep_name = re.split(r'[=<>]', l)[0].strip()
                                dependencies.append(dep_name)
                                if "fastapi" in dep_name: frameworks.add("FastAPI")
                                elif "flask" in dep_name: frameworks.add("Flask")
                                elif "django" in dep_name: frameworks.add("Django")
                                elif "pytorch" in dep_name or "torch" in dep_name: frameworks.add("PyTorch")
                    except Exception:
                        pass
                elif file in ["build.gradle", "settings.gradle"]:
                    frameworks.add("Android / Gradle")
                elif file == "pubspec.yaml":
                    frameworks.add("Flutter / Dart")

                # Detectar Puntos de Entrada
                if file in ["main.py", "app.py", "server.py", "index.js", "App.tsx", "main.ts", "index.ts", "server.js", "manage.py"]:
                    entry_points.append(str(fpath.relative_to(dir_path)))

                # Muestreo de líneas (en archivos de código)
                if ext in [".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".go", ".rs", ".java"]:
                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                        total_lines += len(content.splitlines())
                        # Rutas
                        eps = re.findall(r'[\'"`](/(?:api|v[0-9]|ws)/[^\s\'"`]*)[\'"`]', content)
                        for ep in eps[:5]:
                            endpoints_all.add(ep)
                    except Exception:
                        pass

        # Determinar arquitectura estimada
        arch_type = "Monolito de Scripting"
        if "FastAPI" in frameworks or "Express" in frameworks:
            arch_type = "Servicio API REST / WebSocket"
        if "React Native" in frameworks or "Expo Mobile" in frameworks:
            arch_type = "Aplicación Móvil Cross-Platform"
        if len(entry_points) > 2 and ("Node.js/JavaScript" in frameworks and "Python" in frameworks):
            arch_type = "Arquitectura Híbrida / Multi-Agente"

        return {
            "ok": True,
            "type": "directory_project",
            "name": dir_path.name,
            "path": str(dir_path),
            "architecture_pattern": arch_type,
            "frameworks_detected": sorted(list(frameworks)),
            "total_files": total_files,
            "total_lines_approx": total_lines,
            "file_extensions": dict(sorted(ext_counter.items(), key=lambda x: x[1], reverse=True)[:8]),
            "entry_points": entry_points,
            "dependencies_sample": sorted(list(set(dependencies)))[:30],
            "endpoints_detected": sorted(list(endpoints_all))[:20],
            "summary": (
                f"Proyecto {dir_path.name} ({arch_type}): {total_files} archivos, "
                f"aprox. {total_lines:,} líneas de código. "
                f"Frameworks: {', '.join(frameworks) if frameworks else 'Estándar'}. "
                f"{len(entry_points)} puntos de entrada detectados."
            )
        }

    @staticmethod
    def _parse_python_ast(code: str) -> Dict[str, Any]:
        """Extrae clases, funciones, decoradores e imports vía AST."""
        classes = []
        functions = []
        imports = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({"name": node.name, "methods": methods[:10], "line": node.lineno})
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Solo funciones raíz
                    is_async = isinstance(node, ast.AsyncFunctionDef)
                    decs = [ast.unparse(d) for d in node.decorator_list if hasattr(ast, "unparse")]
                    functions.append({
                        "name": node.name,
                        "async": is_async,
                        "decorators": decs,
                        "line": node.lineno
                    })
                elif isinstance(node, ast.Import):
                    for n in node.names:
                        imports.append(n.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except Exception as e:
            return {"ast_parse_error": str(e)}

        return {
            "classes": classes[:20],
            "functions": functions[:40],
            "imports": sorted(list(set(imports)))[:30]
        }

    @staticmethod
    def _parse_js_ts(code: str) -> Dict[str, Any]:
        """Extrae funciones, componentes de React e imports de JS/TS."""
        functions = re.findall(r'(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(', code)
        arrow_funcs = re.findall(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>', code)
        react_components = re.findall(r'(?:export\s+(?:default\s+)?)?(?:function|const)\s+([A-Z][a-zA-Z0-9_$]+)', code)
        imports = re.findall(r'(?:import|require)\s*\(?[\'"`]([^\'"`]+)[\'"`]', code)

        all_funcs = list(set(functions + arrow_funcs))
        return {
            "functions": all_funcs[:30],
            "react_components": list(set(react_components))[:15],
            "imports": list(set(imports))[:25]
        }

    @staticmethod
    def _detect_language(ext: str) -> str:
        mapping = {
            ".py": "Python", ".js": "JavaScript", ".jsx": "React JSX",
            ".ts": "TypeScript", ".tsx": "React TSX", ".html": "HTML5",
            ".css": "CSS3", ".json": "JSON", ".sh": "Bash Shell",
            ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
            ".apk": "Android Package", ".sql": "SQL Database"
        }
        return mapping.get(ext, f"Desconocido ({ext})")

    # ══════════════════════════════════════════════════════════════════════════
    # INSPECCIÓN DE PAQUETES Y APLICACIONES (.APK, .ZIP, BUNDLES)
    # ══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def inspect_package_bundle(package_path_str: str) -> Dict[str, Any]:
        """
        Desarma e inspecciona un paquete (.apk, .zip, .tar.gz) sin requerir
        desensambladores pesados. Extrae arquitectura, librerías nativas,
        assets, permisos y componentes empaquetados.
        """
        p = Path(package_path_str)
        if not p.is_absolute():
            p = (WORKSPACE / p).resolve()

        if not p.exists():
            return {"ok": False, "error": f"Archivo no encontrado: {package_path_str}"}

        start_time = time.time()
        ext = p.suffix.lower()

        if ext == ".apk" or zipfile.is_zipfile(p):
            res = AlberthREAEngine._inspect_zip_or_apk(p)
        else:
            res = {"ok": False, "error": f"Formato no soportado para inspección de paquete: {ext}"}

        res["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        res["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Guardar reporte
        report_file = REA_REPORTS_DIR / f"rea_package_{int(time.time())}.json"
        try:
            report_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
            res["report_path"] = str(report_file)
        except Exception:
            pass

        return res

    @staticmethod
    def _inspect_zip_or_apk(p: Path) -> Dict[str, Any]:
        """Inspecciona internamente un archivo APK o ZIP."""
        is_apk = p.suffix.lower() == ".apk"
        entries = []
        native_libs = set()
        assets = []
        is_react_native = False
        is_flutter = False
        dex_files = []
        bundle_endpoints = []
        bundle_strings = []

        try:
            with zipfile.ZipFile(p, 'r') as z:
                names = z.namelist()
                total_entries = len(names)

                for name in names:
                    if name.startswith("lib/"):
                        # Librería nativa
                        parts = name.split("/")
                        if len(parts) >= 3:
                            native_libs.add(f"{parts[1]}:{parts[2]}")
                        if "libflutter.so" in name: is_flutter = True
                    elif name.endswith(".dex"):
                        dex_files.append(name)
                    elif "index.android.bundle" in name:
                        is_react_native = True
                        # Analizar el bundle compilado de JS
                        try:
                            bundle_data = z.read(name).decode("utf-8", errors="ignore")
                            # Extraer URLs y endpoints embebidos
                            eps = re.findall(r'[\'"`](https?://[^\s\'"`]+|/(?:api|v[0-9]|ws)/[^\s\'"`]*)[\'"`]', bundle_data)
                            bundle_endpoints.extend(eps[:20])
                            # Muestra de identificadores
                            matches = re.findall(r'\b(?:ws|wss|http|https)://[a-zA-Z0-9\.\-_:]+\b', bundle_data)
                            bundle_strings.extend(matches[:15])
                        except Exception:
                            pass
                    elif name.startswith("assets/"):
                        assets.append(name)

                # Intentar leer AndroidManifest si es APK
                manifest_strings = []
                if is_apk and "AndroidManifest.xml" in names:
                    raw_manifest = z.read("AndroidManifest.xml")
                    # Extracción de strings ASCII / UTF-8 limpios del manifest binario
                    ascii_strings = re.findall(rb'[a-zA-Z0-9\._\-]{4,}', raw_manifest)
                    manifest_strings = [s.decode('ascii', errors='ignore') for s in ascii_strings[:100]]

        except Exception as e:
            return {"ok": False, "error": f"Error al abrir el paquete: {e}"}

        framework = "Nativo (Java/Kotlin)"
        if is_react_native: framework = "React Native"
        elif is_flutter: framework = "Flutter"

        permissions = [s for s in manifest_strings if "permission" in s.lower() or "android.permission" in s]

        return {
            "ok": True,
            "type": "apk_package" if is_apk else "zip_archive",
            "name": p.name,
            "path": str(p),
            "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
            "framework": framework,
            "total_files": total_entries,
            "dex_containers": dex_files,
            "native_architectures": list(set([l.split(":")[0] for l in native_libs])),
            "native_libraries_sample": list(native_libs)[:15],
            "permissions_detected": permissions[:15],
            "embedded_endpoints": list(set(bundle_endpoints))[:20],
            "embedded_servers": list(set(bundle_strings))[:10],
            "assets_count": len(assets),
            "summary": (
                f"Paquete {p.name} ({framework}): {round(p.stat().st_size / (1024 * 1024), 2)} MB. "
                f"Detectados {len(dex_files)} archivos DEX, {len(native_libs)} librerías nativas "
                f"y {len(permissions)} declaraciones de permisos."
            )
        }

    # ══════════════════════════════════════════════════════════════════════════
    # GENERADOR DE ESPECIFICACIÓN CLEAN-ROOM (INGENIERÍA LIMPIA)
    # ══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def generate_clean_room_specification(
        target_name: str,
        feature_intent: str,
        inspected_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera una especificación de Ingeniería Limpia para recrear una función
        o componente observado en un software externo, adaptándolo directamente
        a la pila tecnológica de Alberth (FastAPI, Python, Vanilla JS, React Native).
        """
        inspected_context = ""
        endpoints_hint = []
        if inspected_data and inspected_data.get("ok"):
            endpoints_hint = inspected_data.get("endpoints") or inspected_data.get("embedded_endpoints") or []
            inspected_context = f"Basado en la inspección de: {inspected_data.get('name', 'objetivo')}"

        spec_id = f"clean_room_{int(time.time())}"
        
        # Mapeo de Arquitectura Propuesta
        spec = {
            "ok": True,
            "spec_id": spec_id,
            "target_name": target_name,
            "feature_intent": feature_intent,
            "context": inspected_context,
            "clean_room_protocol": {
                "step_1_behavior": f"Modelar el contrato funcional de entrada/salida para '{feature_intent}'.",
                "step_2_data_structures": "Diseñar esquemas Pydantic desacoplados sin copiar estructuras protegidas.",
                "step_3_implementation": "Escribir código nativo en Python/FastAPI con lógica idempotente.",
                "step_4_ui_integration": "Integrar el componente en el Canvas / HUD de Alberth mediante WebSockets.",
            },
            "suggested_endpoints": [
                f"/api/{target_name.lower().replace(' ', '_')}/execute",
                f"/api/{target_name.lower().replace(' ', '_')}/status"
            ],
            "template_code": f"""# ── Módulo Recreado Limpio: {target_name} ─────────────────────
# Generado por Alberth REA Engine (Clean-Room Standard)
from pydantic import BaseModel
from typing import Dict, Any, Optional

class {target_name.replace(' ', '')}Request(BaseModel):
    action: str = "default"
    payload: Dict[str, Any] = {{}}

class {target_name.replace(' ', '')}Engine:
    @staticmethod
    def execute(req: {target_name.replace(' ', '')}Request) -> Dict[str, Any]:
        # Implementación nativa desacoplada
        return {{
            "status": "success",
            "feature": "{target_name}",
            "intent": "{feature_intent}",
            "result": "Ejecución conforme al contrato funcional limpio."
        }}
"""
        }

        # Guardar blueprint
        bp_file = REA_REPORTS_DIR / f"{spec_id}.json"
        try:
            bp_file.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
            spec["blueprint_path"] = str(bp_file)
        except Exception:
            pass

        return spec


# Instancia singleton para uso rápido
rea_engine = AlberthREAEngine()

if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"🔬 Ejecutando Alberth REA Engine sobre: {arg}")
    res = rea_engine.inspect_code_architecture(arg)
    print(json.dumps(res, indent=2, ensure_ascii=False))
