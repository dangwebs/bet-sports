# Spec: Auto-labeling Pipeline

Resumen
-------
Definir e implementar un pipeline responsable de etiquetar automáticamente predicciones pasadas cuando los resultados reales estén disponibles, garantizando trazabilidad, idempotencia y reversibilidad limitada.

Objetivos clave
---------------
- Pipeline schedulado (cron) que ejecuta diariamente un job de reconciliación.
- Backfill controlado para ventanas históricas (90d, 30d, 7d).
- Marcar predicciones con estados: `pending`, `labeled`, `failed`, `reconciled_at`.
- Guardar `label_metadata` (timestamp, source, confidence_at_label).

Requisitos funcionales
----------------------
1. Job diario: busca predicciones expiradas y matches finalizados, calcula label y persiste.
2. Endpoint manual: `POST /admin/labeler/run?window=90d` para backfills.
3. Reconciliación tolerante a desfases de fecha (configurable window +/-X horas).
4. Audit log de acciones del labeler (qué predicción cambió, por qué).

Requisitos no funcionales
-------------------------
- Idempotencia: re-ejecutar job no debe duplicar labels.
- Observabilidad: métricas Prometheus: labeled_count, failure_count, latency.
- Seguridad: endpoint admin protegido con token o guardia.

Aceptación
----------
- Backfill 90d se completa sin errores en staging sobre un dataset representativo.
- Labels correctos verificados por un muestreo manual (100 muestras).

Desglose de tareas
------------------
1. Diseñar esquema `prediction_labels` y campos en `match_predictions` (2h).
2. Implementar labeler core (logic + heuristics) (4–6h).
3. Job scheduler (cron / Celery beat / APScheduler) (2–3h).
4. Endpoints admin y tests de integración (3h).
5. Añadir métricas y alertas básicas (2h).

Riesgos
-------
- Mismatch de timestamps (predictions future-dated) → Mitigación: ventana configurable y herramienta de diagnóstico.
# Spec: Auto-labeling Pipeline (Epic 4)

Fecha: 2026-03-31

Resumen
-------
Diseñar e implementar un pipeline automático que asigne etiquetas (labels) a predicciones pasadas en función de resultados oficiales de partidos, con trazabilidad, modo `dry-run`, y mecanismos de reconciliación y auditoría.

Objetivos
---------
- Detectar partidos finalizados y casar predicciones almacenadas con resultados reales.
- Marcar predicciones como `labeled` con la etiqueta correspondiente (win/lose/draw/na).
- Mantener logs de decisiones y permitir dry-run sin persistir cambios.

Requisitos (REQ-4.x)
-------------------
- REQ-4.1: Job programado (cron) que extrae partidos finalizados en un rango configurable (ej.: últimos 7 días).
- REQ-4.2: Algoritmo de matching robusto: por `match_id` preferentemente, fallback a combinación de equipos+fecha+fuzzy-name.
- REQ-4.3: Escribir `labeling_audit` con: prediction_id, match_id, matching_strategy, confidence, timestamp, operator (dry-run or system).
- REQ-4.4: Idempotencia: relanzar job no debe duplicar etiquetas ni sobrescribir sin control de versión.
- REQ-4.5: Endpoint admin para lanzar dry-run y descargar informe CSV/JSON.

Aceptación
----------
- AC-1: Dry-run produce informe que concuerda con los matches manualmente verificados (muestra sample).
- AC-2: Job en modo persistente marca etiquetas y registra auditoría sin duplicados.

Esquema de datos (sugerido)
--------------------------
- `predictions` (colección): añadir campos `labeled: bool`, `label: str`, `label_timestamp`, `model_metadata`.
- `labeling_audit` (colección): documento por decisión con metadatos.

Tareas
------
1. Definir matching priority (match_id → team/date fuzzy → heuristics).
2. Implementar job scheduler (celery/cron/kubernetes CronJob) y script `labeler.py` con `--dry-run`.
3. Añadir endpoint admin `/admin/labeler/dry-run` y `/admin/labeler/run` con paginación.
4. Implementar `labeling_audit` y tests de idempotencia.
5. Ejecutar dry-run en 90 días de muestra y validar métricas básicas.

Riesgos
-------
- Riesgo: mal-matching por timestamps incorrectos. Mitigación: normalizar timestamps a UTC y tolerancia configurable.
