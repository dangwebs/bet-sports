# Spec: Refactor C901 (Complejidad excesiva)

Resumen
-------
Reducir la complejidad ciclomática de las funciones/métodos reportados por Ruff (C901).

Objetivo
--------
- Eliminar/simplificar las funciones/métodos que exceden el umbral de complejidad (valor actual: 10).
- Introducir helpers y/o clases de menor responsabilidad para mantener cobertura de tests.

Archivos detectados (prioridad alta)
-----------------------------------
- `backend/src/application/use_cases/use_cases.py` (6 incidencias)
- `backend/src/domain/services/prediction_service.py` (3 incidencias)
- `backend/src/infrastructure/data_sources/football_data_org.py` (3 incidencias)
- `backend/src/application/services/training_data_service.py` (2 incidencias)
- `backend/src/application/use_cases/live_predictions_use_case.py` (2 incidencias)

Estrategia propuesta
--------------------
1. Triage por archivo: crear una rama `refactor/c901/<archivo>` por cada archivo prioritario.
2. Extraer bloques lógicos en funciones privadas o clases auxiliares con responsabilidad única.
3. Añadir tests unitarios para los caminos extraídos antes de modificar la implementación original (cuando falten).
4. Mantener cambios atómicos y revertibles; cada PR debe abordar un único archivo o una superficie pequeña.
5. Verificar `ruff check` y `pytest` en cada PR.

Criterios de aceptación
----------------------
- `ruff check --select C901` no reporta C901 en los archivos modificados.
- Todas las pruebas unitarias pasan.
- Cambios revisados y fusionados en `feature/refactor` o ramas dedicadas.

Tareas mínimas de implementación
-------------------------------
1. Crear rama `refactor/c901/use_cases` y abrir PR con extracción de helpers.
2. Repetir para `prediction_service.py`, `football_data_org.py`, `training_data_service.py`, etc.
3. Ejecutar CI local (`ruff`, `black`, `isort`, `pytest`) y documentar los cambios en cada PR.

Notas
-----
Evitar la introducción de duplicación innecesaria; preferir composición y reutilización cuando aplique.
