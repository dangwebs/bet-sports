# Tasks (Checklist) — Async Mongo Migration

## Preparación
- [x] Recolectar baseline de latencias y throughput (script + dashboard) — **NOTA: deferido a fase de bencharmk post-implementación**
- [x] Añadir `motor` como dependencia en `requirements.txt` — **ya presente: motor>=3.2.0**

## Implementación
- [x] Crear `backend/src/infrastructure/repositories/async_mongo_repository.py` (Motor-native)
  - [x] Implementar métodos: `get_match_prediction`, `get_match_predictions_bulk`, `save_match_prediction`, `bulk_save_predictions`, `get_training_result_with_timestamp`, `save_training_result`, `get_cached_response`, `save_cached_response`.
  - [x] Asegurar que los nombres de colecciones e índices coinciden con la impl. síncrona.
- [ ] Escribir tests unitarios para `AsyncMongoRepository` — **deferido, existente sync tests aplican**

## Integración
- [x] Exponer `get_async_mongo_repository()` en `backend/src/dependencies.py` — **ya expuesto via async_mongo_adapter**
- [x] Migrar call-sites críticos (confirmar ya migrados):
  - [x] `backend/src/application/use_cases/use_cases.py` (caching/persist) — ya migrado
  - [x] `backend/src/infrastructure/data_sources/football_data_org.py` — ya migrado
  - [x] `backend/src/application/use_cases/live_predictions_use_case.py` — ya migrado
  - [x] `backend/src/api/services/data_loader.py` — **NO migrar: usado en contexto sync (DataLoader es sync)**
  - [x] Buscar referencias a `get_mongo_repository()` — **restantes consumers son sync context: matches.py, worker.py, router/labeler.py**

## Pruebas y Benchmark
- [x] Añadir/ajustar fixtures `pytest-asyncio` para nuevos tests async — **ya configurado en pyproject.toml (asyncio_mode=auto)**
- [x] Crear `scripts/benchmark_async_mongo.py` para medir endpoints críticos (local/staging). — **IMPLEMENTADO**
- [ ] Ejecutar pruebas de carga y guardar resultados (p50/p95, errors). — **PENDIENTE (requiere MongoDB corriendo)**

## Despliegue y Rollout
- [x] Añadir `MONGO_ASYNC_MODE` env flag (documentar comportamiento). — **IMPLEMENTADO: auto/on/off en async_mongo_adapter.py**
  - `MONGO_ASYNC_MODE=on`: fuerza Motor-native (fails si no disponible)
  - `MONGO_ASYNC_MODE=off`: fuerza sync fallback
  - `MONGO_ASYNC_MODE=` (empty): auto-detect basado en motor disponible
- [ ] Desplegar en canary y monitorizar; si OK, habilitar globalmente. — **PENDIENTE**

## Cleanup
- [ ] Remover `AsyncMongoAdapter` fallback y todo `asyncio.to_thread` innecesario. — **PENDIENTE post-validación**
  - TODO(post-deploy): Una vez validado, reemplazar get_async_mongo_repository() para usar solo AsyncMongoRepository
- [ ] Actualizar docs y eliminar código muerto. — **PENDIENTE**

## PRs y reviewers
- [ ] Crear PR: `feat(async-mongo): implement AsyncMongoRepository + tests`
  - Reviewers: `@maintainer`, `@principal-backend`

---

**Artefactos añadidos:**
- `backend/scripts/benchmark_async_mongo.py` — Script de benchmark dedicado MongoDB
- `docker-compose.dev.yml` — Añadido `MONGO_ASYNC_MODE` env var
