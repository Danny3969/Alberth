# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-07 09:35 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v4.5+ & Antigravity Native SDK)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador Core [Nvidia NIM GLM-5.1]
│   ├── codigo/         → Agente de Desarrollo & Antigravity SDK [Qwen2.5-Coder-32B / Antigravity Agent]
│   ├── vision/         → Agente Multimodal & Reconocimiento Facial [Nvidia NIM / Llama-3.2-Vision / Gemini]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web & Floating Bar UI (HTML5/CSS3/Three.js/WebSockets/PWA)
│   ├── index.html      → Panel Principal HUD + Orbe 3D WebGL (Three.js Audio-Reactive Double-Buffer)
│   ├── floating.html   → Desktop Floating Bar v4.5+ (Context Autocomplete / Focus / QA Chart 7D / Push / DND)
│   └── sw.js           → Service Worker para funcionamiento PWA Offline de la UI
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
├── agente_antigravity_sdk.py → Integración Nativa Antigravity (Capa 2 / Hub Paralelo / Aprendizaje de Patrones)
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets + Live Canvas A2UI + `/floating` (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua con VAD
├── alberth_vision.py        → Cámara On-Demand + Registro de Personas (ej. Danna) + Fast Cosine Embeddings (<500ms)
├── alberth_qa_watcher.py    → Demonio de supervisión proactiva (filtro 2 horas)
├── alberth_reminders_daemon.py → Demonio de recordatorios sobre SQLite
├── alberth_tts_premium.py   → Síntesis de voz cinematográfica (edge-tts / afplay)
├── alberth_screen_copilot.py→ Copiloto visual de pantalla asistido por Gemini
├── alberth_github_helper.py → Helper de integración con GitHub CLI (`gh`)
├── alberth_memory_sync.py   → Sincronizador de memoria híbrida
├── alberth_learn.py         → CLI de aprendizaje continuo e in-context feedback
├── ecosystem.config.js      → Orquestador de procesos PM2 portable
├── SOUL.md                  → Definición estricta de personalidad y comportamiento
└── MEMORY.md                → Memoria técnica y continuativa del proyecto
```

---

## ⚙️ Configuración y Puertos Activos
- **Panel Web HUD:** `http://localhost:8080` (FastAPI / Three.js 3D Orb / WebSockets)
- **Desktop Floating Bar v4.5+:** `http://localhost:8080/floating` (Context Autocomplete + QA 7-Day Chart + Push PWA + Auto-DND)
- **Live Canvas A2UI:** `/api/canvas` (Dynamic Component Drawer & Predictive QA Visualizer)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Skills Registry:** ClawHub Integration Enabled (`https://clawhub.dev/api/v1`)
- **Túnel Seguro Cloudflare:** `alberth_tunnel.sh`
- **Audit Logs:** `logs/audit_logs.jsonl`
- **Modo de Contexto Activo:** `.context_mode` (`laboral` | `personal`)

---

## 🎨 NOVEDADES DE ALBERTH NEXUS v4.5+ & ANTIGRAVITY SDK

1. **Integración Nativa con Antigravity SDK:**
   - Capa de ejecución programática sobre Antigravity (`agente_antigravity_sdk.py`) con delegación de tareas en segundo plano, políticas de seguridad declarativas (`deny`, `allow`, `ask_user`) y registro de sesiones concurrentes.
   - Motor de aprendizaje de patrones de corrección del usuario (`--learn` y `--get-learning`).
2. **Desktop Floating Bar v4.5+ & Auto-DND Inteligente:**
   - Autocompletado sensible al contexto y al horario (laboral vs personal).
   - Control de No Molestar (Auto-DND) sincronizado con calendario y reglas horarias.
3. **Supervisión QA Predictiva a 7 Días:**
   - Gráfico de canvas predictivo con proyección semanal de incidentes, filtros por severidad y exportación visual en formato PNG.
4. **Cámara On-Demand y Reconocimiento Facial:**
   - Identificación biométrica visual con embeddings de coseno en menos de 500 ms (`alberth_vision.py`), permitiendo enrolar y reconocer familiares (ej. Danna).
5. **Compatibilidad Universal Python 3.9+:**
   - Inclusión de `from __future__ import annotations` en el motor de memoria SQLite (`alberth_memory.py`) para evitar incompatibilidades con anotaciones de tipo PEP 604 en sistemas con Python 3.9 o anterior.

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-07 (Sincronización Local, Compatibilidad Python 3.9 & Antigravity SDK)
- **Git Fast-Forward:** Incorporación local de 15 commits desde GitHub con el stack completo de NEXUS v4.5+ y Antigravity SDK.
- **Hotfix de Compatibilidad:** Corrección en `alberth_memory.py` agregando `from __future__ import annotations` para soportar sintaxis `str | None` en Python 3.9.6 local.
- **Portabilidad SDK:** Resolución dinámica de `WORKSPACE_PATH` en `agente_antigravity_sdk.py`.
- **Verificación:** Ejecución limpia validada de `agente_antigravity_sdk.py`, `alberth_learn.py` y `alberth_memory_sync.py`.

### 2026-09-05 (Alberth NEXUS v4.5+ & Antigravity Native SDK)
- **Antigravity Primary Agent:** Incorporación de Antigravity como agente primario de desarrollo con soporte multivariante, streaming con extended thinking y tools MCP.
- **Visual Engine v4.5+:** Implementación de Canvas Chart de 7 días, Auto-DND y atajos directos en autocomplete.

### 2026-09-04 (Lanzamiento Alberth NEXUS v4.0 a v4.3)
- **UI PWA & Floating Bar:** Floating Bar con Glassmorphism, WebAudio Haptics, Notificaciones push y encolamiento offline.
- **Reconocimiento Facial:** Modo de cámara bajo demanda y comparación de embeddings de rostros.

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
