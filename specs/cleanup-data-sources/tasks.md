# Tasks: Limpieza de data_sources

1. Ejecutar `flake8` y generar lista priorizada de archivos en `backend/src/infrastructure/data_sources/`.
2. Procesar primer archivo: `backend/src/infrastructure/data_sources/football_data_org.py`.
   - Correcciones: trailing whitespace, blank lines, imports/vars no usados, indentación, E3xx fixes.
   - Validar con `flake8` y `pytest`.
   - Commit atómico o revert según resultado.
3. Repetir para siguientes archivos por orden de violaciones (hasta 40 archivos).
4. Recolectar resultados: commits, reverts, tests pasados/ fallidos.

Registro de acciones (se irá actualizando durante la ejecución):

 - [ ] 01 - football_data_org.py — pendiente
