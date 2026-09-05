# 🧠 MEMORY — Proyecto ALBERTH NEXUS (Asistente Personal de IA)
_Última actualización: 2026-09-04 22:26 GMT-5_

## 🔗 Repositorio GitHub Oficial
- **URL:** https://github.com/Danny3969/Alberth
- **Rama Principal:** `main`

---

## 🏗️ Arquitectura del Sistema (Alberth NEXUS v3.3)
```text
[WORKSPACE_ROOT] (dinámico: OPENCLAW_WORKSPACE / ALBERTH_WORKSPACE / ruta local)
├── agents/
│   ├── orquestador/    → Agente Orquestador Core [Nvidia NIM GLM-5.1]
│   ├── codigo/         → Agente de Desarrollo & Refactor [Nvidia NIM Qwen2.5-Coder-32B]
│   ├── vision/         → Agente Multimodal & Reconocimiento Facial [Nvidia NIM / Llama-3.2-Vision]
│   └── qa_proactivo/   → Agente QA & Corrector de Voz [TTS es-MX-JorgeNeural]
├── alberth-android/    → Aplicación Móvil Nativa (React Native / Expo SDK 56)
├── panel/              → Panel Web UI interactivo (HTML5/CSS3/WebSockets)
├── pipeline_refactor/  → Pipeline moderno en Python nativo con Circuit Breaker
├── alberth_web_server.py    → Panel Web FastAPI + WebSockets + Live Canvas A2UI (Puerto 8080)
├── alberth_voice_server.py  → Servidor STT de audio y escucha continua con VAD
├── alberth_vision.py        → Cámara On-Demand + Registro & Reconocimiento de Personas Conocidas
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
- **Panel Web & Live Canvas A2UI:** `http://localhost:8080` (FastAPI / WebSockets / `/api/canvas`)
- **OpenClaw Gateway:** `http://localhost:18789` (Control Plane)
- **Skills Registry:** ClawHub Integration Enabled (`https://clawhub.dev/api/v1`)
- **Túnel Seguro Cloudflare:** `alberth_tunnel.sh`
- **Audit Logs:** `~/.openclaw/workspace/logs/audit_logs.jsonl`
- **Modo de Contexto Activo:** `~/.openclaw/workspace/.context_mode` (`laboral` | `personal`)

---

## 🎨 CARACTERÍSTICAS DIFERENCIALES INTEGRADAS

1. **Cámara On-Demand & Aprendizaje de Personas:**
   - **Activación por Voz:** *"Alberth, activa la cámara"* o *"Alberth, quién está frente a la cámara"*.
   - **Registro de Personas:** *"Alberth, te presento a mi hija Danna"*. El sistema extrae los rasgos visuales, los guarda en `user_facts` bajo `personas_conocidas` y la reconoce automáticamente en futuras interacciones.
2. **Live Canvas (A2UI):** Renderizado de interfaces dinámicas generadas por el agente en tiempo real en `/api/canvas`.
3. **Personalidad `SOUL.md` Inyectada:** Inyección automática del alma de Alberth (mano derecha analítica, semiformal, directa y no condescendiente) en cada prompt.
4. **ClawHub Registry (+5,000 Skills):** Registro de componentes y habilidades remotas activado en `openclaw.json`.
5. **Blindaje RCE & Sanitización STT:** Filtro de caracteres de escape y sanitización de entrada activados en el orquestador de voz.

---

## 🗂️ SEPARACIÓN DE CONTEXTOS (Personal / Laboral)

### 🔵 Contexto Personal (Namespace: `user_personal`)
- **Enfoque:** Hábitos, salud, música (Echo Music / YT Music Premium), recordatorios de hogar, compras, personas conocidas.
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
  - Inferencia Multimodal / Visión: `openrouter/google/gemini-2.5-flash` / `Nvidia NIM Llama-3.2-Vision`
  - Transcripción STT: `groq/whisper-large-v3-turbo`
  - Síntesis de Voz TTS: `es-MX-JorgeNeural` (Edge-TTS)

---

## 📌 Historial de Eventos e Hitos Recientes

### 2026-09-04 (Implementación de Modo Cámara On-Demand & Registro de Personas)
- **Aprendizaje Visual:** Implementada la función `enroll_person()` en `alberth_vision.py` para registrar personas conocidas en `user_facts` (`category: personas_conocidas`).
- **Reconocimiento Visual:** Integrado `recognize_known_people()` para capturar la cámara de forma efímera (cero consumo pasivo de GPU/batería) e identificar personas registradas (ej. Danna), saludándolas y adaptando la conversación.
- **Rutas de Voz:** Integradas en `alberth_master.sh` para frases como *"te presento a..."*, *"mira a..."*, *"quién está frente a la cámara"*.

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
