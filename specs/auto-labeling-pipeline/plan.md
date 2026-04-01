# Plan: Auto-labeling Pipeline

Resumen
-------
Diseñar e implementar un pipeline que etiquete automáticamente predicciones cuando los resultados oficiales estén disponibles. Incluir dry-run, auditoría e idempotencia.

Objetivos
---------
- Job programado (diario) que reconcilia predicciones con resultados.
- Backfill controlado para ventanas históricas (90d, 30d, 7d).
- Endpoint admin para ejecutar dry-run y run persistente.
- Audit logging de decisiones del labeler.

Entregables
-----------
- `scripts/labeler.py` con `--dry-run` y `--window`.
- Job scheduler (Celery beat / APScheduler / CronJob) definido.
- Colección `labeling_audit` y esquema `predictions` ajustado.
- Endpoints `/admin/labeler/dry-run` y `/admin/labeler/run`.
- Métricas Prometheus básicas: `labeled_count`, `failure_count`, `latency`.

Hitos y cronograma
------------------
1. Diseñar esquema de datos y strategy de matching — 0.5–1 día.
2. Implementar labeler core y heuristics — 1–2 días.
3. Scheduler y script CLI — 0.5 día.
4. Endpoints admin y tests de integración — 0.5–1 día.
5. Dry-run en dataset 90d y ajuste — 0.5–1 día.

Dependencias
------------
- Fuente de truth de resultados (collection de matches).
- Acceso a `predictions` collection y repositorios.

Riesgos y mitigaciones
----------------------
- Mal-matching por timestamps: normalizar timestamps a UTC y usar ventanas configurables.
- Duplicado de labels: garantizar idempotencia usando checks por `prediction_id` y versioning.

Próximos pasos inmediatos
------------------------
1. Definir esquema `labeling_audit` y cambios mínimos en `predictions`.
2. Implementar un dry-run que imprima un informe CSV/JSON para validación.