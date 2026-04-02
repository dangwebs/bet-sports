# Plan: ML Traceability

Resumen
-------
Implementar trazabilidad de modelos y predicciones: registrar versión del modelo, artefactos usados, entradas de inferencia y metadatos para reproducibilidad y auditoría.

Objetivos
---------
- Incluir `model_version` y `model_metadata` en cada predicción.
- Almacenar artefactos de modelo y hashes para referencia.
- Proveer endpoint/admin para consultar trazabilidad por `prediction_id`.

Entregables
-----------
- Cambios en esquema `predictions` y tabla/colección `model_registry`.
- Endpoints para consultar trazabilidad.
- Tests de integridad y reproducibilidad.
