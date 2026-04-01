# Tasks: ML Traceability

1. Añadir `model_metadata` a predicciones
   - Incluir `model_name`, `model_version`, `artifact_hash` en `predictions`.
   - Estimación: 2h

2. Crear `model_registry`
   - Almacenar metadatos de cada modelo (training dataset hash, params, metrics, artifact path).
   - Estimación: 2h

3. Endpoint de trazabilidad
   - `/admin/model-trace/{prediction_id}` que devuelve metadata completa.
   - Estimación: 2h

4. Tests de reproducibilidad
   - Validar que con `model_metadata` se puede localizar el artefacto.
   - Estimación: 2h
