# 📱 Estándares de Ingeniería Flutter & Dart (Novasyscom / ECC)

## 1. Arquitectura por Capas
Para proyectos móviles y multiplataforma en Flutter:
- **Capa UI (Presentación):** Widgets declarativos limpios. Cero lógica de negocio o llamadas directas a base de datos en los métodos `build()`.
- **Capa Logic / Domain:** Gestores de estado (Bloc / Provider / Riverpod / Cubit) que controlan eventos y estados de manera inmutable.
- **Capa Data:** Repositorios y fuentes de datos remotas/locales aisladas.

## 2. Convenciones Dart
- Usar `const` constructores en todos los widgets inmutables para optimizar la reconstrucción del árbol de elementos.
- Evitar variables públicas mutables; favorecer clases inmutables con `freezed` o métodos `copyWith`.
- Manejar nulos explícitamente sin abusar del operador `!` (force-unwrap).
- Validar layouts responsivos evitando excepciones de desbordamiento (`RenderFlex overflowed`).
