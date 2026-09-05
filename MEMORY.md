# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04 21:18 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v3.1)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador Core [Nvidia NIM GLM-5.1]
│   ├── codigo/         → Agente de Desarrollo & Refactor [Nvidia NIM Qwen2.5-Coder-32B]
│   ├── vision/         → Agente Multimodal & Visión [Gemini 2.5 Flash]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web UI interactivo (HTML5/CSS3/WebSockets)
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua con VAD
├── alberth_qa_watcher.py    → Demonio de supervisión proactiva (filtro 2 horas)
├── alberth_reminders_daemon.py → Demonio de recordatorios sobre SQLite
├── alberth_tts_premium.py   → Síntesis de voz cinematográfica (edge-tts / afplay)
├── alberth_screen_copilot.py→ Copiloto visual de pantalla asistido por Gemini
├── alberth_github_helper.py → Helper de integración con GitHub CLI (`gh`)
├── alberth_memory_sync.py   → Sincronizador de memoria híbrida
├── alberth_learn.py         → CLI de aprendizaje continuo e in-context feedback
├── ecosystem.config.js      → Orquestador de procesos PM2 portable
└── MEMORY.md                → Memoria técnica y continuativa del proyecto
```

---

## ⚙️ Configuración y Puertos Activos
- **Panel Web Interactive:** `http://localhost:8080` (FastAPI / WebSockets)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Túnel Seguro Cloudflare:** `alberth_tunnel.sh`
- **Audit Logs:** `~/.openclaw/workspace/logs/audit_logs.jsonl`
- **Modo de Contexto Activo:** `~/.openclaw/workspace/.context_mode` (`laboral` | `personal`)

---

## 🗂️ SEPARACIÓN DE CONTEXTOS (Personal / Laboral)

### 🔵 Contexto Personal (Namespace: `user_personal`)
- **Enfoque:** Hábitos, salud, música (Echo Music / YT Music Premium), recordatorios de hogar, compras.
- **Activación:** Verbal (*"Alberth, modo personal"*) o CLI (`python3 alberth_memory.py --set-mode personal`).

### 🟠 Contexto Laboral (Namespace: `user_laboral`)
- **Enfoque:** Alberth NEXUS, Drivo, VALEX, Novasyscom, deploys, repositorios GitHub, firmas DAI, auditorías.
- **Activación:** Verbal (*"Alberth, modo laboral"*) o CLI (`python3 alberth_memory.py --set-mode laboral`).

---

## 👤 Perfil del Usuario y Asistente
- **Usuario:** Señor Daniel Jaya (Guayaquil, GMT-5) — CEO Novasyscom
- **Asistente:** Alberth 🕶️ *(Mano derecha analítica, directa y no aduladora)*
- **Modelos Principales:**
  - Orquestación General: `nvidia/z-ai/glm-5.1`
  - Desarrollo de Código: `nvidia/Qwen/Qwen2.5-Coder-32B-Instruct`
  - Inferencia Multimodal / Visión: `openrouter/google/gemini-2.5-flash`
  - Transcripción STT: `groq/whisper-large-v3-turbo`
  - Síntesis de Voz TTS: `es-MX-JorgeNeural` (Edge-TTS)

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Implementación de Mejoras de Arquitectura & Trazabilidad)
- **Agente de Código Actualizado:** Se cambió el modelo primario de `codigo` en `openclaw.json` a `nvidia/Qwen/Qwen2.5-Coder-32B-Instruct` en Nvidia NIM para máximo rendimiento en desarrollo.
- **Separación de Contextos:** Implementado control de modo `laboral` / `personal` guardado en `.context_mode` y soportado en `alberth_memory.py`.
- **Feedback Loop por Voz & CLI:** Creado `alberth_learn.py` para inyectar correcciones directamente a la memoria sin necesidad de UI web.
- **Auditoría y Trazabilidad:** Implementado registro estructurado JSONL en `logs/audit_logs.jsonl` con seguimiento de agente, query, modo, modelo y latencia.

### 2026-09-04 (Lanzamiento Alberth NEXUS & GitHub Sync)
- **Semana 1:** Instalación del plugin de orquestación Nexus `@houchenyang/nexus` y registro de los 4 agentes especializados (`orquestador`, `codigo`, `vision`, `qa_proactivo`).
- **Semana 2:** Demonio de supervisión proactiva `alberth_qa_watcher.py` con síntesis de voz en tiempo real (`es-MX-JorgeNeural` / `afplay`) y filtro regulador de 2 horas en `qa_state.json`.
- **Semana 3:** Memoria Híbrida activada (`openclaw-mem0` + `active-memory` con `autoRecall` y `autoCapture`), script de sincronización `alberth_memory_sync.py` e integración con GitHub CLI `alberth_github_helper.py`.
- **GitHub:** Inicialización y sincronización con el repositorio oficial [Danny3969/Alberth](https://github.com/Danny3969/Alberth).

---

## 🚀 Guía de Continuidad desde Otros Equipos

Para conectarte o continuar este proyecto desde otra computadora:

1. **Clonar el Repositorio:**
   ```bash
   git clone https://github.com/Danny3969/Alberth.git
   ```
2. **Revisar MEMORY.md:**
   Consultar este archivo para saber el estado exacto de las configuraciones y daemons.
3. **Sincronizar y Subir Cambios:**
   ```bash
   git add .
   git commit -m "feat: actualización de estado"
   git push origin main
   ```
