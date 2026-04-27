---
title: Migración a MongoDB async (Motor) y Auditoría de Rendimiento
author: Equipo Backend (Pair: Principal Backend Engineer)
date: 2026-04-20
status: completed
tags: [performance, migration, async, mongodb, motor]
---

Resumen ejecutivo
------------------
Esta especificación describe la migración controlada de la capa de persistencia MongoDB
a una implementación nativa async basada en `motor` (AsyncIOMotorClient), junto con
un plan de auditoría de rendimiento y validación. Se busca eliminar llamadas bloqueantes
desde handlers/paths `async` (FastAPI), reducir latencias en endpoints críticos y
proveer un camino seguro de rollback usando un adaptador híbrido (`AsyncMongoAdapter`).

Contexto y motivación
----------------------
- Hoy la base de código expone llamadas síncronas a Mongo (PyMongo / repo síncrono)
  desde contextos `async`, lo que puede bloquear el event loop y causar latencias
  y problemas de concurrencia bajo carga.
- Ya se introdujeron parches de baja fricción: `asyncio.to_thread(...)`, batching
  de predicciones y un `AsyncMongoAdapter` que usa `motor` cuando está disponible
  o envuelve el repo síncrono usando `to_thread`.
- El objetivo ahora es completar la migración a una implementación `AsyncMongoRepository`
  basada en `motor`, formalizar la estrategia de despliegue y garantizar métricas de
  rendimiento aceptables antes de eliminar el fallback.

Alcance (in-scope)
-------------------
- Implementar `AsyncMongoRepository` (Motor-native) que ofrezca paridad de API con
  `MongoRepository` actual.
- Añadir/actualizar fábrica DI (`get_async_mongo_repository`) y ajustes en
  `dependencies.py` para exponer la dependencia en contextos async.
- Actualizar pruebas unitarias/integración y CI para soportar `motor`.
- Ejecutar auditoría de rendimiento y benchmark antes/después en endpoints críticos
  (`/suggested-picks`, `/live-predictions`, etc.).

Fuera de alcance (out-of-scope)
-----------------------------
- Reescribir la lógica ML o la arquitectura general de servicios.
- Reemplazar otras dependencias sync (p.ej. `diskcache`) por alternativas async en
  esta iteración (se evaluará en fases posteriores).

Requisitos y criterios de aceptación
-----------------------------------
- Los tests unitarios y de integración existentes pasan (sin introducir flakiness).
- No quedan llamadas síncronas a la base de datos ejecutadas directamente desde
  handlers `async` (detección por grep y revisión de code paths críticos).
- Los endpoints críticos muestran mejora o no empeoran significativamente: objetivo
  inicial: reducir p95 de latencia en 20-40% para `suggested-picks` bajo carga.
- Despliegue con `MONGO_ASYNC_MODE=true` (o similar) debe permitir activar Motor
  sin requerir rollback de esquema ni downtime mayor a X minutos.

Diseño propuesto
----------------
- Implementar `AsyncMongoRepository` (archivo: `backend/src/infrastructure/repositories/async_mongo_repository.py`) que:
  - Use `AsyncIOMotorClient` y colecciones equivalentes.
  - Exporte métodos `async` en paridad con `MongoRepository` (p.ej. `get_match_prediction`, `bulk_save_predictions`, `get_training_result_with_timestamp`, `save_training_result`, etc.).
  - Mantenga índices y nombres de colecciones consistentes con la impl. síncrona.
- Mantener el `AsyncMongoAdapter` como shim de compatibilidad durante migración.
- DI: En `dependencies.py` exponer `get_async_mongo_repository()` para uso en código async.
- Feature-flag / Env: `MONGO_ASYNC_MODE` o depender de la disponibilidad de `motor`.
- CI: Añadir `motor` a `pyproject.toml` extras / CI env; asegurar `pytest-asyncio` configurado.

Plan de migración (alto nivel)
-----------------------------
1. Baseline y métricas: medir latencias actuales y throughput en endpoints críticos.
2. Implementar `AsyncMongoRepository` con tests unitarios (local Motor client).
3. Integración: cambiar consumidores async para usar `get_async_mongo_repository()`.
4. Ejecutar pruebas y benchmarks en entorno de staging (Motor ON).
5. Staged rollout a producción con monitoreo (feature flag o env toggle).
6. Cleanup: eliminar `to_thread` wrappers innecesarios y el fallback cuando seguro.

Riesgos y mitigaciones
----------------------
- Riesgo: regresión de rendimiento por diseño de consultas async.
  - Mitigación: benchmarks y pruebas de carga; mantener `to_thread` fallback temporal.
- Riesgo: tests no cubren paths de concurrencia.
  - Mitigación: añadir tests de integración que simulen múltiples requests simultáneos.

Pruebas y validación
--------------------
- Unit tests para cada método nuevo en `AsyncMongoRepository`.
- Integration tests que ejecuten `live_predictions`/`suggested_picks` en staging.
- Benchmarks reproducibles (scripts en `scripts/benchmark_async_mongo.py`).

Entregables
-----------
- `backend/specs/async-mongo-migration/spec.md` (este archivo)
- `backend/specs/async-mongo-migration/plan.md`
- `backend/specs/async-mongo-migration/tasks.md`

Referencias
----------
- `backend/src/infrastructure/repositories/async_mongo_adapter.py` (ya presente)
- Parches aplicados: `use_cases` async migrations, `football_data_org` updates.

Siguientes pasos inmediatos
--------------------------
1. ✓ Crear `AsyncMongoRepository` con paridad de API.
2. ✓ Añadir `motor` a `requirements.txt` (ya presente).
3. ✓ Migrar call-sites async: use_cases, football_data_org, live_predictions.
4. 🔲 Benchmark y staged rollout (pendientes para siguiente fase)
5. 🔲 Cleanup del fallback (pendiente para post-validación)
