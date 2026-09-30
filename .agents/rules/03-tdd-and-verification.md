# 🧪 Metodología TDD y Bucle de Verificación (ECC / Antigravity)

## 1. Flujo de Desarrollo Guiado por Pruebas (TDD)
Para la creación de nueva lógica o solución de incidencias:
1. **Fase Roja (Red):** Diseñar o actualizar la prueba unitaria que describe el comportamiento esperado antes o a la par del código. Ejecutarla para verificar que falla coherentemente.
2. **Fase Verde (Green):** Implementar la solución mínima y limpia necesaria para que la prueba sea superada con éxito.
3. **Fase Refactor (Refactor):** Pulir el código, optimizar nombres de variables, eliminar redundancias y asegurar que las pruebas sigan pasando al 100%.

## 2. Bucle de Verificación Obligatorio (Pre-Flight Check)
NUNCA asumir que el código funciona solo porque "compila mentalmente":
- Ejecutar el intérprete o suite de pruebas real mediante la terminal.
- Comprobar que no haya regresiones en los módulos circundantes.
- En scripts de shell: Validar siempre la sintaxis con `bash -n script.sh`.
- En código Python: Ejecutar con el entorno virtual designado (`venv/bin/python3 -m py_compile`).
- En aplicaciones web/APIs: Validar que el servidor responda código HTTP 200/OK.
