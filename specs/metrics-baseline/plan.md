# Plan: Metrics Baseline

Resumen
-------
Establecer una línea base histórica de métricas operacionales (ingest rate, error rate, latency, labeled throughput) para identificar regresiones y objetivos de mejora.

Objetivos
---------
- Recolectar métricas históricas (90d mínimo) y calcular percentiles relevantes.
- Establecer umbrales y objetivos (SLO/SLA) basados en baseline.
- Automatizar reportes periódicos y alertas por desviación.

Entregables
-----------
- `specs/metrics-baseline/tasks.md` con pasos de recopilación y dashboard.
- Tablas/CSV con baseline calculado.
