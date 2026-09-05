# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04 22:30 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v4.0 — Visual Engine)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador Core [Nvidia NIM GLM-5.1]
│   ├── codigo/         → Agente de Desarrollo & Refactor [Nvidia NIM Qwen2.5-Coder-32B]
│   ├── vision/         → Agente Multimodal & Reconocimiento Facial [Nvidia NIM / Llama-3.2-Vision]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web & Floating Bar UI (HTML5/CSS3/Three.js/WebSockets)
│   ├── index.html      → Panel Principal HUD + Orbe 3D WebGL (Three.js Audio-Reactive)
│   └── floating.html   → Standalone Desktop Floating Bar (Spotlight / Cmd+Shift+A)
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets + Live Canvas A2UI + `/floating` (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua con VAD
├── alberth_vision.py        → Cámara On-Demand + Registro & Reconocimiento de Personas (ej. Danna)
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
- **Desktop Floating Bar:** `http://localhost:8080/floating` (Glassmorphism Overlay UI)
- **Live Canvas A2UI:** `/api/canvas` (Dynamic Component Drawer)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Skills Registry:** ClawHub Integration Enabled (`https://clawhub.dev/api/v1`)
- **Túnel Seguro Cloudflare:** `alberth_tunnel.sh`
- **Audit Logs:** `~/.openclaw/workspace/logs/audit_logs.jsonl`
- **Modo de Contexto Activo:** `~/.openclaw/workspace/.context_mode` (`laboral` | `personal`)

---

## 🎨 ALBERTH VISUAL ENGINE v4.0 — ARQUITECTURA VISUAL INTEGRADAS

1. **Standalone Desktop Floating Bar (`http://localhost:8080/floating`):**
   - Interfaz minimalista con Glassmorphism (`backdrop-filter: blur(24px)`), atajo de teclado (`Cmd + Shift + A`), respuesta ultra-rápida y badge de contexto activo (`laboral` / `personal`).
2. **Orbe 3D Holográfico Reactivo en Three.js (`panel/index.html`):**
   - Esfera neumórfica de partículas 3D que modula su forma de onda en tiempo real según los decibelios recibidos del micrófono o altavoz (WebAudio API FFT).
3. **Live Canvas Slide-Over (A2UI):**
   - Despliegue automático de tarjetas visuales, widgets, gráficos de finanzas y tablas generadas por el agente.
4. **Sonido Háptico Sintetizado (Audio Cues):**
   - Retroalimentación auditiva de baja frecuencia sintetizada por WebAudio API (efectos de activación de micrófono y confirmación sin archivos pesados).

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Lanzamiento Alberth Visual Engine v4.0)
- **Floating Bar:** Creación del componente flotante desacoplado `panel/floating.html` y ruta `/floating` en `alberth_web_server.py`.
- **Three.js & Audio Spectrum:** Orbe holográfico en Three.js sincronizado con los estados de color (`cyan`, `violeta`, `verde`).
- **Cámara & Reconocimiento Facial:** Enrolamiento visual de personas (`enroll_person`) y saludo contextual integrado en `alberth_vision.py`.

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
