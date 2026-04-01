# Tasks: Auto-labeling Pipeline

1. Diseñar esquema de datos
   - Crear `labeling_audit` y añadir campos sugeridos en `predictions` (`labeled`, `label`, `label_timestamp`, `label_metadata`).
   - Estimación: 2h

2. Implementar labeler core
   - Script `scripts/labeler.py` con `--dry-run` y `--window`.
   - Matching priority: `match_id` → equipo+fecha fuzzy → heuristics.
   - Estimación: 4–6h

3. Implementar idempotencia y auditoría
   - Registrar decisiones en `labeling_audit` y evitar duplicados.
   - Estimación: 2h

4. Scheduler
   - Configurar Celery beat / APScheduler / CronJob y job diario.
   - Estimación: 2–3h

5. Endpoints admin
   - `/admin/labeler/dry-run` y `/admin/labeler/run` con paginación y autenticación.
   - Estimación: 3h

6. Tests e integración
   - Tests de idempotencia, matching y dry-run (incl. muestra 90d).
   - Estimación: 3–4h

7. Métricas y alertas
   - Instrumentar Prometheus metrics y alertas básicas.
   - Estimación: 2h

8. Backfill controlado
   - Herramienta CLI para backfill con `--window=90d` y `--batch-size`.
   - Estimación: 2–4h
