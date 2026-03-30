# Spec: Eliminar imports/variables no usados en MLTrainingOrchestrator

## Resumen
Eliminar imports y referencias no usadas en `backend/src/application/services/ml_training_orchestrator.py` para reducir ruido del linter (F401/F841) y mejorar la calidad del código.

## Alcance
- Archivo objetivo: `backend/src/application/services/ml_training_orchestrator.py`
- Cambios: eliminar imports no utilizados y ajustar el bloque de imports para seguir las convenciones del proyecto.

## Criterios de aceptación
- Flake8 no debe reportar F401/F841 para el archivo modificado.
- Las pruebas existentes deben seguir pasando (`pytest -q`).
- Commit atómico con mensaje conforme a Conventional Commits.

## Riesgos
- Riesgo bajo: solo se eliminan imports no usados. Si una importación parecía no usada pero era necesaria en tiempo de ejecución, ejecutar tests detectará fallos.
