# Spec: Hardening del Rebuild Docker

Fecha: 2026-04-02

## Resumen

El stack local definido en `docker-compose.dev.yml` debe poder reconstruirse con `docker compose -f docker-compose.dev.yml up -d --build --force-recreate` sin fallar por errores TypeScript del frontend ni dejar servicios inestables por rutas/comandos incorrectos en Compose.

## Objetivo

Dejar trazada y operativa la configuracion de rebuild del stack portable y corregir los bloqueos actuales:

1. El build del frontend dentro de `Dockerfile.portable` debe compilar sin errores TypeScript.
2. El servicio `labeler` del compose debe arrancar de forma estable con un entrypoint existente y apto para ejecucion prolongada.
3. La forma correcta de reconstruir el stack debe quedar guardada en el repositorio para uso futuro.

## Requisitos

### REQ-DR-1: Rebuild reproducible
- La forma de reconstruir el stack Docker local debe quedar documentada o automatizada en el repositorio.
- Debe usar `docker compose -f docker-compose.dev.yml up -d --build --force-recreate` como comando canonico.

### REQ-DR-2: Build frontend limpio en imagen portable
- `Dockerfile.portable` debe poder completar la etapa `cd /workspace/frontend && npm run build` sin errores TypeScript originados en el codigo actual.
- Los cambios deben preservar el comportamiento esperado de la UI.

### REQ-DR-3: Servicio labeler estable
- El servicio `labeler` en `docker-compose.dev.yml` debe usar un script existente dentro de la imagen portable.
- El proceso debe ser apto para ejecucion continua y configurable via variables de entorno.

## Criterios de aceptacion

- AC-1: Los errores TypeScript que bloqueaban el build del frontend quedan resueltos.
- AC-2: El compose deja configurado un entrypoint valido para `labeler`.
- AC-3: La forma canonica de reconstruir las imagenes queda guardada en el repo.

## Fuera de alcance

- Rediseñar la arquitectura Docker completa.
- Corregir errores del frontend no relacionados con el build que bloqueaba `Dockerfile.portable`.
- Cambiar el comportamiento funcional del pipeline MLOps fuera de lo necesario para estabilizar el stack.
