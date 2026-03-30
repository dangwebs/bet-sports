# Especificación: Refactor C901 — `live_predictions_use_case.py`

## Resumen
Reducir la complejidad cognitiva de `execute()` y `_generate_prediction()` en `backend/src/application/use_cases/live_predictions_use_case.py`, eliminar `# noqa: C901` y refactorizar en helpers y unidades testeables.

## Contexto
El `LivePredictionsUseCase` incluye funciones asíncronas de alta complejidad que generan predicciones en vivo y preparan la respuesta DTO. Para mantener la mantenibilidad y cumplir con las reglas de lint, extraeremos lógica compleja en helpers y cubriremos con tests.

## Alcance
- Archivo objetivo: `backend/src/application/use_cases/live_predictions_use_case.py`.
- Añadir pruebas unitarias en `backend/tests/unit/test_live_predictions_use_case.py`.

## Objetivos
1. Eliminar `# noqa: C901` en las funciones mencionadas.
2. Extraer helpers: `_determine_data_sources()`, `_build_feature_batch()`, `_normalize_and_apply_probs()`, `_persist_and_cache_response()` y reducir `execute()` a orquestador.
3. Añadir tests unitarios para los helpers extraídos y un test de integración ligero con mocks.
4. Ejecutar `black`, `flake8` y `pytest`.

## Criterios de aceptación
- `live_predictions_use_case.py` no contiene `# noqa: C901`.
- Linters y tests pasan para los archivos modificados.

## Plan
1. Crear la spec (hecho).
2. Extraer helpers y reescribir `execute()` y `_generate_prediction()`.
3. Añadir tests unitarios.
4. Formatear y ejecutar linters/tests.
5. Commit con mensaje `refactor(c901): live_predictions_use_case — extract helpers and remove noqa`.

Procede a implementar según esta spec.