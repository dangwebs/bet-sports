# Spec: Optimizacion de recursos Docker

Fecha: 2026-04-02

## Resumen

El stack local definido en `docker-compose.dev.yml` debe consumir menos CPU, memoria y espacio de imagen en el flujo de desarrollo diario, sin romper el arranque base de `mongodb`, `backend-api` y `frontend` ni el pipeline MLOps manual.

## Objetivo

Reducir el costo operativo del stack portable con cambios de bajo riesgo:

1. El arranque por defecto no debe levantar jobs periodicos opcionales.
2. El pipeline MLOps manual debe usar defaults de CPU mas conservadores.
3. El contexto de build Docker no debe incluir entornos virtuales, modelos ni caches locales que inflan la imagen sin aportar al runtime.

## Requisitos

### REQ-DRO-1: Stack base mas liviano
- `docker compose -f docker-compose.dev.yml up -d` debe enfocarse en el stack base de desarrollo.
- Los servicios periodicos (`ml-worker`, `labeler`, `updater`) deben poder levantarse de forma opt-in mediante profile o comando explicito.

### REQ-DRO-2: Pipeline MLOps con defaults conservadores
- `run_dev_pipeline.sh` no debe consumir por defecto todos los CPUs del host.
- Debe seguir permitiendo override via `N_JOBS`.

### REQ-DRO-3: Contexto Docker reducido
- `.dockerignore` debe excluir entornos virtuales, modelos locales, caches, artefactos y secretos que no son necesarios dentro de la imagen portable.
- El cambio debe reducir el riesgo de copiar archivos pesados o sensibles al build context.

### REQ-DRO-4: Documentacion operativa clara
- `README.md` debe diferenciar entre stack base y servicios opcionales de automatizacion.
- Debe quedar claro como levantar el profile adicional cuando se necesiten jobs periodicos.

## Criterios de aceptacion

- AC-1: El compose deja definidos los servicios periodicos como opt-in.
- AC-2: El pipeline manual reduce su agresividad de CPU por defecto sin perder parametrizacion.
- AC-3: `.dockerignore` cubre los directorios locales mas pesados detectados (`venv`, `.venv`, `ml_models`, caches y artefactos locales equivalentes).
- AC-4: La documentacion refleja el nuevo flujo de uso.

## Fuera de alcance

- Reescribir el stack a multi-stage runtime separado por servicio.
- Cambiar el comportamiento funcional del backend o del frontend.
- Ejecutar rebuilds completos como parte de esta intervencion.