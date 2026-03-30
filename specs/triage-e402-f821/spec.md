# Spec: Correcciones E402 / F821 (Import order & nombres indefinidos)

Resumen
-------
Corregir incidencias reportadas por Ruff relacionadas con importaciones fuera de lugar (`E402`) y nombres indefinidos (`F821`).

Objetivo
--------
- Mover imports al tope de módulos cuando sea seguro.
- Ajustar imports condicionales con `if TYPE_CHECKING:` o `typing.TYPE_CHECKING` cuando corresponda.
- Corregir referencias a nombres indefinidos (`F821`) añadiendo imports faltantes o ajustando alcance/alcances.

Archivos prioritarios detectados
-------------------------------
- `backend/scripts/train_model_optimized.py` (9 incidencias)
- `backend/src/dependencies.py` (8 incidencias)
- `backend/scripts/orchestrator_cli.py` (3 incidencias)
- `backend/src/application/services/ml_training_orchestrator.py` (3 incidencias)
- `backend/src/application/use_cases/live_predictions_use_case.py` (3 incidencias)

Estrategia propuesta
--------------------
1. Triage rápido: para cada archivo, mover imports al inicio o envolver imports de tipo con `if TYPE_CHECKING:`.
2. Corregir nombres indefinidos: añadir imports faltantes o corregir referencias (preferir imports relativos del paquete).
3. Ejecutar `ruff check --select E402,F821` y `pytest` tras los cambios.
4. Mantener commits atómicos (un archivo por commit/PR).

Criterios de aceptación
----------------------
- `ruff check --select E402,F821` no reporta E402/F821 en los archivos modificados.
- Todas las pruebas unitarias pasan.

Tareas mínimas de implementación
-------------------------------
1. Crear rama `fix/imports/train_model_optimized` y mover/corregir imports.
2. Repetir para `dependencies.py` y otros archivos prioritarios.
3. Ejecutar lints y tests localmente; abrir PRs atómicas.
