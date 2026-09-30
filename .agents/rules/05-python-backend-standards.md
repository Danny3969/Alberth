# 🐍 Estándares Backend Python & FastAPI (Alberth / ECC)

## 1. Tipado y Asyncio
- Todo código Python nuevo debe incluir anotaciones de tipo (`type hints`) en argumentos y valores de retorno.
- En servidores FastAPI, usar rutas asíncronas (`async def`) para endpoints I/O bound (bases de datos, HTTP requests, llamadas a LLMs).
- No bloquear el event loop principal de asyncio con operaciones síncronas pesadas (usar `asyncio.to_thread` o `ThreadPoolExecutor` para operaciones bloqueantes).

## 2. Bases de Datos y Rendimiento
- Eliminar consultas N+1 en bases de datos relacionales (usar joins explícitos o eager loading).
- Emplear índices SQLite/PostgreSQL en columnas de búsqueda recurrente.
- En SQLite: Mantener habilitado el modo WAL (`PRAGMA journal_mode=WAL;`) para permitir lecturas y escrituras concurrentes sin bloqueos de archivo.
