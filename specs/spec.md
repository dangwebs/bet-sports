# Spec: Plan de implementación semanal (Speckit)

Fecha: 27 de marzo de 2026
Autor: Orquestador (Copilot)

## Resumen ejecutivo

Esta especificación define el alcance, objetivos y criterios de aceptación para la entrega de los artefactos del Spec Kit necesarios para poner en marcha la semana de trabajo priorizada: `specs/spec.md`, `specs/plan.md` y `specs/tasks.md`.

## Contexto

Durante la revisión arquitectónica se detectaron varias acciones prioritarias: alinear agentes e instrucciones a `RULES.md`, asegurar cumplimiento de CI, generar artefactos de especificación (Spec Kit) y preparar PRs atómicos para validar cambios. Esta especificación formaliza esa iniciativa y define entregables y criterios de éxito.

## Objetivo

- Producir los artefactos de Spec Kit para la ejecución de la semana: especificación, plan y lista de tareas.
- Abrir PRs atómicos con los cambios necesarios (spec + plan + tasks) y preparar PRs secundarios para CI, ADRs y refactor necesarios.

## Alcance

- Crear y versionar en el repositorio los archivos: `specs/spec.md`, `specs/plan.md`, `specs/tasks.md`.
- Crear una rama dedicada y abrir PR con los artefactos.
- Generar el plan de implementación (una semana) y la lista de tareas accionables.

No incluye: cambios de código en producción, despliegues, ni merges automáticos sin revisión.

## Requisitos

- Seguir las reglas de `RULES.md` (idioma, procesos de Orquestador, Spec Kit).
- Cumplir las guías de `code-quality`, `clean-code` y `best-practices` para cualquier cambio que se proponga posteriormente.
- PRs atómicos y con mensajes en formato Conventional Commits.

## Criterios de aceptación

- Los tres archivos (`spec.md`, `plan.md`, `tasks.md`) existen bajo `specs/` y siguen la plantilla mínima aquí definida.
- Existe una rama remota `spec/speckit-week-plan` con un PR abierto apuntando a `main` que incluye los artefactos.
- El `todo` del Speckit refleja el estado: spec creado y plan en progreso.

## Entregables

- `specs/spec.md` (esta especificación)
- `specs/plan.md` (plan diario para la semana)
- `specs/tasks.md` (lista de tareas accionables con criterios de aceptación)
- PR en GitHub con los archivos anteriores (branch: `spec/speckit-week-plan`)

## Dependencias

- Acceso push al repositorio remoto y permisos para crear PRs.
- Disponibilidad de `gh` CLI para crear PRs (si está ausente, se empuja la rama y se notifica).

## Riesgos

- Fallos en CI al ejecutar linters/tests: mitigación — ejecutar localmente y arreglar antes de pedir revisión.
- Permisos insuficientes para crear ramas o PRs: mitigación — instruir al mantenedor para crear PR manualmente.

## Validación

- Comprobar `git status` y que los archivos estén en la rama creada.
- Ejecutar linters y tests relevantes según corresponda (ej.: `cd backend && pytest -v`, `cd frontend && npm run lint`).

---

En caso de dudas, preguntar al propietario del repositorio antes de promover cambios a `main`.
