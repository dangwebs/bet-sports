# Especificación: Refactor C901 — `train_model_optimized.py`

## Resumen
Reducir la complejidad cognitiva de la función `main()` en `backend/scripts/train_model_optimized.py`, eliminar la línea `# noqa: C901` y refactorizar el código en unidades más pequeñas y testeables sin cambiar el comportamiento externo ni la interfaz CLI.

## Contexto
El script contiene una función `async def main()` muy grande y compleja (marca C901). Actualmente se silencia la advertencia con `# noqa: C901`. Para mantener la calidad de código y cumplir con las reglas de lint del proyecto, debemos extraer responsabilidades en helpers y agregar tests unitarios.

## Alcance
- Archivo objetivo: `backend/scripts/train_model_optimized.py`.
- Añadir pruebas unitarias en `backend/tests/unit/test_train_model_optimized.py` o `backend/tests/unit/test_train_scripts.py`.
- No se deben cambiar las opciones del CLI ni el contrato externo (argumentos, ficheros de salida, formato de modelos guardados).

## Objetivos
1. Eliminar `# noqa: C901` de `main()`.
2. Extraer las siguientes responsabilidades en funciones separadas y con tipos/annotations claras:
   - `parse_args()` — parseo de CLI y saneamiento.
   - `init_services(weights)` — inicialización de servicios y singletons necesarios para el worker/ejecución.
   - `clear_stale_predictions(repo)` — limpieza de predicciones antiguas en la BD.
   - `group_matches_by_league(matches)` — agrupado y ordenación.
   - `train_for_league(league_id, league_matches, services, args)` — encapsula la lógica de extracción de features y entrenamiento por liga.
   - `generate_league_predictions(...)` — moverla a nivel de módulo (no anidada) y pasarle explícitamente los servicios/depencias que usa.
3. Añadir tests unitarios para los helpers extraídos (parsers, groupers, y parte de la lógica de `process_match_task`) y tests básicos de integración que no requieran acceso a la DB real (usar mocks/fakes).
4. Ejecutar `flake8` y `pytest` y dejar el archivo libre de supresiones `# noqa` relacionadas con C901.

## Criterios de aceptación
- `backend/scripts/train_model_optimized.py` no contiene `# noqa: C901`.
- `flake8 backend/scripts/train_model_optimized.py` no genera advertencias sobre C901 ni errores nuevos (F821, E402, etc.).
- Nuevos tests unitarios pasan (`pytest` exit code 0).
- Comportamiento CLI intacto (smoke test cronológico: `--days` y `--league` funcionan igual).

## Riesgos y mitigaciones
- Dependencias globales / ciclos de importación: usar importaciones locales dentro de funciones cuando sea necesario.
- Tiempo de ejecución del script: los cambios son refactorings, no deben afectar la lógica de negocio.
- Cobertura de tests: añadir tests unitarios para los helpers críticos; dejar pruebas integradas fuera de este cambio salvo que existan fixtures.

## Tareas (Plan de implementación)
1. Crear esta especificación (hecho).
2. Añadir tests unitarios iniciales (mocks) para `parse_args()` y `group_matches_by_league()`.
3. Extraer helpers y mover `generate_league_predictions` a módulo.
4. Iterar flake8 / black hasta dejar el archivo limpio.
5. Ejecutar `pytest` y corregir fallos.
6. Preparar commit con mensaje `refactor(c901): train_model_optimized — extract helpers and remove noqa`.

## Estimación
- 2–4 horas de desarrollo dependiendo de la cantidad de micro-refactors y tests necesarios.

---

Si estás de acuerdo, delego la implementación al especialista `backend` para ejecutar las tareas 2–5 según este spec. ¿Procedo a delegar e implementar ahora?