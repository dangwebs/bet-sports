# Tasks: Manual Lint Fixes

1. Ejecutar linters y recolectar reportes
   - `npm run lint` (frontend), `pytest` + linters backend (flake8/pylint) según configuración.
   - Estimación: 1h

2. Clasificar errores en auto-fix / manual
   - Generar lista y agrupar por prioridad.
   - Estimación: 1h

3. Aplicar correcciones manuales por paquete
   - Backend primero (estabilidad), luego frontend.
   - Estimación: 2–4h

4. Ajustar reglas problemáticas y documentar excepciones
   - Estimación: 1h

5. Añadir check en CI para evitar regresiones
   - Estimación: 1h
