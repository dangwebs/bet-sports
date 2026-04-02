# Tasks: API Decomposition

Lista de tareas accionables (ordenadas, con estimación y dependencias).

1. Inventario de `main.py` y routers
   - Descripción: listar modelos Pydantic, funciones y endpoints definidos en `main.py` y routers actuales.
   - Output: `/tmp/api_inventory.md` con mapping modelo→archivo.
   - Estimación: 2–3h
   - Dependencias: ninguno

2. Crear `backend/src/api/schemas/` y mover modelos
   - Descripción: mover modelos Pydantic detectados y actualizar imports.
   - Estimación: 3–5h
   - Dependencias: Inventario
   - AC: tests unitarios de serialización pasan.

3. Implementar `backend/src/api/mappers/`
   - Descripción: `prediction_mapper.py`, `league_mapper.py` con funciones puras y tests.
   - Estimación: 4–6h
   - Dependencias: `schemas/`

4. Crear `backend/src/application/use_cases/` y migrar lógica con efectos
   - Descripción: encapsular operaciones de persistencia y side-effects.
   - Estimación: 4–6h
   - Dependencias: mappers, repositorios

5. Refactorizar `backend/src/api/routers/*` para delegar a use-cases
   - Descripción: routers deben mapear request→schema→use_case→response.
   - Estimación: 3–4h
   - Dependencias: use_cases, mappers

6. Simplificar `main.py` y registrar routers
   - Descripción: dejar en `main.py` solo configuración (middleware, rate-limiter, registro de routers).
   - Estimación: 1–2h
   - Dependencias: routers refactorizados

7. Pruebas de contrato e integración
   - Descripción: ejecutar suite de tests y pruebas manuales en endpoints críticos.
   - Estimación: 2–4h

8. PRs incrementales y revisión
   - Descripción: fragmentar trabajo en PRs pequeños, cada uno con tests que aseguren no breaking changes.
   - Estimación: variable
