# Spec: API Decomposition

Resumen
-------
Descomponer el monolito HTTP en módulos claros: `schemas`, `mappers`, `services`, `routers` y `use_cases`. El objetivo es mejorar mantenibilidad, testabilidad y permitir que el resto de epics (testing, auto-labeling, ML traceability) se implementen con mínima fricción.

Objetivos
--------
- Extraer todos los modelos Pydantic de `main.py` a `src/api/schemas/`.
- Crear `src/api/mappers/` para convertir entre documentos DB y DTOs.
- Crear `src/api/services/` para lógica de consulta (thin adapters) que llaman a repositorios.
- Registrar routers por dominio en `src/api/routers/` y mantener contratos previos.
- Preservar compatibilidad de API: respuestas y formatos no deben cambiar sin versión.

Alcance
------
- Backend HTTP (FastAPI) dentro de `backend/src/api/`.
- No incluye cambios en `infrastructure/` repositorios salvo adaptadores mínimos.

Requisitos funcionales
----------------------
1. Todos los modelos expuestos por la API deben estar en `src/api/schemas/`.
2. Cada recurso debe tener un `APIRouter` propio dentro de `src/api/routers/`.
3. Las conversiones entre DB docs y schemas deben vivir en `src/api/mappers/`.
4. Las operaciones de orquestación deben delegar a `src/application/use_cases/`.
5. `main.py` debe limitarse a configurar middleware, rate-limiter y registrar routers.

Requisitos no funcionales
-------------------------
- Mantener cobertura de pruebas de contratos de API (tests existentes pasan).
- Cambios pequeños por commit, con mensajes claros (conventional commits).
- No introducir breaking changes sin bump de versión API.

Migración
---------
1. Crear `src/api/schemas/*` y copiar modelos actuales.
2. Implementar `mappers` y reemplazar uso directo de dicts en routers.
3. Registrar routers nuevos en `main.py` y ejecutar test-suite.
4. Hacer PR con cambio incremental y correr CI.

Aceptación
----------
- `pytest` pasa en CI.
- Endpoints existentes devuelven el mismo JSON (validados por tests de contrato).
- No hay imports circulares y `main.py` queda reducido a <200 líneas.

Desglose de tareas
------------------
1. Auditar `main.py` y extraer modelos (2–3h).
2. Implementar `schemas/` y `mappers/` (4–6h).
3. Crear `services/` adaptadores y ajustar routers (4h).
4. Escribir tests de contrato y ajustar (3–4h).

Riesgos y mitigaciones
----------------------
- Riesgo: import circulares → Mitigación: dependencias inversas vía interfaces y DI.
- Riesgo: rotura de frontend → Mitigación: tests contractuales y revisar manualmente endpoints críticos.
# Spec: API Decomposition (Epic 1)

Fecha: 2026-03-31

Resumen
-------
Romper el `main.py` monolítico en módulos bien definidos: `schemas/`, `mappers/`, `services/`, `routers/` y `application/use_cases/`. Mejorar testabilidad y separar responsabilidades para facilitar evolución del API y la instrumentación del pipeline de etiquetado.

Objetivos
---------
- Extraer todos los modelos Pydantic y esquemas a `src/api/schemas/`.
- Mover la lógica de transformación (mappers) a `src/api/mappers/`.
- Encapsular la lógica de negocio en `src/application/use_cases/`.
- Exponer rutas por dominio en `src/api/routers/` y mantener compatibilidad de contrato con clientes existentes.
- Añadir pruebas que verifiquen que los contratos permanezcan estables.

Alcance
-------
In-scope:
- Reorganización de código en el backend Python (carpeta `backend/src`).
- Creación de mappers y capas de servicio ligeras.
- Ajustes mínimos en `main.py` para incluir routers y middlewares.

Out-of-scope:
- Cambios a la API pública fuera de la compatibilidad hacia atrás.
- Modificaciones al frontend o despliegue.

Requisitos (REQ-1.x)
-------------------
- REQ-1.1: Mover todos los modelos/serializadores Pydantic a `src/api/schemas/`.
- REQ-1.2: Implementar mappers (`prediction_mapper.py`, `league_mapper.py`) bajo `src/api/mappers/` y exponer funciones puras, probables `map_doc_to_model()`.
- REQ-1.3: Crear use-cases en `src/application/use_cases/` para operaciones con efectos (guardar feedback, cargar predicciones, calcular stats).
- REQ-1.4: Cada dominio tendrá su `APIRouter` en `src/api/routers/` y será registrado desde `main.py`.
- REQ-1.5: Mantener compatibilidad del contrato (mismos campos JSON y códigos HTTP) y documentar cualquier cambio.

Aceptación
----------
- AC-1: `main.py` no debe contener modelos Pydantic ni lógica de negocio; solo configuración y registro de routers.
- AC-2: Los endpoints existentes deben pasar los tests actuales sin cambios en sus contratos.
- AC-3: Los mappers y use-cases tienen tests unitarios que cubren los caminos felices y errores críticos.

Tareas (desglose)
-----------------
1. Inventario: listar modelos y funciones actualmente en `main.py` y routers existentes.
2. Crear `src/api/schemas/` y mover modelos Pydantic.
3. Implementar `src/api/mappers/prediction_mapper.py` y `league_mapper.py`.
4. Crear `src/application/use_cases/` y mover lógica con efectos (feedback, persistencia).
5. Refactor `src/api/routers/*` para delegar a use-cases y mappers.
6. Ajustar `main.py`: registrar routers y mantener middlewares (rate-limiter, CORS).
7. Añadir tests unitarios para mappers y use-cases; garantizar que los tests de integración pasan.

Dependencias
------------
- `backend/src/infrastructure/repositories/*` (repositorio Mongo) para persistencia.
- Test fixtures y datos sintéticos para validar contratos.

Riesgos y mitigaciones
----------------------
- Riesgo: ruptura de contrato con clientes. Mitigación: correr test suite de integración antes y después; mantener stubs.
- Riesgo: tiempo de ejecución incremental por mala abstracción. Mitigación: perf-test en endpoints críticos.

Entregables
-----------
- `specs/api-decomposition/spec.md` (este archivo)
- Código reorganizado en `backend/src/api/{schemas,mappers,routers}`
- Tests asociados en `backend/tests/`

Estimación inicial
------------------
4–8 jornadas de ingeniería (depende de pruebas y correcciones detectadas).
