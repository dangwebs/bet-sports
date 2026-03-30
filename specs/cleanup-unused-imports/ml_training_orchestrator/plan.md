# Plan: Limpieza atómica de imports en MLTrainingOrchestrator

1. Discovery: verificar el archivo objetivo y confirmar las importaciones reportadas por flake8.
2. Crear artefactos de spec/plan/tasks (hecho).
3. Aplicar cambio atómico en `ml_training_orchestrator.py` eliminando imports no usados.
4. Ejecutar `flake8` en el archivo y luego `pytest -q` en `backend/`.
5. Si todo pasa, commitear con mensaje: `refactor(ml): remove unused imports in ml_training_orchestrator`.
6. Repetir para otros archivos de bajo riesgo según reporte F401/F841.
