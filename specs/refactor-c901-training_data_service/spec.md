# Especificación: Refactor C901 — `training_data_service.py`

Objetivo
--------
Reducir la complejidad cognitiva (C901) en las funciones:

- `fetch_comprehensive_training_data`
- `_backfill_gap`

Sin cambiar la semántica ni la API pública del servicio.

Estrategia
---------
1. Extraer bloques lógicos en helpers privados dentro de la misma clase:
   - `_fetch_github_matches`
   - `_fetch_csv_for_league`
   - `_fetch_football_data_org_matches`
   - `_fetch_espn_matches`
   - `_fetch_openfootball_matches`
   - `_get_sortable_date`
   - `_backfill_via_football_data_org`
   - `_backfill_via_openfootball`
2. Reescribir `fetch_comprehensive_training_data` para orquestar llamadas a esos helpers.
3. Mantener lógica de backfill y fechas exactamente igual, solo moviendo trozos a métodos privados.
4. Ejecutar `ruff check --select C901` y `pytest` y arreglar cualquier regresión.

Criterios de aceptación
-----------------------
- `ruff check --select C901` no reporta C901 en `training_data_service.py`.
- Todos los tests pasan localmente.
- Cambios pequeños y con pruebas que aseguren comportamiento.

Notas
-----
Este spec es parte del plan de triage `specs/triage-c901/spec.md` y se crea para cumplir la política "specs-first" del proyecto.
