# Spec: Limpieza segura en `picks_service.py`

## Resumen
Realizar una limpieza de bajo riesgo en `backend/src/domain/services/picks_service.py` para reducir ruido del linter y mejorar legibilidad.

## Alcance
- Archivo: `backend/src/domain/services/picks_service.py`
- Cambios permitidos (bajo riesgo):
  - Eliminar imports no usados (p.ej. `math` si no se usa).
  - Eliminar espacios en blanco finales y líneas en blanco con espacios (W291/W293).
  - Corregir declaraciones claramente duplicadas o redefinitions (F811) cuando sea obvio y seguro.
  - Corregir f-strings vacíos (F541) si se detecta texto estático.

No se harán refactors de lógica ni reformat completos que puedan cambiar comportamiento sin pruebas adicionales.

## Criterios de aceptación
- Flake8 no debe reportar F401 (imports no usados) ni F541 en el archivo.
- Cambios atómicos, cada commit con mensaje `refactor(picks): <acción corta>`.
- `pytest -q` sigue pasando (o al menos no introduce errores nuevos en la suite actual).
