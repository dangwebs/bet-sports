# Spec: Data Sanity Rules

Resumen
-------
Definir validaciones y reglas de sanity para ingestion y storage de predicciones y resultados: formatos de timestamp, ventanas válidas, ranges de probabilidades y checks para detectar outliers (p.ej. future-dated predictions).

Objetivos
--------
- Validar timestamps al ingest (ISO8601, timezone-aware).
- Rechazar o normalizar predicciones con probabilidades fuera [0,1].
- Regla de alerta para `date_delta_h` anómalo (p.ej. > 168h).

Requisitos funcionales
----------------------
1. Middleware o validación en entrypoint que normalice/valide payloads.
2. Job nightly que escanea DB y reporta anomalías.

Desglose de tareas
------------------
1. Implementar validador central en `src/api/utils/validators.py` (2h).
2. Añadir checks en ingestion y pruebas (2h).
3. Implementar scanner nocturno y alertas (3h).

Aceptación
----------
- Reducción comprobable de predicciones future-dated en un muestreo previo/post.
# Spec: Data Sanity Rules (Epic 8)

Fecha: 2026-03-31

Resumen
-------
Definir reglas automáticas y validaciones para los datos entrantes (ingestión de partidos, predicciones y resultados) para evitar sesgos, mal-matches por tiempos y datos corruptos.

Objetivos
---------
- Validar timestamps, nombres de equipos y valores de mercado.
- Detectar duplicados y rupturas de esquema.
- Generar alertas y métricas de calidad de datos.

Requisitos (REQ-8.x)
-------------------
- REQ-8.1: Validaciones en la capa de ingest (schema + types + timestamp plausibility).
- REQ-8.2: Canonicalización de nombres de equipos mediante tabla `team_aliases`.
- REQ-8.3: Pipeline de detección de outliers (ej. apuestas con probabilidades fuera de rango o volumes nulos).

Aceptación
----------
- AC-1: Las ingest pipelines rechazan (o marcan) registros con timestamps inconsistentes y documentan el motivo.
- AC-2: Los dashboards muestran porcentaje de registros rechazados por regla.

Tareas
------
1. Crear `src/infrastructure/validators` con validaciones JSON/Pydantic reutilizables.
2. Implementar canonicalizer para nombres de equipos y tests unitarios.
3. Añadir métricas Prometheus/Logs para alertas de calidad.
