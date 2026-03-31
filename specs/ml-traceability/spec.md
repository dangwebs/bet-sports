# Spec: ML Traceability

Resumen
-------
Garantizar que cada predicción lleve metadatos de modelo (`model_id`, `model_version`, `training_snapshot_hash`, `feature_version`) y que exista una tabla/documento de `model_metadata` con trazabilidad completa del entrenamiento.

Objetivos
--------
- Añadir `model_metadata` a los documentos de predicción.
- Almacenar artefactos de entrenamiento básicos (hash de dataset, parámetros, fecha, seed).
- Exponer endpoint para consultar `model_metadata` y asociar predicciones a versión de modelo.

Requisitos funcionales
----------------------
1. `model_metadata` almacenado en DB y referenciado desde `match_predictions`.
2. Endpoint `GET /api/v1/models/{model_id}` con información de entrenamiento.

Desglose de tareas
------------------
1. Definir esquema para `model_metadata` (1h).
2. Ajustar código que crea predicciones para inyectar `model_metadata` (2–3h).
3. Añadir endpoint y tests (2h).

Aceptación
----------
- Se puede trazar una predicción hasta la versión de modelo y parámetros usados.
# Spec: ML Traceability (Epic 7)

Fecha: 2026-03-31

Resumen
-------
Introducir metadatos de modelo en cada predicción y en los artefactos de entrenamiento para asegurar reproducibilidad, auditoría y posibilidad de rollback de decisiones del labeler.

Objetivos
---------
- Anotar `model_version`, `feature_hash`, `training_snapshot` y `inference_signature` en cada documento de predicción.
- Registrar metadatos de entrenamiento (datasets usados, parámetros, métricas) en colección `model_metadata`.

Requisitos (REQ-7.x)
-------------------
- REQ-7.1: Cambiar esquema de `predictions` para incluir `model_metadata` con campos mínimos: `version`, `trained_at`, `dataset_hash`.
- REQ-7.2: Versionado semántico del modelo y política sobre rollbacks.
- REQ-7.3: API para consultar predicciones por `model_version` y filtrar por entrenamiento.

Aceptación
----------
- AC-1: Pruebas que muestran que una predicción contiene `model_metadata` correctamente rellenado.
- AC-2: Dashboard o query básica que agregue métricas por `model_version`.

Tareas
------
1. Diseñar `model_metadata` schema y migración para predicciones existentes.
2. Modificar el flujo de generación de predicciones para inyectar metadatos.
3. Añadir endpoints analíticos simples para filtrar por versión.
