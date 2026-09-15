# 🎨 DESIGN.md — Alberth Quantum Cockpit Brand Contract
<!-- OpenDesign Brand Contract Specification v1.0 -->

## 1. Brand Identity & Creative Direction
- **Identity:** Alberth NEXUS — Advanced Cybernetic AI Butler & Personal Operating System.
- **Aesthetic Direction:** Cyberpunk Quantum Cockpit (JARVIS / Iron Man / AMSY inspired), tactical HUD, holographic wireframes, dark obsidian depth with high-contrast neon luminescence.
- **Mood:** Professional, authoritative, futuristic, elegant, responsive and alive.
- **Tone:** Refined British modern butler, distinguished, highly intelligent, loyal and composed.
- **Tratamiento Protocolar:** Exclusivamente **"Señor"** en toda interacción de interfaz, voz y texto.

---

## 2. Color Tokens & Palette Architecture

### Surface & Background Tokens
| Token | HEX / Value | Role |
| :--- | :--- | :--- |
| `--bg-obsidian` | `#040711` | Primary background canvas |
| `--bg-card` | `rgba(6, 14, 28, 0.72)` | Glassmorphic HUD cards |
| `--bg-card-hover` | `rgba(10, 22, 44, 0.85)` | Elevated surface hover state |
| `--bg-dock` | `rgba(4, 8, 18, 0.90)` | Bottom command bar & Floating Widget |

### Accent & Luminescence Tokens
| Token | HEX / Value | Role |
| :--- | :--- | :--- |
| `--cyan-core` | `#00f0ff` | Primary quantum accent, HUD rings, active states |
| `--cyan-glow` | `rgba(0, 240, 255, 0.45)` | Volumetric neon glow shadow |
| `--blue-electric`| `#0077ff` | Secondary telemetry accent, live streaming wave |
| `--amber-warn` | `#ffb703` | Processing state, warnings, high-load telemetry |
| `--emerald-live` | `#00ff88` | Active connection, online status, healthy daemon |
| `--crimson-crit`| `#ff0055` | Disconnect, critical error, stop action |

### Border & Elevation Tokens
| Token | CSS Value |
| :--- | :--- |
| `--border-hud` | `1px solid rgba(0, 240, 255, 0.22)` |
| `--border-active` | `1px solid rgba(0, 240, 255, 0.75)` |
| `--glass-filter` | `backdrop-filter: blur(14px) saturate(180%)` |
| `--shadow-quantum`| `0 8px 32px 0 rgba(0, 0, 0, 0.55), inset 0 0 16px rgba(0, 240, 255, 0.08)` |

---

## 3. Typography Hierarchy

### Font Families
- **Display / Headers / Telemetry:** `'Orbitron', 'Rajdhani', sans-serif`
- **Body / Chat / Content:** `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- **Terminal / Code / Logs:** `'JetBrains Mono', monospace`

### Scale
- **HUD Hero Title:** `20px` (Weight 700, Letter-spacing `0.15em`, Text-transform uppercase)
- **Card Header:** `14px` (Weight 600, Letter-spacing `0.10em`, Text-transform uppercase)
- **Body & Chat:** `13px` (Weight 400, Line-height `1.55`)
- **Telemetry Labels:** `10px` (Weight 600, Letter-spacing `0.12em`, Opacity `0.75`)

---

## 4. Key Component Specs

### 3D Holographic Orb (`.orb-stage`)
- Centerpiece of the cockpit cockpit view.
- 1,800 Fibonacci particle swarm rendered via WebGL (Three.js).
- State-reactive:
  - `idle`: Slow ambient cyan wave (`#00f0ff`), 12 RPM.
  - `listening`: Pulsing emerald wave (`#00ff88`), amplitude +35%.
  - `thinking`: Rapid amber/violet orbital vortex (`#ffb703`), 45 RPM.
  - `speaking`: Harmonic expansion linked in real time to `speakerAnalyser`.

### Ultra-Live Badge (`#btn-ultra-live`)
- Gradient background: `linear-gradient(135deg, #00f0ff, #0077ff)`.
- Pulse glow: `0 0 20px rgba(0, 240, 255, 0.7)`.
- Keyframe animation: `livePulseGlow 1.5s infinite alternate ease-in-out`.

### Echo Music Player Card
- Compact glassmorphism container with animated frequency visualizer.
- Cyberpunk cover art with glowing ambient backlight.
- Multi-playlist quick selector, sequential/shuffle playback, and tactile seekbar.

---

## 5. Craft & Anti-Slop Rules (OpenDesign Principles)
1. **Never use plain browser defaults:** Inputs, scrollbars, and buttons must use custom cybernetic tokens.
2. **Never flash unstyled white backgrounds:** The entire cockpit must remain OLED deep obsidian (`#040711`).
3. **Keep micro-animations snappy:** All hover, transition, and expand durations between `150ms` and `250ms` with `cubic-bezier(0.16, 1, 0.3, 1)`.
4. **WCAG AA Compliance:** Ensure minimum 4.5:1 text-to-background contrast on all informational readouts.
5. **No decorative dead ends:** Every interactive element in the HUD must provide visual feedback (glow, haptic sound, or tooltip).
