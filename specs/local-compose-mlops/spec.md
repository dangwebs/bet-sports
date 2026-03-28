# Spec: Entrenamiento MLOps local en Docker Compose y portabilidad

Fecha: 2026-03-28
Autor: Orchestrator

## Objetivo

Eliminar el entrenamiento diario dependiente de GitHub Actions y mover la ejecución de entrenamiento/predicción/top-picks a un flujo local encapsulado en Docker Compose, manteniendo portabilidad para ejecución en cualquier host con Docker.

## Alcance

- Definir un servicio de pipeline MLOps en `docker-compose.dev.yml` que use recursos de la máquina local.
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

## Requisitos no funcionales

- Seguir `RULES.md` (español, clean architecture, no secretos hardcodeados).
- No romper arranque existente del backend/frontend.
- Mantener compatibilidad con variables de entorno actuales.

## Criterios de aceptación

- `docker compose -f docker-compose.dev.yml --profile mlops run --rm mlops-pipeline` ejecuta cleanup + train + predict + top-picks.
- `run_dev_pipeline.sh` usa Docker Compose, no `.venv` local.
- Workflow `enterprise_daily_mlops.yml` deja de entrenar en Actions.
- README documenta claramente el nuevo flujo.
