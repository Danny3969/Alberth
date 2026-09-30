# 🛡️ Reglas de Seguridad y Credenciales (Antigravity & ECC)

## Verificaciones de Seguridad Obligatorias
Antes de cualquier commit, ejecución en producción o entrega final:

1. **Cero Secretos Hardcodeados:**
   - NUNCA escribir API keys, tokens JWT, contraseñas ni URLs privadas en el código fuente.
   - Usar siempre variables de entorno (`.env`) o gestores seguros de configuración.
   - Verificar que `.env` y archivos `.key` o `.pem` estén estrictamente incluidos en `.gitignore`.

2. **Validación Rigurosa en Fronteras de Entrada:**
   - Validar y tipar todo input externo recibido (APIs, query params, bodies JSON, CLI args).
   - Sanitizar cadenas de texto para prevenir inyecciones SQL (usar queries parametrizadas siempre).
   - Sanitizar salidas HTML para erradicar cualquier riesgo de XSS (Cross-Site Scripting).

3. **Manejo Seguro de Errores:**
   - Los mensajes de error dirigidos a usuarios o clientes finales nunca deben exponer stack traces completos, rutas absolutas del servidor, ni nombres de tablas o esquemas de base de datos.
   - Registrar los detalles técnicos en logs internos protegidos.

4. **Protocolo en Caso de Incidente:**
   - Si se detecta una vulnerabilidad crítica o un secreto expuesto accidentalmente: DETENER la tarea, invalidar la clave expuesta, rotar credenciales y reportar de inmediato al Señor.
