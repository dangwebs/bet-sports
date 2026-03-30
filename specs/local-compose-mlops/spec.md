# Spec: Entrenamiento MLOps local en Docker Compose y portabilidad

Fecha: 2026-03-28
Autor: Orchestrator

## Objetivo

Eliminar el entrenamiento diario dependiente de GitHub Actions y mover la ejecución de entrenamiento/predicción/top-picks a un flujo local encapsulado en Docker Compose, usando una imagen única del proyecto que contenga backend, frontend y utilidades MLOps para maximizar portabilidad en cualquier host con Docker.

## Alcance

- Definir una imagen portable del proyecto con runtime Python + Node y todo el código necesario.
- Definir servicios `backend-api`, `frontend` y `mlops-pipeline` en `docker-compose.dev.yml` reutilizando esa imagen.
- Ajustar scripts para ejecutar el pipeline desde Docker Compose.
- Remover el entrenamiento automático de GitHub Actions (dejar solo workflow informativo/manual).
- Actualizar documentación operativa para uso local y despliegue portable.

## Fuera de alcance

- Reescritura completa de backend a un único motor de base de datos.
- Cambios funcionales de UI.
- Orquestación Kubernetes.

## Requisitos funcionales

1. Debe existir una forma de ejecutar entrenamiento completo con un comando local único basado en Compose.
2. El pipeline debe permitir parametrizar CPU (`N_JOBS`) y días (`TRAIN_DAYS`) sin tocar código.
3. GitHub Actions no debe ejecutar entrenamiento de modelo.
4. El proyecto debe poder levantarse de forma portable con contenedores (servicios base + pipeline bajo perfil).
5. Backend, frontend y entrenamiento deben vivir dentro de la imagen/stack Docker del proyecto, sin requerir bind mounts de código del host para funcionar.

## Requisitos no funcionales

- Seguir `RULES.md` (español, clean architecture, no secretos hardcodeados).
- No romper arranque existente del backend/frontend.
- Mantener compatibilidad con variables de entorno actuales.

## Criterios de aceptación

- `docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline` ejecuta cleanup + train + predict + top-picks.
- `run_dev_pipeline.sh` usa Docker Compose, no `.venv` local.
- Workflow `enterprise_daily_mlops.yml` deja de entrenar en Actions.
- README documenta claramente el nuevo flujo.
