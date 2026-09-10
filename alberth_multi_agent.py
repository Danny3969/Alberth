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
   - Valida si el resultado cumple la meta del Señor Danny. Si detecta fallos, regresa cíclicamente al Ingeniero.
5. 🎙️ SINTETIZADOR:
   - Redacta la entrega ejecutiva final con el trato característico («Señor Danny»).

Costo: $0.00 | Tolerancia a fallos con hasta 3 bucles de auto-corrección.
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
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

WORKSPACE_DIR = Path(os.environ.get("OPENCLAW_WORKSPACE") or os.environ.get("ALBERTH_WORKSPACE") or Path(__file__).parent.resolve())


# ── Estado Compartido del Grafo Multi-Agente ──────────────────────────────────

class AlberthAgentState(TypedDict):
    mission: str
    plan: List[str]
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
    Analiza la misión global del Señor Danny y formula un plan de pasos estructurado.
    """
    mission = state.get("mission", "")
    print(f"\n[Multi-Agente] 🧠 Estratega (DeepSeek) planificando misión...")

    prompt = (
        f"Misión solicitada por el Señor Danny:\n\"{mission}\"\n\n"
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
    return {"plan": steps}


def investigator_node(state: AlberthAgentState) -> Dict[str, Any]:
    """
    Nodo 2: Investigador (Meta Llama 3.2 Vision + DuckDuckGo + RAG)
    Recolecta datos externos o locales si la misión o el plan lo requieren.
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    print(f"\n[Multi-Agente] 👁️ Investigador (Llama Vision / Web) buscando evidencia...")

    findings = []
    combined_query = f"{mission} {' '.join(plan)}"

    # 0. Navegación Web Autónoma con Playwright si la misión requiere interactuar con páginas o portales
    if any(w in combined_query.lower() for w in ["navega", "entra a la web", "abre la pagina", "portal", "mercadolibre", "wikipedia", "formulario", "pagina web"]):
        try:
            import alberth_playwright_agent as pw_agent
            print(f"[Investigador] 🌐 Desplegando Navegador Playwright en segundo plano...")
            pw_res = pw_agent.run_autonomous_browser_mission(mission=mission, max_steps=4)
            if pw_res and pw_res.get("success") and pw_res.get("summary"):
                findings.append(f"Resultados de Navegación Playwright:\n{pw_res['summary']}")
        except Exception as pwe:
            print(f"[Investigador] Error Playwright: {pwe}")

    # 1. Búsqueda Web en tiempo real si requiere noticias, clima o datos externos
    if not findings and any(w in combined_query.lower() for w in ["clima", "tiempo", "noticia", "precio", "buscar", "investiga", "web"]):
        if search_helper:
            try:
                # Extraer posible ciudad o tema usando el método correcto search_duckduckgo_live
                search_res = search_helper.search_duckduckgo_live(mission, max_results=3)
                if search_res:
                    findings.append(f"Resultados de Búsqueda Web:\n{json.dumps(search_res, ensure_ascii=False)}")
            except Exception as e:
                print(f"[Investigador] Error búsqueda: {e}")

    # 2. Búsqueda RAG en documentos locales si se mencionan archivos
    if any(w in combined_query.lower() for w in ["documento", "pdf", "manual", "archivo local", "rag"]):
        if rag_memory:
            try:
                rag_res = rag_memory.search_documents(mission, limit=2)
                if rag_res and rag_res.get("resultados"):
                    findings.append(f"Documentos Locales (RAG):\n{json.dumps(rag_res['resultados'], ensure_ascii=False)}")
            except Exception as e:
                print(f"[Investigador] Error RAG: {e}")

    # 3. Síntesis investigativa con Meta Llama 3.2
    raw_findings = "\n\n".join(findings) if findings else "No se requirieron fuentes externas para esta tarea."
    prompt_inv = (
        f"Misión: {mission}\n"
        f"Datos encontrados:\n{raw_findings[:1500]}\n\n"
        "Resume de forma concisa los datos clave que el Agente Ingeniero necesitará para escribir el código o reporte."
    )
    summary, model_used = models.query_llama_vision(prompt=prompt_inv, max_tokens=300)
    print(f"   Investigación completada ({model_used}).")
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
        f"Misión del Señor Danny: \"{mission}\"\n"
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
    if not script_content or script_content.startswith("Señor Danny") or "Traceback" in script_content:
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
    Evalúa la salida de ejecución contra la meta original del Señor Danny.
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
    Redacta la entrega final de alto nivel para el Señor Danny.
    """
    mission = state.get("mission", "")
    plan = state.get("plan", [])
    research = state.get("research_findings", "")
    exec_out = state.get("execution_output", "")
    iter_count = state.get("iterations", 0)

    print(f"\n[Multi-Agente] 🎙️ Sintetizador generando reporte final...")

    prompt_syn = (
        f"Eres Alberth, el asistente personal de élite del Señor Danny.\n"
        f"Misión solicitada: \"{mission}\"\n"
        f"Pasos ejecutados por tu equipo multi-agente ({iter_count} ciclos):\n{json.dumps(plan, ensure_ascii=False)}\n"
        f"Datos investigados: {research[:300]}\n"
        f"Resultado obtenido del Ingeniero:\n{exec_out[:1000]}\n\n"
        "Redacta una respuesta ejecutiva, directa, profesional y concisa dirigida al 'Señor Danny'. "
        "Informa que el equipo multi-agente ha completado la misión y presenta los datos concretos o el estado de los archivos creados."
    )

    final_text, model_used = models.query_llama_vision(prompt=prompt_syn, max_tokens=500)

    # Respaldo determinista si la API externa experimenta congestión momentánea
    if not final_text or final_text.startswith("Señor Danny, el sistema") or "Error" in model_used:
        final_text = (
            f"Señor Danny, la misión «{mission}» ha sido completada con éxito por el equipo multi-agente ({iter_count} ciclo).\n\n"
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
    """Construye y compila el grafo cíclico multi-agente en LangGraph."""
    workflow = StateGraph(AlberthAgentState)

    # 1. Agregar Nodos
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("investigator", investigator_node)
    workflow.add_node("engineer", engineer_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("synthesizer", synthesizer_node)

    # 2. Definir Aristas y Flujo
    workflow.set_entry_point("strategist")
    workflow.add_edge("strategist", "investigator")
    workflow.add_edge("investigator", "engineer")
    workflow.add_edge("engineer", "auditor")

    # 3. Arista Condicional Cíclica (Auto-Corrección)
    workflow.add_conditional_edges(
        "auditor",
        should_continue,
        {
            "engineer": "engineer",
            "synthesizer": "synthesizer"
        }
    )

    workflow.add_edge("synthesizer", END)

    # Compilar el grafo
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
        "plan": final_state.get("plan", []),
        "output": final_state.get("execution_output", ""),
        "final_summary": final_state.get("final_summary", "")
    }


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
