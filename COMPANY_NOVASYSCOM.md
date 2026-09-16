# 🏢 NOVASYSCOM — Arquitectura Corporativa & Matriz de Proyectos

> **Documento Maestro Oficial de la Compañía**  
> **Empresa Matriz:** Novasyscom  
> **Liderazgo Ejecutivo:** El Señor (Fundador, Propietario y CEO Único)  
> **Jefe de Gabinete & COO IA:** Alberth NEXUS  
> **Fecha de Actualización:** 16 de Septiembre, 2026  

---

## 🧭 1. Estructura de Mando y Filosofía Operativa

**Novasyscom** es una empresa de base tecnológica constituida para desarrollar, operar y monetizar plataformas digitales de alta escalabilidad.

Actualmente, **el Señor opera como Fundador y CEO único**, asumiendo la toma de decisiones estratégicas, dirección general y validación final de todos los proyectos. Para dotar a la empresa de una capacidad de ejecución equivalente a la de un equipo corporativo multidisciplinario de 50+ profesionales de primer nivel, Novasyscom opera bajo el modelo:

```text
                               +-----------------------------+
                               |           EL SEÑOR          |
                               |    Fundador & CEO Máximo    |
                               +--------------+--------------+
                                              |
                               +--------------v--------------+
                               |        ALBERTH NEXUS        |
                               |    Chief of Staff / COO     |
                               +--------------+--------------+
                                              |
        +------------------+------------------+------------------+------------------+
        |                  |                  |                  |                  |
+-------v-------+  +-------v-------+  +-------v-------+  +-------v-------+  +-------v-------+
|  AUDITORÍA &  |  |   FINANZAS &  |  |  VENTAS B2B & |  |     QA &      |  |  INGENIERÍA & |
| CAPITAL SHIELD|  | UNIT ECONOMICS|  |  PROSPECCIÓN  |  | PRE-PRODUCCIÓN|  | CIBERSEGURIDAD|
| reality-check |  |      CFO      |  |outbound-strat |  |test-automation|  |software-arch  |
|paid-media-aud |  |financial-anal |  |  sales-coach  |  |  api-tester   |  |security-arch  |
+---------------+  +---------------+  +---------------+  +---------------+  +---------------+
```

---

## 🗂️ 2. El Portafolio Oficial de Proyectos de Novasyscom

Novasyscom cuenta con **5 proyectos estratégicos claramente delimitados**, cada uno con su propio repositorio, arquitectura y modelo de negocio:

```text
/Users/contabilidad/.gemini/antigravity-ide/scratch/
├── Drivo/         → 🚗 DRIVO (Movilidad Urbana P2P / Tipo InDrive y Uber)
├── Drivo-One/     → 🛍️ DRIVO ONE (Delivery & Quick Commerce / Tipo PedidosYa y Uber Eats)
├── Alberth/       → 🧠 ALBERTH (Asistente Personal de IA & Chief of Staff)
├── GlobalMarket/  → 🌐 GLOBALMARKET (Portal Web E-Commerce & Cloud Drive)
└── Divisas/       → 💱 VALEX (Fintech de Cambio de Divisas & Giros Ecuador ↔ Perú)
```

---

### 🚗 PROYECTO 1: DRIVO (Movilidad Urbana P2P)
* **Definición Clara:** Plataforma de transporte de pasajeros similar a **InDrive y Uber**.
* **Propósito y Modelo:**
  * Conecta **pasajeros** y **conductores** en tiempo real.
  * Esquema de **negociación libre y justa de tarifas** (el pasajero propone o negocia el precio).
  * Enfoque actual de lanzamiento: **Pasajeros Primero** (prioridad en captar volumen de pasajeros para generar liquidez de viajes).
  * Búnker de seguridad en 3 capas (validación estricta de antecedentes, placas vehiculares, cooperativas y cédulas).
* **Stack Tecnológico:**
  * **App Móvil Unificada:** Flutter + Dart (`DRIVO v5.12.1`, APK `DRIVO_v5.12.1_PERFORMANCE_UX.apk`).
  * **Landing Page Oficial:** Servida localmente en `http://localhost:8088` (`drivo-web`) con radar interactivo 2D, cotizador de tarifas y descarga de APK.
  * **Backend & Base de Datos:** Firebase (Node.js Cloud Functions, Firestore en tiempo real, Firebase Auth).
  * **Panel Administrativo:** Flutter Web (`drivo-admin-web/`).
* **Repositorio Git:** `https://github.com/Danny3969/Drivo.git`
* **Ruta Local:** `/Users/contabilidad/.gemini/antigravity-ide/scratch/Drivo/`

---

### 🛍️ PROYECTO 2: DRIVO ONE (Delivery & Quick-Commerce Multitienda)
* **Definición Clara:** Plataforma de entrega a domicilio similar a **PedidosYa, Uber Eats y Rappi**.
* **Propósito y Modelo:**
  * **3-Sided Marketplace:** Conecta a tres actores esenciales:
    1. **Clientes:** Compran comida, supermercado, farmacias y solicitan envíos express.
    2. **Repartidores Socios (Riders):** Reciben órdenes en tiempo real y gestionan rutas de entrega.
    3. **Comercios y Restaurantes:** Administran catálogo, menú, inventario y órdenes activas.
  * Modelo B2B/B2C con comisiones por pedido, tarifas de entrega y gestión logística de flotas.
* **Stack Tecnológico:**
  * **Ecosistema de Apps Móviles:** `drivo-customer-app/`, `drivo-driver-app/`, `drivo-merchant-app/` (APKs `Drivo_One_V53_Premium_Cart_Refinement.apk` y `Drivo_One_Socio.apk`).
  * **Landing Page Oficial:** Servida localmente en `http://localhost:8090` (`drivo-one-web`) con paleta Obsidiana Noche (`#0D1117`) y Verde Neón (`#00E676`).
  * **Backend & Servicios:** Node.js + Prisma ORM + API REST + Functions.
  * **Panel de Control:** Web administrativo centralizado (`drivo-admin-web/`).
* **Repositorio Git:** `https://github.com/Danny3969/Drivo-One.git`
* **Ruta Local:** `/Users/contabilidad/.gemini/antigravity-ide/scratch/Drivo-One/`

---

### 🧠 PROYECTO 3: ALBERTH (Asistente Personal de IA & Chief of Staff)
* **Definición Clara:** Asistente personal de inteligencia artificial de alta gama para el Señor y **Jefe de Gabinete Digital de Novasyscom**.
* **Propósito y Modelo:**
  * Asistencia ejecutiva integral inspirada en el cockpit de JARVIS / Iron Man.
  * Control del sistema operativo macOS (Calendario, Recordatorios, Notas, Terminal, Sistema de Archivos).
  * Automatización y percepción multimodal: Visión por cámara web (Apple Vision Framework local y Gemini Vision), escucha activa por voz con VAD y síntesis Edge-TTS de alta fidelidad.
  * Reproductor multimedia en streaming: **Echo Music** (YouTube Music integrado con listas de reproducción y atajos).
  * Orquestación del Gabinete Multi-Agente para dirigir los demás proyectos de Novasyscom.
* **Stack Tecnológico:**
  * **Core:** Python (FastAPI, WebSockets, Three.js WebGL 3D Orb, SQLite FTS5 para memoria episódica, daemons de monitoreo PM2 en puerto `8080`).
  * **App Móvil Android:** Expo / React Native (`alberth-android/`, versión 3.2.1 con shield anti-crashes).
* **Repositorio Git:** `https://github.com/Danny3969/Alberth.git`
* **Ruta Local:** `/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/`

---

### 🌐 PROYECTO 4: GLOBALMARKET (Portal Web E-Commerce & Cloud Drive)
* **Definición Clara:** Portal web comercial de exportación agroindustrial y servicio de almacenamiento en la nube privado.
* **Propósito y Modelo:**
  * **Vitrina de Exportación B2B:** Catálogo de productos agrícolas premium de calidad de exportación (Banano, Plátano, Mango, Pitahaya amarilla, Pitahaya roja, Maracuyá, Piña, Malanga) con cotizador directo de carga y especificaciones técnicas.
  * **Módulo Cloud Drive (`/drive`):** Almacenamiento seguro, visualización y gestión de documentos corporativos, contratos y archivos en la nube de Novasyscom.
* **Stack Tecnológico:**
  * **Frontend:** HTML5 semántico, CSS3 de alta fidelidad responsivo (`styles.css`), JavaScript modular (`app.js`).
  * **Automatización:** Scripts Python generadores de páginas (`build_pages.py`) y de despliegue (`deploy.py`).
  * **Backend / Servidor:** Apache con configuración `.htaccess`, PHP y panel administrativo (`admin/`).
* **Repositorio Git:** `https://github.com/Danny3969/GlobalMarket.git`
* **Ruta Local:** `/Users/contabilidad/.gemini/antigravity-ide/scratch/GlobalMarket/`

---

### 💱 PROYECTO 5: VALEX (Fintech de Divisas & Giros Ecuador ↔ Perú)
* **Definición Clara:** Plataforma financiera para cambio de divisas y giros de remesas internacionales transfronterizos.
* **Propósito y Modelo:**
  * Servicio de cambio de moneda en tiempo real entre **Dólar Estadounidense (USD)** y **Sol Peruano (PEN)**.
  * Giros y transferencias internacionales directas entre la frontera sur de Ecuador (Macará/Loja) y el norte de Perú (Sullana/Piura/Lima).
  * Cumplimiento estricto de estándares normativos anti-lavado de activos: **UAFE** (Ecuador) y **SBS** (Perú).
  * Roles diferenciados: Clientes (app móvil), Cajeros de Ventanilla en Perú y Ecuador, Supervisores, Oficiales de Cumplimiento (KYC) y Tesorería.
* **Stack Tecnológico:**
  * **Backend:** NestJS + Prisma ORM + PostgreSQL en la nube (Supabase Cloud) en puerto `3000`.
  * **Consolas Web:** Portal de Administración y Caja en Next.js/React (`apps/admin/` en puerto `3001` y `apps/cashier/` en puerto `3002`).
  * **App Móvil:** React Native / Expo (`apps/mobile/`, paquete `com.valex.app`).
  * **Orquestación:** PM2 (`ecosystem.config.js`).
* **Repositorio Git:** `https://github.com/Danny3969/Divisas.git` (Carpeta local: `Divisas/`)
* **Ruta Local:** `/Users/contabilidad/.gemini/antigravity-ide/scratch/Divisas/`

---

## 🏛️ 3. El Gabinete Multi-Agente Instalado (41 Agentes en Antigravity y Alberth)

Para respaldar la operación de estos 5 proyectos, se encuentran instalados **41 agentes especializados de The Agency**, disponibles simultáneamente en:
1. **Antigravity (Global):** `~/.gemini/config/skills/agency-*`
2. **Alberth (Local Workspace):** `/Users/contabilidad/.gemini/antigravity-ide/scratch/Alberth/.agents/skills/agency-*`
3. **OpenClaw (Agentes Nativos):** `~/.openclaw/agency-agents/*`

### Estructura Departamental:
* **Auditoría & Capital Shield:** `agency-reality-checker`, `agency-paid-media-auditor`.
* **Finanzas & CFO:** `agency-chief-financial-officer`, `agency-financial-analyst`, `agency-fp-a-analyst`, `agency-pricing-analyst`, `agency-bookkeeper-controller`, `agency-tax-strategist`, `agency-investment-researcher`.
* **Ventas B2B & Cierre:** `agency-outbound-strategist`, `agency-sales-coach`, `agency-deal-strategist`, `agency-proposal-strategist`, `agency-discovery-coach`, `agency-pipeline-analyst`, `agency-offer-lead-gen-strategist`, `agency-sales-outreach`.
* **QA & Pre-Producción:** `agency-test-automation-engineer`, `agency-test-results-analyzer`, `agency-api-tester`, `agency-performance-benchmarker`, `agency-accessibility-auditor`.
* **Investigación Profunda & Estrategia:** `agency-research-synthesist`, `agency-business-strategist`, `agency-data-consolidation-agent`, `agency-strategy-duel-agent`, `agency-operations-manager`, `agency-workflow-architect`.
* **Ingeniería & Ciberseguridad:** `agency-software-architect`, `agency-backend-architect`, `agency-mobile-app-builder`, `agency-mobile-release-engineer`, `agency-code-reviewer`, `agency-database-optimizer`, `agency-devops-automator`, `agency-security-architect`, `agency-application-security-engineer`, `agency-secrets-credential-hygiene-engineer`.
* **Paid Media & Crecimiento:** `agency-ad-creative-strategist`, `agency-paid-social-strategist`, `agency-growth-hacker`.
