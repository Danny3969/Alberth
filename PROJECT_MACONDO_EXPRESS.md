# 🚐 PROJECT MACONDO EXPRESS · TRANSPORTE PUERTA A PUERTA & ENCOMIENDAS QR
_Cooperativa de Transporte Interurbano y Logística de Carga Ligera_
_Ecosistema Corporativo Novasyscom_
_Fundador & CEO: El Señor_

---

## 🧭 1. Resumen Ejecutivo & Modelo Operativo

**Macondo Express** es una plataforma digital de dos aplicaciones móviles enlazadas, diseñada a medida para cooperativas de transporte interprovincial/interurbano (ej. Guayaquil ↔ Machala, Cuenca ↔ Loja). Su modelo de negocio se basa en la excelencia del servicio puerta a puerta, el confort en autos/camionetas de capacidad limitada (4 puestos), la certeza logística en encomiendas mediante verificación criptográfica QR y transacciones 100% en efectivo.

```text
       ┌─────────────────────────────────────────────────────────────┐
       │                COOPERATIVA MACONDO EXPRESS                  │
       └──────────────┬───────────────────────────────┬──────────────┘
                      │                               │
       ┌──────────────▼──────────────┐ ┌──────────────▼──────────────┐
       │     📱 MACONDO PASAJERO     │ │    🚐 MACONDO CONDUCTOR     │
       │   - Reserva Asientos (1..4) │ │   - Manifiesto Puerta a Pta │
       │   - Recogida GPS a la Puerta│ │   - Navegación Waze / Maps  │
       │   - Encomiendas con QR      │ │   - Escáner QR de Entrega   │
       │   - Pago 100% Efectivo      │ │   - Despacho & Admin Turnos │
       └─────────────────────────────┘ └─────────────────────────────┘
```

---

## 🔑 2. Reglas de Negocio Fundamentales (Directrices del Señor)

1. **Capacidad Estricta de 4 Pasajeros por Unidad:**
   - La flota opera con autos (sedanes) y camionetas doble cabina.
   - Cada vehículo tiene exactamente **4 cupos de pasajeros** para garantizar máximo confort.
   - El pasajero no requiere seleccionar un asiento en un mapa complejo de autobús; selecciona simplemente el número de puestos requeridos (1, 2, 3 o 4) de los disponibles en el turno.
2. **Servicio Puerta a Puerta con Coordenadas GPS:**
   - El pasajero fija su dirección exacta, referencia y coordenadas GPS de recogida.
   - El conductor visualiza en su manifiesto la ruta ordenada de recogidas con botón directo para abrir la navegación en **Google Maps o Waze**.
3. **Logística de Encomiendas con Verificación QR Criptográfica:**
   - El remitente registra el paquete y los puntos de recogida y entrega.
   - El sistema genera un **Código QR de Entrega único**.
   - El conductor escanea el código QR del destinatario al entregar físicamente el paquete, validando la entrega en la base de datos y disparando una notificación instantánea al remitente.
4. **Recaudación 100% en Efectivo:**
   - Cero fricción bancaria. Todos los pasajes y encomiendas se cobran en efectivo al abordar o al entregar.

---

## 🛠️ 3. Arquitectura Tecnológica & Stack

- **Lenguaje & Framework:** Flutter (Dart >=3.0.0 <4.0.0) para aplicaciones móviles iOS/Android y Web.
- **Base de Datos & Backend:** Supabase PostgreSQL con funciones almacenadas seguras (RPC):
  - `reservar_cupos_atomico`: Bloqueo pesimista de fila (`FOR UPDATE`) para evitar sobreventa de asientos.
  - `confirmar_entrega_encomienda`: Validación criptográfica de Códigos QR.
- **Estructura del Repositorio:**
  - `/Users/contabilidad/.gemini/antigravity-ide/scratch/MacondoExpress/`
    - `macondo_core/`: Modelos, constantes de color y servicio Supabase compartido.
    - `macondo_pasajero/`: Aplicación móvil/web de clientes.
    - `macondo_conductor/`: Aplicación móvil/web de choferes y panel de despacho.
    - `supabase/macondo_schema.sql`: DDL relacional, índices e historial de semillas.
    - `interactive_preview/`: Simulador interactivo dual en tiempo real (Puerto `8092`).

---

## 🌐 4. Simulador Interactivo Dual en Vivo

- **URL Local:** `http://localhost:8092`
- **Servicio PM2:** `macondo-express-web`
- **Funcionalidad:** Permite probar en paralelo el flujo del pasajero (reserva atómica y generación de QR) y la respuesta del conductor (actualización de cupos, manifiesto con GPS y escaneo QR de confirmación).
