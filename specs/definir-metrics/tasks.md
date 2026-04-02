# Tasks: Definir métricas

1. Crear catálogo de métricas
   - Descripción: definir nombres, labels y tipo (counter/gauge/histogram) en `docs/metrics_catalog.md`.
   - Estimación: 2h

2. Implementar wrapper de métricas
   - Descripción: añadir `backend/src/utils/metrics.py` con helpers para counters/histograms/gauges.
   - Estimación: 1–2h

3. Instrumentar puntos críticos
   - Descripción: instrumentar ingest, labeler job, endpoints clave y workers.
   - Estimación: 4h

4. Añadir endpoint `/metrics` y tests de smoke
   - Descripción: exponer métricas y validar con test de integración ligera.
   - Estimación: 1h

5. Crear dashboards y reglas de alerta
   - Descripción: definir paneles y alertas básicas en Grafana/Alertmanager.
   - Estimación: 2h

6. Validación y ajuste de buckets/labels
   - Descripción: ejecutar en staging y ajustar buckets para histogramas.
   - Estimación: 1–2h
