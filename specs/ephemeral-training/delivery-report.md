# Delivery Report: Entrenamiento Efimero

Fecha: 2026-04-02
Estado: completado a nivel backend

## Resumen

El pipeline de entrenamiento ya no persiste modelos ML como artefactos `.joblib` en disco. Los modelos viven solo en memoria durante la corrida activa y, al finalizar, se ejecuta una limpieza explicita de artefactos locales.

MongoDB pasa a ser la persistencia canonica del resultado de entrenamiento:

- `training_results` con clave `latest_daily` para el resumen agregado de entrenamiento.
- `match_predictions` para las predicciones generadas durante la corrida.

## Cambios entregados

- Se elimino la persistencia local de `ml_picks_classifier.joblib` en el orchestrator.
- Se eliminaron las escrituras `joblib.dump(...)` del script `train_model_optimized.py`.
- Se centralizo la limpieza de artefactos en `backend/src/core/model_artifacts.py`.
- Se ajusto el fallback de `PicksService` y `GetPredictionsUseCase` para tratar la ausencia de modelo local como comportamiento esperado.
- Se persistio `latest_daily` desde el scheduler y se guardo tambien el resultado en cache unificada.
- Se normalizo `save_training_result(...)` a un formato BSON-friendly para evitar fallos al persistir objetos de dominio complejos en MongoDB.
- Se corrigieron bloqueos heredados de entrypoints:
  - `scheduler.py` ahora degrada con gracia si `apscheduler` no esta instalado.
  - `use_cases.py` toma `LEAGUES_METADATA` desde `src.domain.constants`.
  - `train_model_optimized.py` usa `src.dependencies`.
  - `warmup_all_leagues.py` usa `src.dependencies`, inyecta `match_aggregator` y reporta persistencia en MongoDB.
  - `cache_warmup_service.py` ya no falla en import-time por tipado runtime no resuelto.

## Validacion ejecutada

- Validacion de sintaxis y errores de editor sobre los archivos Python modificados: sin errores.
- Validacion minima de imports/entrypoints:
  - `scheduler_mode=fallback`
  - `scheduler_has_instance=False`
  - `leagues_total=14`
  - `league_e0_exists=True`
  - `train_parse_days=1`
  - `train_parse_league=E0`
- Verificacion funcional en entorno temporal:
  - `orchestrator_cli.py train --days 550 --leagues E0` completo sin dejar `.joblib` persistidos.
  - `training_results.latest_daily` quedo persistido correctamente tras el fix BSON-friendly.
  - Se verifico persistencia de predicciones activas para `E0` en MongoDB.
- Verificacion controlada de warmup sin infraestructura externa:
  - `cache_warmup_service.py` importa correctamente.
  - `warmup_all_leagues.py` importa correctamente.
  - `main()` arma el wiring completo con `match_aggregator`, `persistence_repository` y `background_processor` cuando se ejecuta con un stub de `CacheWarmupService`.

## Impacto operativo

- El filesystem local deja de ser una dependencia de persistencia para el entrenamiento ML.
- El sistema mantiene degradacion controlada cuando no existe modelo local.
- La fuente de verdad para resultados y predicciones pasa a ser MongoDB, no los artefactos versionados del backend.

## Riesgos residuales

- En entornos sin `apscheduler`, el cron queda deshabilitado; el flujo diario sigue disponible via ejecucion directa.
- Una ejecucion real de `warmup_all_leagues.py` sigue requiriendo MongoDB disponible cuando se usan las fabricas reales de persistencia.

## Recomendacion para PR

Presentar este cambio como un `fix` de persistencia y robustez operativa del pipeline ML, no como un refactor cosmetico. El comportamiento observable cambia: los resultados de entrenamiento deben leerse desde MongoDB y no desde archivos locales.