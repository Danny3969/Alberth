# 🚗 DRIVO & DRIVO ONE — Contexto de Proyectos para Alberth

> Este archivo es la base de conocimiento permanente de los DOS proyectos de Novasyscom.
> Alberth debe leerlo antes de responder cualquier pregunta sobre cualquiera de los proyectos.
> Última actualización: 2026-06-19

> ⚠️ IMPORTANTE: Son dos productos DISTINTOS con bases de código SEPARADAS. No confundirlos.

---

# PROYECTO 1: DRIVO (Transporte Urbano)

## 🎯 ¿Qué es DRIVO?

DRIVO (también llamado internamente **Macondo Drive**) es una plataforma de transporte urbano tipo Uber, construida por **Novasyscom**. Conecta **conductores** y **pasajeros** en tiempo real, con negociación de precios, sistema de créditos/comisión, y mapas en vivo.

**CEO / Propietario del proyecto:** `digitalspace` (el usuario de este workspace).

---

## 🏗️ Arquitectura del Proyecto

El proyecto vive en `/Users/digitalspace/Desktop/Drivo/` y tiene 3 componentes principales:

| Componente | Ruta | Tecnología | Descripción |
|---|---|---|---|
| **App Móvil** | `drivo/` | Flutter + Dart | App para conductores y pasajeros |
| **Backend** | `macondo-backend/` | Firebase (Node.js Cloud Functions + Firestore) | Lógica de negocio, autenticación, comisiones |
| **Admin Web** | `macondo-admin-web/` | Flutter Web | Panel de administración |

**Base de datos:** Firebase Firestore (NoSQL, tiempo real)  
**Auth:** Firebase Authentication  
**Mapas:** Google Maps SDK (Android/iOS/Web)  
**Bundle ID móvil:** `com.example.local_transport_app`  
**Firebase Project:** `macondo-drive`

---

## 📦 Estado Actual de la App (Versión Vigente)

**Versión activa:** `DRIVO v5.12.1`  
**APK más reciente:** `DRIVO_v5.12.1_PERFORMANCE_UX.apk`

### ✅ Últimos fixes implementados (Fase SEG + Performance)

1. **PremiumAvatar** — `_getInitials()` con null safety, regex split, fallback robusto
2. **MapScreen** — Type-safe cast `(_userData?['name'] as String?)`
3. **RegisterScreen** — Bug crítico: validación de placa/cooperativa ahora funciona (antes había bypass)
4. **AuthService** — Validación de duplicados (email, teléfono, cédula) antes de registrar
5. **ProfileScreen** — Validación de unicidad al cambiar email/phone/cédula
6. **Drawer** — `profileImageUrl` guardado dentro de `driverProfile`
7. **PremiumAvatar** — `CachedNetworkImage` para fotos en caché local
8. **MapScreen** — Radar timer optimizado: 100ms → 200ms (−50% rebuilds)
9. **Deps** — Eliminados `cloud_functions` y `google_maps_flutter_web` (no usados)

### 🔐 Fase de Seguridad (SEG-01) — Aplicada en código

- Eliminado almacenamiento de `password` en texto plano en Firestore
- `index.ts`: Eliminado `update({ password })` en `changeUserPasswordSecure`
- Admin web: Cambio de contraseña migrado a Cloud Function segura
- `AndroidManifest.xml`: `android:allowBackup="false"`

---

## ⏳ Pendientes Críticos (Requieren Acción Manual)

### 🔴 URGENTE: Restricción de Google Maps API Key
- **Consola:** https://console.cloud.google.com/apis/credentials
- **API Key expuesta:** `AIzaSyAPUrJ53bAaFRYcYXWIumucVQmb_RYDOQU`
- **Acción:** Restringir a los paquetes/dominios de DRIVO + solo las APIs necesarias (Maps, Directions, Places, Geocoding)

### 🔴 URGENTE: Firebase App Check (Producción)
- Código ya configurado en modo DEBUG
- Pendiente: Activar en consola Firebase → App Check → registrar cada plataforma con providers de producción (Play Integrity / App Attest / reCAPTCHA v3)

### 🟡 PENDIENTE: Keystore para Release Signing
- `android/app/build.gradle.kts` ya tiene la config lista
- Falta: Generar `upload-keystore.jks` y llenar `key.properties`
- Obtener SHA-1 del keystore para agregarlo a la restricción de Maps API

---

## 🧠 Reglas de Ingeniería del Proyecto

Estas reglas son **absolutas** y Alberth debe respetarlas al 100%:

1. **Analizar antes de actuar** — Entender el sistema actual antes de proponer cambios
2. **Cambios mínimos** — Solo modificar lo necesario para la tarea solicitada
3. **No refactorizar sin permiso** — No cambiar código funcional aunque parezca mejorable
4. **Dividir en pasos** — Cambios grandes se dividen en pasos pequeños y confirmados
5. **Pedir autorización** — Nunca ejecutar cambios de código sin aprobación explícita del CEO
6. **Prioridad:** Estabilidad → Consistencia → Claridad → Mejoras

---

## 📋 Historial de Fases Relevantes

| Fase | Fecha | Descripción |
|---|---|---|
| SEG-01 | 2026-06-03 | Seguridad: Detener sangrado (passwords en Firestore, App Check, Backup) |
| FASE 63 | 2026-03-25 | Restauración de calificación y segundo viaje |
| FASE 62 | 2026-03-25 | Blindaje de créditos y comisión 10% |
| FASE 61 | 2026-03-25 | Blindaje de roles y ETA dinámico en ofertas |
| PERFORMANCE_UX | 2026-06-19 | Optimización de radar, caché de fotos, limpieza de deps |

---

## 🗺️ Decisiones de Arquitectura Tomadas

### Sistema de Carrusel (Confirmado)
**Decisión:** Mantener el sistema de **Carrusel con Enfoque Dinámico** para múltiples viajes simultáneos.  
**Justificación:** Evita múltiples listeners de mapas pesados y peticiones Firestore redundantes. El mapa se limpia automáticamente para mostrar solo la ruta relevante. Permite al pasajero concentrarse en un conductor a la vez.

### Roles en MapScreen
Los conductores ven viajes que pueden pagar con su `walletBalance`. El rol se detecta via `rideData['riderId']` para evitar "ceguera de rol" entre conductor y pasajero.

---

## 📍 Rutas de Archivos Clave

```
/Users/digitalspace/Desktop/Drivo/
├── drivo/                          ← App móvil Flutter (FUENTE PRINCIPAL)
│   ├── lib/
│   │   ├── screens/
│   │   │   ├── map_screen.dart     ← Pantalla principal con mapa y carrusel
│   │   │   ├── register_screen.dart
│   │   │   └── profile_screen.dart
│   │   └── services/
│   │       ├── auth_service.dart   ← Autenticación + validación unicidad
│   │       └── ride_service.dart   ← Lógica de viajes y comisiones
│   └── android/
│       ├── app/build.gradle.kts   ← Config de signing release
│       └── key.properties.template
├── macondo-backend/
│   └── functions/index.ts          ← Cloud Functions (Node.js)
├── macondo-admin-web/              ← Panel admin (Flutter Web)
├── CONTEXT.md                      ← Estado rápido del proyecto
├── RECORDS.md                      ← Historial quirúrgico completo
├── PENDIENTE_FASE1.md              ← Tareas manuales de seguridad
├── AI_ARCHITECTURE_RULES.md       ← Reglas para agentes de IA
└── AI_Antigravity_rules.md        ← Reglas específicas para Antigravity
```

---

# PROYECTO 2: DRIVO ONE (Delivery / Ecommerce)

## 🎯 ¿Qué es DRIVO ONE?

DRIVO ONE es una plataforma de **delivery y comercio electrónico** tipo Rappi/UberEats, construida por **Novasyscom**. Conecta **clientes**, **conductores (socios)** y **comerciantes (merchants)** para gestión de pedidos, entregas y pagos en tiempo real.

**Es un producto diferente a DRIVO** — no comparten código fuente ni base de datos.

**CEO / Propietario:** `digitalspace` (el usuario de este workspace)

---

## 🏗️ Arquitectura de DRIVO ONE

El proyecto vive en `/Users/digitalspace/Desktop/Drivo One/` y tiene **5 componentes**:

| Componente | Ruta | Tecnología | Descripción |
|---|---|---|---|
| **App Cliente** | `drivo-customer-app/` | Flutter + Dart | App para clientes que hacen pedidos |
| **App Conductor** | `drivo-driver-app/` | Flutter + Dart | App para socios/repartidores |
| **App Merchant** | `drivo-merchant-app/` | Flutter + Dart | App para comerciantes/negocios |
| **Backend** | `drivo-backend/` | Node.js + Express + Prisma | API REST, lógica de negocio, pagos |
| **Admin Web** | `drivo-admin-web/` | Flutter Web | Panel de administración |

**Backend stack:**
- **Runtime:** Node.js + Express
- **ORM:** Prisma (SQL — a diferencia de DRIVO que usa Firestore)
- **Auth:** Firebase Admin + JWT (`jsonwebtoken`)
- **Storage:** Cloudinary (imágenes de productos)
- **Pagos:** Google Pay (via `googleapis`)
- **Seguridad:** `helmet`, `express-rate-limit`, `bcryptjs`
- **Package name backend:** `drivo-eats-backend`

---

## 📦 Estado Actual de DRIVO ONE (Versión Vigente)

**APK más reciente (Customer):** `Drivo_One_V53_Premium_Cart_Refinement.apk`  
**APK más reciente (Socio/Driver):** `Drivo_One_Socio.apk`

### Historial de versiones recientes (Customer)

| APK | Descripción |
|---|---|
| V53 Premium_Cart_Refinement | Refinamiento del carrito — **VIGENTE** |
| V52 Hybrid_Persistence | Persistencia híbrida del carrito |
| V51 Surgical_Order_Fix | Fix quirúrgico de órdenes |
| V50 Aesthetic_Carousel | Carrusel estético |
| V49 Dynamic_Sync | Sincronización dinámica |
| V48 Advanced_Logistics | Logística avanzada |
| V47 Order_Master_Fix | Fix maestro de órdenes |
| V40 Brand_Immersion | Identidad de marca |
| Customer_v82_OrderModule | Módulo de órdenes |

---

## 🗺️ Rutas de Archivos Clave — DRIVO ONE

```
/Users/digitalspace/Desktop/Drivo One/
├── drivo-customer-app/       ← App Flutter del cliente
│   └── lib/
├── drivo-driver-app/         ← App Flutter del conductor/socio
│   └── lib/
├── drivo-merchant-app/       ← App Flutter del comerciante
│   └── lib/
├── drivo-backend/            ← API Node.js + Express + Prisma
│   ├── src/
│   ├── prisma/               ← Schema SQL y migraciones
│   └── package.json          ← name: "drivo-eats-backend"
├── drivo-admin-web/          ← Panel admin Flutter Web
└── Drivo_One_Instaladores/   ← APKs históricos
```

**Versión fija de trabajo:** `/Users/digitalspace/Desktop/Drivo_One_v4_Fixed/`  
(Contiene: `drivo_customer_v4.apk`, `drivo_driver_v4.apk`, `drivo_merchant_v4.apk`)

---

## 🔑 Diferencias Clave entre DRIVO y DRIVO ONE

| Aspecto | DRIVO | DRIVO ONE |
|---|---|---|
| **Tipo** | Transporte (tipo Uber) | Delivery / Ecommerce (tipo Rappi) |
| **Apps** | 1 app unificada (conductor + pasajero) | 3 apps separadas (cliente, conductor, merchant) |
| **Backend** | Firebase Firestore (NoSQL) | Express + Prisma (SQL) |
| **Auth** | Firebase Authentication | Firebase Admin + JWT |
| **Storage** | Firebase Storage | Cloudinary |
| **Versión vigente** | v5.12.1 | V53 |
| **Ruta** | `/Desktop/Drivo/drivo/` | `/Desktop/Drivo One/` |

---

## 🔮 Próximos Pasos Sugeridos

1. **Completar pendientes de seguridad** — Restricción Maps API + Firebase App Check (manuales en consola)
2. **Generar keystore** para distribución en Play Store
3. **Testing del segundo viaje** — Bug reportado: botón "PEDIR OTRO" no operativo post-Fase 63
4. **Fase de QA** — Probar flujo completo conductor-pasajero con las últimas correcciones
