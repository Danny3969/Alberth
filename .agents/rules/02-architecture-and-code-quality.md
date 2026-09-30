# 🏗️ Estándares de Arquitectura y Calidad de Código (ECC / Antigravity)

## 1. Principios de Diseño
- **Inmutabilidad por Defecto:** Preferir transformaciones inmutables sobre mutaciones en el lugar para evitar efectos secundarios imprevistos.
- **Funciones Pequeñas y Foco Único:** Cada función debe hacer una sola cosa y hacerla de manera determinista. Limitar funciones a un tamaño legible (<50 líneas salvo justificación de parsing/máquina de estados).
- **Falla Rápida y Explícita (Fail Loudly):** Nunca silenciar excepciones con bloques vacíos `except: pass` o `catch (e) {}`. Si ocurre un fallo, registrar el error con contexto o relanzarlo adecuadamente.
- **Sin Código Basura:** Prohibido dejar declaraciones de depuración (`console.log`, `print()`, `debugger;`) en código que vaya a ser entregado.

## 2. Convenciones de Commits
Seguir estrictamente la especificación de **Conventional Commits**:
- `feat:` Nuevas funcionalidades visibles o motores integrados.
- `fix:` Correcciones de errores o bugs.
- `refactor:` Mejoras en estructura interna sin alterar comportamiento externo.
- `test:` Adición o mejora de suites de pruebas.
- `docs:` Modificaciones en bitácoras, READMEs o bóvedas de conocimiento.
- `perf:` Optimizaciones de rendimiento de CPU/RAM/Red.
- `chore:` Mantenimiento de dependencias o configuración interna.

## 3. Filosofía Antigravity
- Mantener la integridad de la documentación existente.
- Preservar comentarios arquitectónicos existentes.
- Producir siempre enlaces clicables tipo `file:///` para archivos y símbolos de código.
