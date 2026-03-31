# Plan: Data Sanity Rules

Resumen
-------
Establecer validaciones automáticas para ingestión y almacenamiento de predicciones y resultados: timestamps, rangos de probabilidades, canonicalización de nombres, y detección de outliers.

Objetivos
---------
- Validar y normalizar timestamps (ISO8601, timezone-aware).
- Rechazar o normalizar probabilidades fuera de [0,1].
- Canonicalizar nombres de equipos usando `team_aliases`.
- Implementar scanner nocturno que reporte anomalías.

Entregables
-----------
- `src/infrastructure/validators` con validadores reutilizables.
- Canonicalizer de equipos y tabla `team_aliases`.
- Scanner nocturno y métricas de calidad.

Hitos y cronograma
------------------
1. Implementar validador central y tests — 0.5–1 día.
2. Añadir checks en puntos de ingest — 0.5 día.
3. Implementar scanner nocturno y alertas — 1 día.

Dependencias
------------
- Puntos de ingest existentes (endpoints/queues).
- Fuente de alias de equipos (data/team_aliases o `data/team_short_names.json`).

Riesgos
-------
- Falsos positivos al rechazar registros — Mitigación: marcar y cuarentenar, no borrar automáticamente.

Próximos pasos inmediatos
------------------------
1. Implementar `src/infrastructure/validators/` y añadir pruebas unitarias.
2. Añadir metricas para % rechazados y alertas en dashboards.