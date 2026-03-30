# Plan: Limpieza incremental de `picks_service.py`

1. Discovery: ejecutar `flake8` para identificar errores actuales (ya realizado y reportado).
2. Crear spec/plan/tasks (hecho).
3. Eliminar imports no usados (commit atómico).
4. Eliminar espacios finales y líneas en blanco con espacios (commit atómico).
5. Corregir f-strings vacíos (`F541`) y redefinitions sencillas (`F811`) si se detectan casos claros.
6. Ejecutar `flake8 backend/src/domain/services/picks_service.py` y `pytest -q`.
7. Repetir hasta que las violaciones de bajo riesgo estén resueltas.
