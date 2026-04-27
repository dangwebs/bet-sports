# Tasks — Excelencia de Validación Full-Stack

## Preparación
- [x] Inspeccionar workflows, hooks y scripts actuales.
- [x] Identificar el gap entre validación local y CI.
- [x] Crear spec, plan y tasks del cambio.

## Implementación
- [x] Crear `scripts/quality_gate.sh` como comando canónico full-stack.
- [x] Hacer que `scripts/local_checks.sh` delegue al comando canónico o replique su flujo.
- [x] Actualizar `docs/developer-linting.md` con el comando fuente de verdad.

## Verificación
- [ ] Ejecutar el gate canónico completo.
- [x] Registrar las familias de fallos resultantes.
- [x] Corregir la primera familia crítica seleccionada.
- [ ] Reejecutar el gate afectado y luego el gate completo.

## Seguimiento
- [ ] Dejar documentado el estado exacto de la deuda restante.
- [ ] Preparar la siguiente iteración: tipado y refactor de complejidad.