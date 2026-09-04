# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04 17:25 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v3.0)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador (Core Master) [Nvidia NIM GLM-5.1 / DeepSeek]
│   ├── codigo/         → Agente de Desarrollo & Refactor [GitHub CLI / Shell]
│   ├── vision/         → Agente Multimodal & Visión [Gemini 2.5 Flash]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web UI interactivo (HTML5/CSS3/WebSockets)
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua con WebRTC VAD
├── alberth_qa_watcher.py    → Demonio de supervisión proactiva (filtro 2 horas)
├── alberth_reminders_daemon.py → Demonio de recordatorios sobre SQLite
├── alberth_tts_premium.py   → Síntesis de voz cinematográfica (edge-tts / afplay)
├── alberth_screen_copilot.py→ Copiloto visual de pantalla asistido por Gemini
├── alberth_github_helper.py → Helper de integración con GitHub CLI (`gh`)
├── alberth_memory_sync.py   → Sincronizador de memoria híbrida
├── ecosystem.config.js      → Orquestador de procesos PM2 portable
└── MEMORY.md                → Memoria técnica y continuativa del proyecto
```

---

## ⚙️ Configuración y Puertos Activos
- **Panel Web Interactive:** `http://localhost:8080` (FastAPI / WebSockets)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Túnel Seguro Cloudflare:** [`alberth_tunnel.sh`](file:///Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/alberth_tunnel.sh)
- **Variables & Credenciales:** Protegidas en `~/.openclaw/.env` (`chmod 600`)

---

## 👤 Perfil del Usuario y Asistente
- **Usuario:** Señor Daniel Jaya (Guayaquil, GMT-5) — CEO Novasyscom
- **Asistente:** Alberth 🕶️ *(Mano derecha analítica, directa y no aduladora)*
- **Modelos Principales:**
  - Inferencia de Texto: `nvidia/z-ai/glm-5.1` / `fcm-nvidia/deepseek-ai/deepseek-v4-flash`
  - Inferencia Multimodal / Visión: `openrouter/google/gemini-2.5-flash`
  - Transcripción STT: `groq/whisper-large-v3-turbo`
  - Síntesis de Voz TTS: `es-MX-JorgeNeural` (Edge-TTS)

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Corrección de Portabilidad & Saneamiento Operativo)
- **Portabilidad Total de Rutas:** Se eliminaron las rutas fijas (`/Users/digitalspace/...`) en todos los demonios y scripts base (`alberth_reminders_daemon.py`, `alberth_voice_server.py`, `alberth_qa_watcher.py`, `alberth_memory_sync.py`, `alberth_screen_copilot.py`, `alberth_tunnel.sh`). Ahora resuelven dinámicamente según `OPENCLAW_WORKSPACE`, `ALBERTH_WORKSPACE` o ruta de ejecución local.
- **Configuración PM2 Portable:** `ecosystem.config.js` adaptado con `__dirname` y fallback inteligente al intérprete `python3` del sistema.
- **Resolución Problemas Operativos:**
  - **Firma DAI:** Diagnóstico completado. El error en rojo no es del certificado digital sino de la estructura/metadatos del archivo PDF generado. Protocolo de solución establecido vía re-exportación limpia (Vista Previa / Ghostscript).
  - **Reportes Agrícolas (Miguel vs. Israel):** Esquema de validación cruzada estructurado para garantizar consistencia en racimos y cajas Woodfarm/Bonanza.
  - **Proceso "Program":** Hoja de ruta para migración automática de datos eliminando la intervención manual.
- **Sincronización:** Verificación y actualización de memoria activa en GitHub.

### 2026-09-04 (Lanzamiento Inicial Alberth NEXUS)
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
