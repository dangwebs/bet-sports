# Plan de implementación (1 semana)

## Objetivo de la semana

Entregar los artefactos de Spec Kit y avanzar con el pipeline mínimo para validar las acciones prioritarias: PRs atómicos para spec, ajustes de CI, ADRs y un piloto de refactor ligero.

## Resumen diario

- Día 1 (Lunes): Crear spec y abrir PR de spec. Preparar rama `spec/speckit-week-plan`.
- Día 2 (Martes): Revisar resultados de CI del PR de spec; crear PRs para ajustes de CI (time-outs, job-scopes) y ADR inicial.
- Día 3 (Miércoles): Ejecutar y arreglar fallos de tests y lint en backend y frontend. Añadir tests faltantes mínimos y arreglar errores críticos.
- Día 4 (Jueves): Implementación piloto de refactor (pequeños cambios de desacoplamiento, extracción de interfaces en backend) y PR asociado.
- Día 5 (Viernes): Validación final, recoger feedback, consolidar PRs, preparar notas de merge y checklist de despliegue.

## Criterios de entrega por día

- Día 1: PR con `specs/*` abierto; `todo` actualizado (`Crear spec` completado, `Generar plan` en progreso).
- Día 2: PRs de CI + ADR creados; link a cada PR en la tarea correspondiente.
- Día 3: Build/CI verde o lista de fallos documentada con owner y tarea para arreglar.
- Día 4: PR piloto creado mostrando patrón de refactor y pruebas unitarias asociadas.
- Día 5: Checklist completado, PRs listos para revisión final.

## Notas operativas

- Mensajes de commit en formato Conventional Commits.
- Activar `code-quality`, `clean-code` y `best-practices` en revisiones de PR.
- No mergear sin al menos una revisión y CI verde (salvo excepciones documentadas).
