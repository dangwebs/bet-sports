# Plan: Local Compose MLOps

## Fase 1: Imagen portable del proyecto

1. Crear una imagen única del proyecto con Python + Node.
2. Incluir dentro de la imagen backend, frontend y utilidades MLOps.

## Fase 2: Infra Docker Compose

1. Extender `docker-compose.dev.yml` con:
   - `backend-api`
   - `frontend`
   - `mlops-pipeline` (perfil `mlops`)
2. Reutilizar la misma imagen del proyecto en los servicios principales.
3. Definir variables parametrizables (`N_JOBS`, `TRAIN_DAYS`, `PREDICT_LEAGUES`).

## Fase 3: Scripts operativos

1. Crear script interno de pipeline en backend para secuencia deterministic.
2. Actualizar `run_dev_pipeline.sh` para invocar servicio `mlops-pipeline` de Compose.

## Fase 4: CI/CD alignment

1. Modificar `.github/workflows/enterprise_daily_mlops.yml` para eliminar entrenamiento automático.
2. Dejar workflow manual/informativo de delegación local.

## Fase 5: Documentación y validación

1. Actualizar README con flujo local portable.
2. Validar sintaxis YAML y scripts shell.
3. Validar que Compose no requiera bind mounts del código del host.
