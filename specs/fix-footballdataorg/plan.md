# Plan de trabajo

1. Discovery: identificar exactamente qué funciones están duplicadas y cuáles son las implementaciones canónicas.
2. Especificación: (este spec) definir alcance y criterios de aceptación.
3. Implementación atómica:
   - Eliminar definiciones duplicadas conservando la versión correcta.
   - Normalizar retornos (usar listas vacías en lugar de `None` cuando corresponde).
   - Corregir errores de indentación y estilo mínimos que impidan `black`/`flake8`.
4. Validación:
   - `python -m py_compile` sobre el archivo.
   - `flake8` y `black`.
   - `pytest -q`.
5. Commit atómico con mensaje `fix(data-source): unificar football_data_org.py y corregir lint`.
