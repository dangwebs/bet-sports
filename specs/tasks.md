# Lista de tareas accionables

Cada tarea debe convertirse en un issue/PR si procede. Marcar responsable y estimación.

1. Crear spec (speckit.specify)
   - Estado: ✅ Completado
   - Responsable: Orquestador
   - Estimación: 1h
   - Criterio de aceptación: `specs/spec.md` añadido y PR abierto con la rama `spec/speckit-week-plan`.

2. Generar plan (speckit.plan)
   - Estado: ✅ Completado
   - Responsable: Orquestador + Dev
   - Estimación: 1h
   - Criterio de aceptación: `specs/plan.md` añadido y tareas delegadas en `specs/tasks.md`.

3. Crear PR para ajustes de CI
   - Estado: ✅ Completado (cambios aplicados en workflow)
   - Responsable: Dev
   - Estimación: 2h
   - Criterio de aceptación: PR con cambios de configuración y `ci` en el mensaje de commit; pruebas iniciales pasan o se documentan fallos.

4. Crear ADR para decisiones relevantes
   - Estado: ✅ Completado
   - Responsable: Arquitecto/Dev
   - Estimación: 1h
   - Criterio de aceptación: `docs/adr/` contiene el ADR con contexto y decisión.

5. Arreglar fallos de lint/tests (backend/frontend)
    - Estado: ✅ Completado
   - Responsable: Dev
   - Estimación: 4h
   - Criterio de aceptación: CI pasa o hay tareas pendientes con due owners asignados.
   - Evidencia:
     - Frontend lint: OK (requiriendo `frontend/eslint.config.js`).
     - Frontend build: OK.
     - Frontend tests: 7/7 passing.
       - Backend pytest: 3/3 passing (`backend/tests/unit/test_time_utils.py`).

6. Implementación piloto (refactor ligero)
    - Estado: ✅ Completado
   - Responsable: Dev
   - Estimación: 6h
   - Criterio de aceptación: PR con refactor pequeño que demuestra la estrategia (ej.: extraer interfaz para repositorio, añadir tests unitarios).
    - Evidencia:
       - Refactor en `backend/src/utils/time_utils.py` (eliminación de import inline, conversión explícita UTC -> Colombia).
       - Tests unitarios nuevos en `backend/tests/unit/test_time_utils.py`.

7. Validación final y merge readiness
   - Estado: ✅ Completado
   - Responsable: Orquestador/Dev
   - Estimación: 2h
   - Criterio de aceptación: Checklist completado, PRs con reviewers, CI verde o plan de mitigación aceptado.
   - Evidencia:
     - Checklist generado: `specs/merge-readiness-checklist.md`.
     - PR #14 abierto y limpio (`mergeStateStatus: CLEAN`).
     - Check reportado: `GitGuardian Security Checks` en `SUCCESS`.
