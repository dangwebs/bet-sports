# Tareas: Entrenamiento Efímero

## Bloque 1: Orchestrator

- [x] **T1 / REQ-ET-1**: Eliminar la persistencia local en `ml_training_orchestrator.py` quitando la llamada a `save_models()`.
- [x] **T2 / REQ-ET-2**: Crear una función `cleanup_model_files()` que elimine `backend/ml_picks_classifier.joblib` y `backend/ml_models/*.joblib`.
- [x] **T3 / REQ-ET-2**: Ejecutar `cleanup_model_files()` al final de `run_training_pipeline()`, incluso si no hubo modelo persistido en la corrida actual.

## Bloque 2: Script de entrenamiento optimizado

- [x] **T4 / REQ-ET-1**: Eliminar todas las llamadas activas a `joblib.dump()` en `backend/scripts/train_model_optimized.py`.
- [x] **T5 / REQ-ET-1**: Mantener `models_bundle` exclusivamente en memoria para la generación inmediata de predicciones.
- [x] **T6 / REQ-ET-2**: Agregar limpieza de `.joblib` al final de `main()` en `train_model_optimized.py`.

## Bloque 3: Fallback y logging

- [x] **T7 / REQ-ET-4**: Ajustar `PicksService` para registrar como `info` la ausencia del modelo local cuando sea un comportamiento esperado.
- [x] **T8 / REQ-ET-4**: Confirmar que `PredictionService._get_model()` sigue retornando `None` sin lanzar error cuando no existe archivo local.

## Bloque 4: Validación

- [x] **T9 / AC-1..AC-4**: Buscar referencias activas a `joblib.dump(...)` en el flujo operativo y confirmar que fueron eliminadas.
- [x] **T10 / AC-5**: Validar sintaxis de los archivos Python modificados.
- [x] **T11 / REQ-ET-5**: Hacer que `backend/src/scheduler.py` degrade con gracia si `apscheduler` no está instalado, sin romper `run_daily_orchestrated_job()` ni el cron cuando la librería existe.
- [x] **T12 / REQ-ET-5**: Corregir en `backend/src/application/use_cases/use_cases.py` el origen de `LEAGUES_METADATA` para usar `src.domain.constants`.
- [x] **T13 / REQ-ET-5**: Corregir en `backend/scripts/train_model_optimized.py` el import de dependencias al módulo real `src.dependencies`.
- [x] **T14**: Documentar en el PR o changelog técnico que MongoDB pasa a ser la persistencia canónica del resultado del entrenamiento (`specs/ephemeral-training/delivery-report.md`).
- [x] **T15 / REQ-ET-5**: Corregir en `backend/scripts/warmup_all_leagues.py` el import legado a `src.api.dependencies` y alinear el mensaje operativo de persistencia a MongoDB.
- [x] **T16 / Seguimiento REQ-ET-5**: Desbloquear la construcción de `backend/scripts/warmup_all_leagues.py` corrigiendo el tipado runtime de `CacheWarmupService` e inyectando `match_aggregator`.
