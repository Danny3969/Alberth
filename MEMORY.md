# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v3.0)
```text
/Users/digitalspace/.openclaw/workspace/
├── agents/
│   ├── orquestador/    → Agente Orquestador (Core Master) [Nvidia NIM GLM-5.1 / DeepSeek]
│   ├── codigo/         → Agente de Desarrollo & Refactor [GitHub CLI / Shell]
│   ├── vision/         → Agente Multimodal & Visión [Gemini 2.5 Flash]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua
├── alberth_qa_watcher.py    → Demonio de supervisión proactiva (filtro 2 horas)
├── alberth_tts_premium.py   → Síntesis de voz cinematográfica (edge-tts / afplay)
├── alberth_github_helper.py → Helper de integración con GitHub CLI (`gh`)
├── alberth_memory_sync.py   → Sincronizador de memoria híbrida
├── ecosystem.config.js      → Orquestador de procesos PM2
└── MEMORY.md                → Memoria técnica y continuativa del proyecto
```

---

## ⚙️ Configuración y Puertos Activos
- **Panel Web Interactive:** `http://localhost:8080` (FastAPI / WebSockets)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Variables & Credenciales:** Protegidas en `~/.openclaw/.env` (`chmod 600`)

---

## 👤 Perfil del Usuario y Asistente
- **Usuario:** Señor Daniel Jaya (Guayaquil, GMT-5)
- **Asistente:** Alberth 🕶️ *(Mano derecha analítica, directa y no aduladora)*
- **Modelos Principales:**
  - Inferencia de Texto: `nvidia/z-ai/glm-5.1` / `fcm-nvidia/deepseek-ai/deepseek-v4-flash`
  - Inferencia Multimodal / Visión: `openrouter/google/gemini-2.5-flash`
  - Transcripción STT: `groq/whisper-large-v3-turbo`
  - Síntesis de Voz TTS: `es-MX-JorgeNeural` (Edge-TTS)

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Transformación Alberth NEXUS 100% Completada)
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
