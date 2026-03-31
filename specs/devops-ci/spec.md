# Spec: DevOps & CI

Resumen
-------
Establecer pipelines CI que garanticen calidad (lint, typecheck, tests, build) y publicar artefactos docker para entornos de staging/preview. Añadir checks que protejan la rama `main`/`develop`.

Objetivos
--------
- Pipeline GitHub Actions: `lint`, `typecheck`, `pytest`, `build`, `coverage`.
- Gate en PRs para evitar merges con tests fallidos o coverage decreciente.
- Imagenes Docker etiquetadas por commit SHA y canal (develop/main).

Requisitos funcionales
----------------------
1. `ci.yml` que ejecute pasos en Ubuntu con cache de pip/node.
2. Artefacto de cobertura subido (codecov o cobertura almacenada).
3. Job de nightly que corre backfills y smoke-tests en staging.

Desglose de tareas
------------------
1. Crear pipeline base en `.github/workflows/ci.yml` (3h).
2. Añadir job `nightly` para sanity-checks y backfills (2h).
3. Configurar Docker build/push para images (2h).

Aceptación
----------
- PR templates y pipeline en verde en la rama `develop`.
# Spec: DevOps & CI (Epic 6)

Fecha: 2026-03-31

Resumen
-------
Establecer pipelines reproducibles para linting, tests, build y deploy en CI; añadir jobs programados (nightly labeling orchestration), y políticas de calidad (coverage gates, security scanning).

Objetivos
---------
- Pipeline que ejecute `lint`, `type-check`, `pytest`, `build` y publique artefactos.
- Job nocturno/diario para ejecutar dry-run del labeler y recolectar métricas.

Requisitos (REQ-6.x)
-------------------
- REQ-6.1: GitHub Actions (o equivalente) con jobs `lint`, `test`, `build`, `publish`.
- REQ-6.2: Coverage threshold configurado y fallos en pipeline si se rompe.
- REQ-6.3: Job programado `nightly-labeler` que lanza script en entorno de staging.

Aceptación
----------
- AC-1: PRs muestran resultado de jobs y no pueden mergear si los gates fallan.
- AC-2: Nightly labeler produce artefactos (report CSV/JSON) disponibles en acciones.

Tareas
------
1. Añadir workflows: `.github/workflows/ci.yml` y `.github/workflows/nightly-labeler.yml`.
2. Configurar secrets y runners para staging.
3. Documentar cómo levantar localmente los jobs de CI.
