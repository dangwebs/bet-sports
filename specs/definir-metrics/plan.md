# Plan: Definir métricas

Resumen
-------
Estandarizar y publicar un catálogo de métricas operacionales y de negocio para el sistema (ingest, labeler, modelos, pipelines). Garantizar nombres, tipos y puntos de instrumentación consistentes para Prometheus/Grafana.

Objetivos
---------
- Definir un catálogo canónico de métricas (nombres, labels, tipo: counter/gauge/histogram).
- Instrumentar backend y jobs (ingest, labeler, workers) con `prometheus_client`.
- Publicar dashboards básicos y reglas de alerta para anomalías críticas.

Entregables
-----------
- `docs/metrics_catalog.md` (catálogo de métricas y convenciones).
- Instrumentación básica en: ingestion path, labeler job, scheduler, endpoints críticos.
- Dashboards/Grafana JSON o instrucciones para crear paneles clave (ingest rate, error rate, latency, labeled_count).
- Reglas de alerta (ej.: tasa de fallos > X, backlog del labeler > Y).

Hitos y cronograma
------------------
1. Catálogo de métricas y convenciones — 0.5 día.
2. Biblioteca de instrumentación y wrappers comunes — 0.5–1 día.
3. Instrumentación de endpoints primarios y jobs — 1 día.
4. Crear dashboards y alertas — 0.5 día.

Dependencias
------------
- Librería `prometheus_client` en el entorno Python.
- Acceso a la infraestructura de métricas (Prometheus/Grafana) o instrucciones para exportar métricas.
- Puntos de integración: `backend/src/api/*`, `scripts/labeler.py`, workers.

Riesgos y mitigaciones
----------------------
- Overhead de instrumentación → usar histogram buckets razonables y evitar métricas cardinales altas.
- Falta de endpoint Prometheus accesible → documentar cómo exponer `/metrics` y añadir tests de smoke.

Próximos pasos inmediatos
------------------------
1. Crear `docs/metrics_catalog.md` con las métricas propuestas.
2. Añadir un wrapper sencillo `metrics.py` en `backend/src/utils/` para exponer contadores/histogramas.
