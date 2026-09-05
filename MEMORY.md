# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04 22:48 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v4.2 — Spotlight, Focus & PWA)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador Core [Nvidia NIM GLM-5.1]
│   ├── codigo/         → Agente de Desarrollo & Refactor [Nvidia NIM Qwen2.5-Coder-32B]
│   ├── vision/         → Agente Multimodal & Reconocimiento Facial [Nvidia NIM / Llama-3.2-Vision]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web & Floating Bar UI (HTML5/CSS3/Three.js/WebSockets/PWA)
│   ├── index.html      → Panel Principal HUD + Orbe 3D WebGL (Three.js Audio-Reactive Double-Buffer)
│   ├── floating.html   → Desktop Floating Bar v4.2 (Spotlight Autocomplete / Focus Mode / QA Severities)
│   └── sw.js           → Service Worker para funcionamiento PWA Offline de la UI
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
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
- **Desktop Floating Bar v4.2:** `http://localhost:8080/floating` (Spotlight Autocomplete + Focus Mode + PWA)
- **Live Canvas A2UI:** `/api/canvas` (Dynamic Component Drawer)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Skills Registry:** ClawHub Integration Enabled (`https://clawhub.dev/api/v1`)
- **Túnel Seguro Cloudflare:** `alberth_tunnel.sh`
- **Audit Logs:** `~/.openclaw/workspace/logs/audit_logs.jsonl`
- **Modo de Contexto Activo:** `~/.openclaw/workspace/.context_mode` (`laboral` | `personal`)

---

## 🎨 NOVEDADES DE ALBERTH NEXUS v4.2

1. **Spotlight Autocomplete en la Floating Bar:** Despliegue automático de comandos frecuentes (`/modo personal`, `/modo laboral`, `/confidencial`, `/camara`, `qué hora es`) al escribir.
2. **Modo "Focus" (`Cmd + Shift + F`):** Colapso instantáneo de paneles secundarios a una barra minimalista limpia para concentrarse al máximo.
3. **Severidades QA & Historial de Alertas:** Clasificación por colores de alertas QA (`sugerencia`: cian, `advertencia`: amarillo, `critico`: rojo).
4. **PWA & Offline Service Worker (`sw.js`):** Cacheo de la interfaz gráfica para que funcione 100% offline sin servidor de red externo.

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Lanzamiento Alberth NEXUS v4.2)
- **UI PWA & Offline:** Implementación del Service Worker `panel/sw.js` y autocompletado estilo Spotlight.
- **Focus Mode:** Modo concentración accesible con `Cmd + Shift + F`.
- **QA Severities:** Clasificación por niveles de severidad en notificaciones.

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
