# Plan: Entrenamiento Efímero

Fecha: 2026-04-01

## Enfoque

Modificar el pipeline de entrenamiento para que los modelos ML vivan SOLO en memoria durante el ciclo de entrenamiento + inferencia. Después de generar y guardar predicciones en MongoDB, eliminar cualquier archivo `.joblib` del disco.

## Objetivos

- Cumplir `REQ-ET-1` y `REQ-ET-2` sin romper el scheduler diario.
- Mantener compatibilidad con el fallback estadístico definido en `REQ-ET-4`.
- Dejar la base de datos como fuente canónica del resultado de entrenamiento e inferencia (`REQ-ET-3`).

## Pasos

### 1. `ml_training_orchestrator.py` — Eliminar persistencia a disco
- Eliminar la llamada a `save_models(clf, "ml_picks_classifier.joblib")` dentro de `run_training_pipeline()`.
- Agregar función `cleanup_model_files()` que elimine archivos `.joblib` de `ml_models/` y raíz.
- Invocar `cleanup_model_files()` al final de `run_training_pipeline()`.

### 2. `train_model_optimized.py` — Eliminar `joblib.dump()` y agregar limpieza
- Eliminar todas las líneas `joblib.dump(...)` que escriben a `ml_models/*.joblib`.
- Los modelos se mantienen en memoria en `models_bundle` (ya existe) que se pasan a `generate_league_predictions()`.
- Agregar limpieza de archivos `.joblib` al final de `main()`.

### 3. `picks_service.py` — Log informativo cuando no hay modelo
- El constructor ya maneja `None` gracefully. Ajustar log de `warning` a `info` cuando el modelo no existe (es esperado ahora).

### 4. Limpieza de archivos existentes
- Agregar una función utilitaria reutilizable para limpiar archivos `.joblib`.

## Validación

1. Verificar que no queden llamadas activas a `joblib.dump(...)` en los flujos operativos modificados.
2. Verificar que el cleanup contemple tanto `backend/ml_models/*.joblib` como `backend/ml_picks_classifier.joblib`.
3. Ejecutar una validación de sintaxis sobre los archivos Python modificados.
4. Confirmar que el fallback del `PredictionService` sigue siendo no disruptivo cuando no existe modelo local.

## Riesgos

- **Bajo**: Si el scheduler falla entre entrenamiento e inferencia, las predicciones no se generan. Mitigación: el sistema ya tiene fallback a Poisson estadístico base.
- **Bajo**: Los archivos `.joblib` existentes en el repo. Se deben eliminar o ignorar en `.gitignore`.

## Resultado esperado

- El entrenamiento deja de depender del filesystem como artefacto persistente.
- Las predicciones y resultados continúan disponibles en MongoDB.
- No quedan residuos `.joblib` luego de cada corrida.
