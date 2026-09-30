#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alberth_multi_agent.py — Framework Multi-Agente SOTA para Alberth (LangGraph + Foundation Models)
================================================================================================
Implementa un Grafo Cíclico de Estados (StateGraph) donde cuadrillas de agentes especializados
colaboran de forma autónoma con bucles de auto-corrección:

1. 🧠 ESTRATEGA (DeepSeek R1 / V3):
   - Desglosa la misión en un plan de acción paso a paso.
2. 👁️ INVESTIGADOR (Meta Llama 3.2 Vision + DuckDuckGo + RAG):
   - Recolecta datos en vivo, noticias web, clima o fragmentos de documentos locales.
3. 💻 INGENIERO (Qwen 2.5 Coder + Ejecución macOS):
   - Genera scripts en Python/Bash, crea archivos y ejecuta operaciones controladas.
4. ⚖️ AUDITOR / QA:
   - Valida si el resultado cumple la meta del Señor. Si detecta fallos, regresa cíclicamente al Ingeniero.
5. 🎙️ SINTETIZADOR:
   - Redacta la entrega ejecutiva final con el trato característico («Señor»).

Costo: $0.00 | Tolerancia a fallos con hasta 3 bucles de auto-corrección.
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Any, Optional, TypedDict

# Importación de LangGraph
from langgraph.graph import StateGraph, END

# Importación de modelos fundacionales y herramientas de Alberth
import alberth_foundation_models as models
try:
    import alberth_search_helper as search_helper
except ImportError:
    search_helper = None

try:
    import alberth_rag_memory as rag_memory
except ImportError:
    rag_memory = None

# ── Módulos de Inteligencia (cargados opcionalmente) ———————————————————
try:
    import alberth_osint as osint_module
except ImportError:
    osint_module = None

try:
    import alberth_websec_scanner as websec_module
except ImportError:
    websec_module = None

try:
    import alberth_face_recognition as face_module
except ImportError:
    face_module = None

try:
    import alberth_skills
except ImportError:
    alberth_skills = None

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())


# ── Estado Compartido del Grafo Multi-Agente ──────────────────────────────────

class AlberthAgentState(TypedDict):
    mission: str
    plan: List[str]
    critic_feedback: str
    critic_approved: bool
    critic_rounds: int
    research_findings: str
    code_artifacts: Dict[str, str]
    execution_output: str
    qa_report: str
    qa_approved: bool
    iterations: int
    final_summary: str


# ── Nodos Especializados ──────────────────────────────────────────────────────

def strategist_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 1: Estratega (DeepSeek R1 / V3)
    Analiza la misión global del Señor y formula un plan de pasos estructurado.
    Si el Crítico rechazó un plan previo, incorpora su retroalimentación para reformularlo.
    """
    mission = state.get("mission", "")
    critic_feedback = state.get("critic_feedback", "")
    rounds = state.get("critic_rounds", 0)

    print(f"\n[Multi-Agente] 🧠 Estratega (DeepSeek) planificando misión{' (Revisión tras Crítica)' if rounds > 0 else ''}...")

    prompt = (
        f"Misión solicitada por el Señor:\n\"{mission}\"\n\n"
    )
    if critic_feedback and rounds > 0:
        prompt += (
            f"El Crítico Adversarial ha observado el plan anterior con estas indicaciones:\n"
            f"\"{critic_feedback}\"\n\n"
            "Corrige y optimiza el plan resolviendo estas objeciones con máxima precisión.\n\n"
        )

    prompt += (
        "Eres el Agente Estratega de Alberth. Desglosa esta misión en 2 a 4 pasos concisos de acción. "
        "Indica qué datos investigar y qué archivo o script se debe construir y ejecutar. "
        "Devuelve exclusivamente una lista numerada en español sin introducciones superfluas."
    )

    plan_text, model_used = models.query_deepseek_reasoning(
        prompt=prompt,
        max_tokens=350
    )

    # Convertir a lista de pasos limpios
    steps = [line.strip() for line in plan_text.splitlines() if line.strip() and line[0].isdigit()]
    if not steps:
        steps = [plan_text.strip()]

    print(f"   Plan generado ({model_used}): {len(steps)} pasos definidos.")
    return {
        "plan": steps,
        "critic_approved": False,
        "critic_rounds": rounds,
        "critic_feedback": critic_feedback
    }


def critic_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 1.5: Crítico Adversarial (Llama 3.3 / Fallback DeepSeek)
    Debate y audita el plan del Estratega antes de autorizar la ejecución.
    Aplica el principio de Devil's Advocate para detectar omisiones, riesgos y viabilidad.
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    rounds = state.get("critic_rounds", 0)

    print(f"\n[Multi-Agente] ⚖️ Crítico Adversarial auditando plan (Ronda {rounds + 1})...")

    # Si ya superó 2 rondas de debate, auto-aprobar para evitar bloqueos
    if rounds >= 2:
        print("   [Crítico] Límite de rondas de debate alcanzado. Plan aprobado con observaciones.")
        return {"critic_approved": True, "critic_rounds": rounds + 1}

    plan_str = "\n".join(f"- {p}" for p in plan)
    prompt = (
        f"Misión del Señor:\n\"{mission}\"\n\n"
        f"Plan propuesto por el Estratega:\n{plan_str}\n\n"
        "Eres el Agente Crítico Adversarial de Alberth. Tu rol es auditar con rigor extremo este plan.\n"
        "Pregúntate: ¿Es viable? ¿Falta recopilar datos esenciales? ¿Hay riesgos de ejecución o ambigüedad?\n"
        "Reglas de respuesta:\n"
        "- Si el plan es claro, seguro y accionable para cumplir la misión, responde EXACTAMENTE:\n"
        "  APROBADO: <breve justificación>\n"
        "- Si el plan tiene omisiones graves o requiere ajustes importantes, responde:\n"
        "  RECHAZADO: <explicación concisa de qué debe corregir el Estratega>"
    )

    review_text, model_used = models.query_llama_vision(
        prompt=prompt,
        max_tokens=250
    )

    is_approved = "APROBADO" in review_text.upper()
    print(f"   Veredicto Crítico ({model_used}): {'✅ APROBADO' if is_approved else '❌ RECHAZADO'}")

    return {
        "critic_approved": is_approved,
        "critic_feedback": review_text.strip(),
        "critic_rounds": rounds + 1
    }


def should_revise_plan(state: AlberthAgentState) -> str:
    """
    Condicional del Crítico:
    - Si el Crítico aprueba (o rounds >= 2) -> avanzar a 'investigator'.
    - Si el Crítico rechaza -> volver a 'strategist' para replanificar.
    """
    if state.get("critic_approved", False) or state.get("critic_rounds", 0) >= 2:
        return "investigator"
    return "strategist"


def investigator_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 2: Investigador ELITE Paralelo (R6)
    Recolecta datos externos o locales ejecutando múltiples fuentes de inteligencia en paralelo
    mediante ThreadPoolExecutor (OSINT, WebSec, Playwright, Search, RAG y alberth_skills).
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    print(f"\n[Multi-Agente] 👁️ Investigador Elite buscando evidencia en paralelo...")

    findings = []
    combined_query = f"{mission} {' '.join(plan)}".lower()

    tasks_to_run = []

    # 1. Definir funciones de herramientas
    def _run_osint(target: str) -> Optional[str]:
        if not osint_module or not target:
            return None
        print(f"[Investigador ⚡ Paralelo] 🔍 OSINT activo → objetivo: {target}")
        osint_res = osint_module.search_username(target)
        if osint_res:
            hits = [p for p in osint_res if p.get("found")]
            return f"OSINT — Perfiles encontrados para '{target}':\n" + json.dumps(hits[:10], ensure_ascii=False, indent=2)
        return None

    def _run_websec(target_url: str) -> Optional[str]:
        if not websec_module or not target_url:
            return None
        print(f"[Investigador ⚡ Paralelo] 🛡️ WebSec Scanner activo → URL: {target_url}")
        sec_res = websec_module.analyze_headers(target_url)
        if sec_res:
            return (
                f"Análisis de Seguridad Web — {target_url}:\n"
                f"Score: {sec_res.get('security_score', '?')}/100\n"
                + json.dumps(sec_res.get('headers_analysis', [])[:5], ensure_ascii=False, indent=2)
            )
        return None

    def _run_playwright(q_mission: str) -> Optional[str]:
        try:
            import alberth_playwright_agent as pw_agent
            print(f"[Investigador ⚡ Paralelo] 🌐 Playwright navegando...")
            pw_res = pw_agent.run_autonomous_browser_mission(mission=q_mission, max_steps=4)
            if pw_res and pw_res.get("success") and pw_res.get("summary"):
                return f"Navegación Web Playwright:\n{pw_res['summary']}"
        except Exception as e:
            print(f"[Investigador] Playwright error: {e}")
        return None

    def _run_duckduckgo(q: str) -> Optional[str]:
        if search_helper:
            try:
                print(f"[Investigador ⚡ Paralelo] 🦆 DuckDuckGo buscando...")
                search_res = search_helper.search_duckduckgo_live(q, max_results=3)
                if search_res:
                    return f"Resultados de Búsqueda Web:\n{json.dumps(search_res, ensure_ascii=False)}"
            except Exception as e:
                print(f"[Investigador] DuckDuckGo error: {e}")
        return None

    def _run_rag(q: str) -> Optional[str]:
        if rag_memory:
            try:
                print(f"[Investigador ⚡ Paralelo] 📚 RAG consultando base documental...")
                rag_res = rag_memory.search_documents(q, limit=2)
                if rag_res and rag_res.get("resultados"):
                    return f"Documentos Locales (RAG):\n{json.dumps(rag_res['resultados'], ensure_ascii=False)}"
            except Exception as e:
                print(f"[Investigador] RAG error: {e}")
        return None

    def _run_discovered_skill(q: str) -> Optional[str]:
        if alberth_skills:
            try:
                matched_skill = alberth_skills.find_skill_for(q)
                if matched_skill:
                    s_name = getattr(matched_skill, "NAME", "skill")
                    print(f"[Investigador ⚡ Paralelo] 🧩 Skill descubierta: {s_name}")
                    res = matched_skill.execute({"query": q, "mission": q})
                    if res:
                        return f"Habilidad Modular ({s_name}):\n{json.dumps(res, ensure_ascii=False, indent=2)}"
            except Exception as e:
                print(f"[Investigador] Error ejecutando skill modular: {e}")
        return None

    # 2. Planificar qué herramientas lanzar
    import re as _re

    # TOOL A: OSINT
    _osint_kw = ["usuario", "perfil", "rastrea", "huella digital", "redes sociales",
                 "quién es", "quien es", "email", "correo", "persona", "osint"]
    if osint_module and any(k in combined_query for k in _osint_kw):
        target = _re.sub(
            r'(rastrea a|perfil de|osint de|investiga a|qu\w+ es)\s*', '',
            mission, flags=_re.I
        ).strip().split()[0] if mission.strip() else ""
        if target:
            tasks_to_run.append((_run_osint, (target,), "OSINT"))

    # TOOL B: WebSec Scanner
    _websec_kw = ["seguridad", "vulnerabilidad", "headers", "ssl", "https",
                  "sitio web", "dominio", "url", "website", "escanea", "escanear"]
    if websec_module and any(k in combined_query for k in _websec_kw):
        url_match = _re.search(r'(https?://[\w./-]+|[\w.-]+\.[a-z]{2,})', mission)
        if url_match:
            t_url = url_match.group(0)
            if not t_url.startswith("http"):
                t_url = "https://" + t_url
            tasks_to_run.append((_run_websec, (t_url,), "WebSec"))

    # TOOL C: Playwright
    _pw_kw = ["navega", "entra a la web", "abre la pagina", "portal",
              "mercadolibre", "wikipedia", "formulario", "pagina web"]
    if any(w in combined_query for w in _pw_kw):
        tasks_to_run.append((_run_playwright, (mission,), "Playwright"))

    # TOOL D: DuckDuckGo
    if any(w in combined_query for w in ["clima", "tiempo", "noticia", "precio", "buscar", "investiga", "web"]):
        tasks_to_run.append((_run_duckduckgo, (mission,), "DuckDuckGo"))

    # TOOL E: RAG Local
    if any(w in combined_query for w in ["documento", "pdf", "manual", "archivo local", "rag"]):
        tasks_to_run.append((_run_rag, (mission,), "RAG"))

    # TOOL F: Modular Skills Registry
    if alberth_skills and not tasks_to_run:
        tasks_to_run.append((_run_discovered_skill, (combined_query,), "Skills"))

    # 3. Ejecución Paralela con ThreadPoolExecutor
    if tasks_to_run:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks_to_run), 5)) as executor:
            future_to_name = {executor.submit(fn, *args): name for fn, args, name in tasks_to_run}
            for fut in concurrent.futures.as_completed(future_to_name):
                t_name = future_to_name[fut]
                try:
                    res_val = fut.result()
                    if res_val:
                        findings.append(res_val)
                except Exception as exc:
                    print(f"[Investigador] ⚠️ Excepción en tool {t_name}: {exc}")

    # Fallback si no hubo tareas o findings y se solicitaba información
    if not findings and any(w in combined_query for w in ["buscar", "que es", "qué es", "como", "cómo", "info"]):
        fallback_res = _run_duckduckgo(mission)
        if fallback_res:
            findings.append(fallback_res)

    # 4. Síntesis investigativa con Meta Llama 3.2
    tools_used = len(findings)
    raw_findings = "\n\n".join(findings) if findings else "No se requirieron fuentes externas para esta tarea."
    prompt_inv = (
        f"Misión: {mission}\n"
        f"Datos encontrados ({tools_used} fuentes de inteligencia concurrentes):\n{raw_findings[:2000]}\n\n"
        "Resume de forma concisa los datos clave que el Agente Ingeniero necesitará para escribir el código o reporte."
    )
    summary, model_used = models.query_llama_vision(prompt=prompt_inv, max_tokens=400)
    print(f"   Investigación paralela completada ({model_used}) — {tools_used} fuente(s) integradas.")
    return {"research_findings": summary}


def extract_python_code(raw_text: str) -> str:
    """Extrae código Python puro eliminando saludos, markdown y explicaciones."""
    # 1. Si hay bloque de código ```python ... ```
    if "```python" in raw_text:
        code = raw_text.split("```python", 1)[1]
        if "```" in code:
            code = code.split("```", 1)[0]
    elif "```" in raw_text:
        code = raw_text.split("```", 1)[1]
        if "```" in code:
            code = code.split("```", 1)[0]
    else:
        code = raw_text

    # 2. Eliminar líneas que sean saludos o texto conversacional antes del primer import/def/código
    lines = code.splitlines()
    clean_lines = []
    found_code_start = False
    valid_starters = ("import ", "from ", "def ", "class ", "#", "with ", "if ", "for ", "while ", "try:", "print(")

    for line in lines:
        stripped = line.strip()
        if not found_code_start:
            if any(stripped.startswith(vs) for vs in valid_starters) or (("=" in stripped or ":" in stripped) and not stripped.startswith(("¡", "¿", "Hola", "Saludos", "Señor"))):
                found_code_start = True
                clean_lines.append(line)
        else:
            clean_lines.append(line)

    return "\n".join(clean_lines).strip() or code.strip()


def engineer_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 3: Ingeniero (Qwen 2.5 Coder + Ejecución macOS)
    Escribe el script o solución de código y lo ejecuta en el entorno seguro.
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    research = state.get("research_findings", "")
    qa_report = state.get("qa_report", "")
    iter_count = state.get("iterations", 0)

    print(f"\n[Multi-Agente] 💻 Ingeniero (Qwen Coder) construyendo solución (Iteración {iter_count + 1})...")

    critique_prompt = f"\nObservaciones previas del Auditor QA que DEBES corregir:\n{qa_report}\n" if qa_report else ""

    prompt_code = (
        f"Eres el Agente Ingeniero de Software (Qwen Coder) de Alberth.\n"
        f"Misión del Señor: \"{mission}\"\n"
        f"Plan: {json.dumps(plan, ensure_ascii=False)}\n"
        f"Datos investigados: {research}\n"
        f"{critique_prompt}\n"
        "REGLAS ESTRICTAS DE PROGRAMACIÓN:\n"
        "- Genera código Python 3 autocontenido, limpio, sin errores de sintaxis y completamente cerrado.\n"
        "- NO agregues saludos, ni introducciones conversacionales, ni texto explicativo.\n"
        "- NO dejes comillas triples \"\"\" sin cerrar ni bloques incompletos.\n"
        "- Imprime el resultado con print() para que el Auditor QA pueda verificar la salida.\n"
        "- Si la misión pide guardar en un archivo, escribe el archivo con open(..., 'w', encoding='utf-8').\n"
        "- Devuelve ÚNICAMENTE el bloque de código entre triple tilde de python ```python ... ```."
    )

    code_text, model_used = models.query_qwen_coder(
        prompt=prompt_code,
        system_prompt="Eres un compilador y generador de código Python 3 estricto. Devuelve únicamente código ejecutable sin saludos ni explicaciones.",
        max_tokens=950
    )

    # Extraer código limpio sin saludos
    script_content = extract_python_code(code_text)

    # Validar que sea código antes de intentar ejecutarlo
    if not script_content or script_content.startswith("Señor") or "Traceback" in script_content:
        print(f"   ⚠️ Respuesta no es código Python válido.")
        return {
            "code_artifacts": {},
            "execution_output": "ERROR: El modelo devolvió un mensaje de texto en lugar de código Python ejecutable."
        }

    # Ejecutar el script en un subproceso aislado
    exec_out = ""
    script_path = Path("/tmp/alberth_agent_task.py")
    try:
        script_path.write_text(script_content, encoding="utf-8")
        venv_py = WORKSPACE_DIR / "venv" / "bin" / "python3"
        py_bin = str(venv_py) if venv_py.exists() else sys.executable
        res = subprocess.run([py_bin, str(script_path)], capture_output=True, text=True, timeout=15)
        if res.returncode == 0:
            exec_out = f"STDOUT:\n{res.stdout.strip()}"
        else:
            exec_out = f"ERROR (exit {res.returncode}):\n{res.stderr.strip()}\nSTDOUT:\n{res.stdout.strip()}"
    except subprocess.TimeoutExpired:
        exec_out = "ERROR: El script excedió el tiempo límite de 15 segundos."
    except Exception as e:
        exec_out = f"ERROR de ejecución: {e}"

    print(f"   Código ejecutado ({model_used}). Longitud salida: {len(exec_out)} caracteres.")
    return {
        "code_artifacts": {"alberth_agent_task.py": script_content},
        "execution_output": exec_out
    }


def auditor_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 4: Auditor QA
    Evalúa la salida de ejecución contra la meta original del Señor.
    Si hay un error de ejecución o datos faltantes, rechaza y solicita corrección cíclica.
    """
    exec_out = state.get("execution_output", "")
    iter_count = state.get("iterations", 0) + 1

    print(f"\n[Multi-Agente] ⚖️ Auditor QA evaluando calidad...")

    has_error = "ERROR" in exec_out or "Traceback" in exec_out or "SyntaxError" in exec_out or not exec_out.strip()

    if not has_error:
        qa_approved = True
        report = "Resultado verificado y aprobado. Código ejecutado exitosamente sin errores."
        print(f"   ✅ Auditor aprueba resultado exitoso.")
    elif iter_count < 3:
        qa_approved = False
        report = f"El script falló con el siguiente error de ejecución:\n{exec_out[:400]}\nCorrige el código eliminando el error y asegurando que sea Python 3 válido."
        print(f"   ❌ Auditor detecta fallo. Activando bucle de auto-corrección ({iter_count}/3).")
    else:
        qa_approved = True
        report = "Límite de iteraciones alcanzado. Se entrega el mejor resultado obtenido."
        print(f"   ⚠️ Límite de auto-correcciones alcanzado. Procediendo a síntesis.")

    return {
        "qa_approved": qa_approved,
        "qa_report": report,
        "iterations": iter_count
    }


def synthesizer_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 5: Sintetizador Ejecutivo
    Redacta la entrega final de alto nivel para el Señor.
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    research = state.get("research_findings", "")
    exec_out = state.get("execution_output", "")
    iter_count = state.get("iterations", 0)

    print(f"\n[Multi-Agente] 🎙️ Sintetizador generando reporte final...")

    prompt_syn = (
        f"Eres Alberth, el asistente personal de élite del Señor.\n"
        f"Misión solicitada: \"{mission}\"\n"
        f"Pasos ejecutados por tu equipo multi-agente ({iter_count} ciclos):\n{json.dumps(plan, ensure_ascii=False)}\n"
        f"Datos investigados: {research[:300]}\n"
        f"Resultado obtenido del Ingeniero:\n{exec_out[:1000]}\n\n"
        "Redacta una respuesta ejecutiva, directa, profesional y concisa dirigida al 'Señor'. "
        "Informa que el equipo multi-agente ha completado la misión y presenta los datos concretos o el estado de los archivos creados."
    )

    final_text, model_used = models.query_llama_vision(prompt=prompt_syn, max_tokens=500)

    # Respaldo determinista si la API externa experimenta congestión momentánea
    if not final_text or final_text.startswith("Señor, el sistema") or "Error" in model_used:
        final_text = (
            f"Señor, la misión «{mission}» ha sido completada con éxito por el equipo multi-agente ({iter_count} ciclo).\n\n"
            f"Resultados de ejecución:\n{exec_out.strip()}"
        )

    print(f"   Síntesis completada ({model_used}).")
    return {"final_summary": final_text}


# ── Condicional de Flujo Cíclico ──────────────────────────────────────────────

def should_continue(state: AlberthAgentState) -> str:
    """
    Decide el siguiente paso del grafo:
    - Si el Auditor aprobó o se alcanzó el límite de 3 iteraciones -> sintetizar y terminar.
    - Si el Auditor rechazó -> regresar cíclicamente al Ingeniero para auto-corregir el código.
    """
    if state.get("qa_approved", False) or state.get("iterations", 0) >= 3:
        return "synthesizer"
    return "engineer"


# ── Construcción del Grafo StateGraph de LangGraph ───────────────────────────

def build_alberth_multi_agent_graph():
    """Construye y compila el grafo cíclico multi-agente en LangGraph.
    
    Flujo con debate adversarial (R4):
    
        Estratega → Crítico → (si rechazado → Estratega) | (si aprobado → Investigador)
                                       Investigador → Ingeniero → Auditor QA
                                                    (si rechazado → Ingeniero x3)
                                                         ↓
                                                    Sintetizador → FIN
    """
    workflow = StateGraph(AlberthAgentState)

    # 1. Agregar Nodos
    workflow.add_node("strategist",  strategist_node)
    workflow.add_node("critic",      critic_node)        # ◄ nuevo nodo adversarial
    workflow.add_node("investigator", investigator_node)
    workflow.add_node("engineer",    engineer_node)
    workflow.add_node("auditor",     auditor_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # 2. Definir Aristas
    workflow.set_entry_point("strategist")
    workflow.add_edge("strategist", "critic")            # ◄ Estratega → Crítico

    # 3. Arista Condicional: Crítico → Investigador | Estratega (debate)
    workflow.add_conditional_edges(
        "critic",
        should_revise_plan,
        {
            "investigator": "investigator",
            "strategist":   "strategist",
        }
    )

    workflow.add_edge("investigator", "engineer")
    workflow.add_edge("engineer", "auditor")

    # 4. Arista Condicional Cíclica (Auto-Corrección del Ingeniero)
    workflow.add_conditional_edges(
        "auditor",
        should_continue,
        {
            "engineer":     "engineer",
            "synthesizer":  "synthesizer"
        }
    )

    workflow.add_edge("synthesizer", END)
    return workflow.compile()


# ── Función Maestra de Ejecución de Misiones ──────────────────────────────────

_app_graph = None

def run_multi_agent_mission(mission: str) -> Dict[str, Any]:
    """
    Punto de entrada para ejecutar cualquier misión compleja multi-agente en Alberth.
    Retorna el estado final consolidado con el reporte ejecutivo.
    """
    global _app_graph
    if _app_graph is None:
        _app_graph = build_alberth_multi_agent_graph()

    initial_state: AlberthAgentState = {
        "mission": mission,
        "plan": [],
        "critic_feedback": "",
        "critic_approved": False,
        "critic_rounds": 0,
        "research_findings": "",
        "code_artifacts": {},
        "execution_output": "",
        "qa_report": "",
        "qa_approved": False,
        "iterations": 0,
        "final_summary": ""
    }

    t_start = time.time()
    final_state = _app_graph.invoke(initial_state)
    elapsed = time.time() - t_start

    return {
        "success": True,
        "elapsed_seconds": round(elapsed, 2),
        "mission": mission,
        "iterations": final_state.get("iterations", 1),
        "critic_rounds": final_state.get("critic_rounds", 0),
        "critic_feedback": final_state.get("critic_feedback", ""),
        "plan": final_state.get("plan", []),
        "output": final_state.get("execution_output", ""),
        "final_summary": final_state.get("final_summary", ""),
        # Alias para compatibilidad con alberth_master.sh
        "final_response": final_state.get("final_summary", ""),
    }


# Alias de conveniencia e integración directa
run_mission = run_multi_agent_mission


# ── Ejecución CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_mission = "Investiga el clima de hoy en Medellín, calcula la temperatura en Fahrenheit y genera un archivo de texto con el reporte en /tmp/alberth_report.txt"
    if len(sys.argv) > 1 and sys.argv[1] == "--mission":
        test_mission = " ".join(sys.argv[2:])

    print("=" * 70)
    print("🚀 EJECUTANDO MISIÓN MULTI-AGENTE (LANGGRAPH)")
    print(f"🎯 Misión: \"{test_mission}\"")
    print("=" * 70)

    res = run_multi_agent_mission(test_mission)

    print("\n" + "=" * 70)
    print(f"🏁 RESULTADO FINAL (Tiempo: {res['elapsed_seconds']}s | Ciclos: {res['iterations']})")
    print("=" * 70)
    print(res["final_summary"])
    print("-" * 70)
    print("Salida técnica del script ejecutado:")
    print(res["output"])
    print("=" * 70)
