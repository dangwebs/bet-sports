# Plan: Limpieza y validación de data_sources

1. Descubrimiento
   - Ejecutar `flake8 backend/ --format=default` para listar violaciones y priorizar archivos.
   - Identificar hasta 40 archivos con más violaciones en `backend/src/infrastructure/data_sources/`.

2. Preparación
   - Crear rama local `fix/cleanup-data-sources` (si procede).
   - Crear artefactos Speckit (spec, plan, tasks) — ya creados.

3. Iteración por archivo (por orden de mayor a menor violaciones)
   - Leer el archivo objetivo.
   - Aplicar correcciones: eliminar trailing/blank whitespace (W291/W293), quitar imports/vars no usados (F401/F841), arreglar indentación E111/E117 y saltos de línea E302/E305.
   - Ejecutar `flake8 backend/` para validar que las correcciones no introdujeron nuevas violaciones relevantes.
   - Ejecutar `cd backend && pytest -q`.
     - Si `pytest` pasa: hacer commit atómico del archivo con mensaje en español (Conventional Commits), y continuar con el siguiente archivo.
     - Si `pytest` falla: revertir los cambios del archivo, documentar el fallo en `specs/cleanup-data-sources/tasks.md` y continuar con el siguiente archivo.

4. Cierre
   - Ejecutar `flake8 backend/` y `cd backend && pytest -q` al terminar las iteraciones.
   - Generar un resumen con los commits realizados y los archivos revertidos.
