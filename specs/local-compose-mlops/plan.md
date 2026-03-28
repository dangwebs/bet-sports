# Plan: Local Compose MLOps

## Fase 1: Infra Docker Compose

1. Extender `docker-compose.dev.yml` con:
   - `backend-api`
   - `frontend`
   - `mlops-pipeline` (perfil `mlops`)
2. Definir variables parametrizables (`N_JOBS`, `TRAIN_DAYS`, `PREDICT_LEAGUES`).

## Fase 2: Scripts operativos

1. Crear script interno de pipeline en backend para secuencia deterministic.
2. Actualizar `run_dev_pipeline.sh` para invocar servicio `mlops-pipeline` de Compose.

## Fase 3: CI/CD alignment

1. Modificar `.github/workflows/enterprise_daily_mlops.yml` para eliminar entrenamiento automático.
2. Dejar workflow manual/informativo de delegación local.

## Fase 4: Documentación y validación

1. Actualizar README con flujo local portable.
2. Validar sintaxis YAML y scripts shell.
