# Especificación: Refactor C901 — `ml_training_orchestrator.py`

## Resumen
Reducir la complejidad cognitiva de la función `run_training_pipeline()` en `backend/src/application/services/ml_training_orchestrator.py`, eliminar `# noqa: C901` y refactorizar en helpers y unidades testeables.

## Contexto
El servicio `ml_training_orchestrator` contiene una función de orquestación larga que compone la canalización de entrenamiento por liga. Actualmente está marcada con `# noqa: C901`.

## Alcance
- Archivo objetivo: `backend/src/application/services/ml_training_orchestrator.py`.
- Añadir pruebas unitarias en `backend/tests/unit/test_ml_training_orchestrator.py` (usar mocks donde sea necesario).

## Objetivos
1. Eliminar `# noqa: C901` de `run_training_pipeline()`.
2. Extraer responsabilidades como `prepare_datasets()`, `execute_training_for_league()`, `evaluate_and_save_models()` y `generate_post_training_artifacts()`.
3. Añadir tests unitarios para los helpers.
4. Ejecutar `black`, `flake8` y `pytest`.

## Criterios de aceptación
- El archivo no contiene `# noqa: C901`.
- `flake8` y `pytest` pasan para los archivos modificados.

## Riesgos
- Dependencias transversales a servicios externos: usar importaciones locales y mocks en tests.

## Plan
1. Crear la spec (hecho).
2. Extraer helpers y reescribir `run_training_pipeline()` para que sea orquestador simple.
3. Añadir tests unitarios.
4. Formatear y correr linters/tests.
5. Commit local con mensaje `refactor(c901): ml_training_orchestrator — extract helpers and remove noqa`.

Procede a implementar según esta spec.