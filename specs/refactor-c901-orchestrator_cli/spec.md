# Especificación: Refactor C901 — `orchestrator_cli.py`

## Resumen
Reducir la complejidad cognitiva de la función `cmd_predict()` en `backend/scripts/orchestrator_cli.py`, eliminar `# noqa: C901` y refactorizar el código en unidades más pequeñas y testeables sin cambiar la interfaz CLI.

## Contexto
`orchestrator_cli.py` define comandos CLI asíncronos que orquestan predicciones y tareas complejas. `cmd_predict()` está marcado con `# noqa: C901` debido a su tamaño y complejidad.

## Alcance
- Archivo objetivo: `backend/scripts/orchestrator_cli.py`.
- Añadir pruebas unitarias en `backend/tests/unit/test_orchestrator_cli.py` (mocks donde sea necesario).
- Mantener los nombres y firma del CLI (click/argparse) sin cambios.

## Objetivos
1. Eliminar `# noqa: C901` de `cmd_predict()`.
2. Extraer responsabilidades en funciones pequeñas y explícitas:
   - `parse_predict_args()` si corresponde.
   - `prepare_services()` — inicialización de servicios necesarios.
   - `gather_upcoming_and_stats()` — obtención de próximos partidos y estadísticas.
   - `process_match_for_prediction()` — proceso por partido (aislar porción de lógica que puede testearse con inputs fakes).
   - `batch_and_persist_predictions()` — ensamblado y persistencia.
3. Añadir tests unitarios para los helpers extraídos y un test de integración ligero que valide el flujo principal con servicios mockeados.
4. Ejecutar `black`, `flake8` y `pytest` y dejar el archivo limpio sin `# noqa` relacionados a C901.

## Criterios de aceptación
- El archivo `backend/scripts/orchestrator_cli.py` no contiene `# noqa: C901`.
- `flake8 backend/scripts/orchestrator_cli.py` no genera advertencias de C901 ni errores de import/runtime.
- Nuevos tests unitarios pasan (`pytest` exit code 0).

## Riesgos y mitigaciones
- Ciclos de importación: usar importaciones locales dentro de helpers según sea necesario.
- Mocking extenso: usar fixtures y fakes en `backend/tests/unit/fixtures/`.

## Tareas (Plan de implementación)
1. Crear la especificación (hecho).
2. Extraer helpers y reescribir `cmd_predict()` para que orqueste solo.
3. Añadir tests unitarios para cada helper.
4. Ejecutar `black` y `flake8` y corregir avisos.
5. Ejecutar `pytest` y corregir fallos.
6. Commit con mensaje `refactor(c901): orchestrator_cli — extract helpers and remove noqa`.

## Estimación
- 1–3 horas dependiendo del tamaño del `cmd_predict()` y la cantidad de mocks necesarios.

---

Procederé a delegar la implementación al agente `Backend` para aplicar los cambios y ejecutar las verificaciones solicitadas.