# Spec: Remover supresiones/errores C901 (complejidad)

Estado: draft
Owner: Orchestrator

Objetivo
--------
Reducir la complejidad ciclomática reportada por `ruff` (C901) en funciones críticas del backend, garantizando que los cambios sean cubiertos por tests y se realicen en commits atómicos y revertibles.

Alcance inicial
----------------
- `backend/src/application/use_cases/suggested_picks_use_case.py`
- `backend/src/application/use_cases/suggested_picks_use_case.py`
- `backend/src/application/use_cases/suggested_picks_use_case.py`
- Lista completa se obtendrá con: `.venv/bin/ruff check . --select C901 --format=json`

Criterios de aceptación
-----------------------
- `ruff check .` ya no debe reportar C901 en los archivos abordados.
- Las pruebas unitarias existentes y nuevas pasan localmente (`pytest -q`).
- Cada refactor se realiza en una rama por cada archivo grande: `refactor/c901/<file>`.

Estrategia y pasos
------------------
1. Discovery
   - Ejecutar: `.venv/bin/ruff check . --select C901 --format=json` para obtener el listado exacto de ubicaciones y funciones.
   - Generar un `triage-c901.json` con la lista priorizada (por número de referencias y por cobertura de tests).

2. Priorización
   - Priorizar primero funciones que 1) tienen tests, 2) no tocan I/O crítico, 3) son tratables con extracción de helpers.

3. Para cada archivo/función priorizada:
   a. Añadir tests unitarios que cubran el comportamiento actual (características y edge-cases).
   b. Extraer bloques lógicos a funciones auxiliares pequeñas con nombres descriptivos.
   c. Mantener la interfaz pública de la función (sin cambiar contractos) cuando sea posible.
   d. Ejecutar `ruff check` y `pytest` tras cada cambio menor.
   e. Commit atómico y abrir PR con description: "refactor(c901): <archivo> - extraer <componentes>".

4. Revisión
   - Revisión de PR centrada en comportamiento (tests) y legibilidad.

5. Cierre
   - Una vez todos los C901 del scope resueltos, actualizar `pyproject.toml` si se aplicaron cambios de configuración y cerrar la spec.

Riesgos y mitigaciones
----------------------
- Riesgo: cambios comportamentales indeseados. Mitigación: escribir tests antes de refactor.
- Riesgo: scope demasiado amplio. Mitigación: ramas por archivo y PRs pequeños.

Tareas iniciales (por hacer)
---------------------------
- [ ] Ejecutar `ruff --select C901` y crear `specs/remove-c901/triage-c901.json`.
- [ ] Crear rama `refactor/c901/triage` y subir el JSON.
- [ ] Para top-3 archivos, crear tareas individuales y asignarlas.

Notas
-----
- No se deben añadir supresiones globales (`# noqa: C901`) salvo justificación en este spec.
- Si una función es inherentemente compleja por construcción y no es práctica la extracción, documentarlo y marcar como excepción temporal con una tarea de seguimiento.