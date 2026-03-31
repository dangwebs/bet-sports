# Spec: Testing Foundation

Resumen
-------
Establecer una base de pruebas reproducible y con cobertura mínima para asegurar regresiones y permitir refactor seguro. Incluye frameworks, convenciones, fixtures y objetivos de cobertura por capa (domain, application, integration).

Objetivos
--------
- Definir y documentar la estrategia de pruebas (unit, integration, contract, e2e).
- Implementar fixtures reutilizables y factories para datos.
- Objetivos de cobertura: Domain ≥ 85%, Application ≥ 80%, Integration ≥ 70% (meta progresiva).
- Integrar ejecución de tests en CI con reporte de coverage.

Alcance
------
- Código Python en `backend/src/` y tests en `backend/tests/`.
- No incluye frontend e2e (se puede añadir después).

Requisitos funcionales
----------------------
1. `pytest` con plugins necesarios (`pytest-asyncio`, `pytest-mock`, `coverage`).
2. Fixtures en `backend/tests/conftest.py` para cliente TestClient, DB mock, time-freeze.
3. Factories para crear matches/predictions en `backend/tests/factories/`.
4. Tests contractuales que validen shape de respuestas de endpoints críticos.

Requisitos no funcionales
-------------------------
- Tests reproducibles y rápidos: unit tests <100ms cada uno idealmente.
- Documentación de cómo ejecutar tests localmente y en CI.

Aceptación
----------
- `pytest -q` pasa localmente con exit code 0.
- CI bloquea merges si cobertura desciende por debajo del umbral configurado.

Desglose de tareas
------------------
1. Añadir `backend/tests/conftest.py` con fixtures principales (1–2h).
2. Implementar factories y helpers para datos de prueba (2–3h).
3. Convertir tests existentes a usar fixtures (2–4h).
4. Configurar coverage y reporte en CI (2h).

Riesgos
-------
- Datos de prueba frágiles → Mitigación: factories y fixtures centralizados.
# Spec: Testing Foundation (Epic 2)

Fecha: 2026-03-31

Resumen
-------
Establecer una base de pruebas robusta que permita confiar en cambios refactorizados y acelerar desarrollo seguro. Abarca pruebas unitarias (dominio), pruebas de aplicación (use-cases) y pruebas de integración (endpoints), plus infra de CI para ejecutarlas.

Objetivos
---------
- Definir objetivos de cobertura por capa y configurar herramientas (`pytest`, `pytest-cov`, `factory_boy`).
- Añadir fixtures reutilizables y mocks para `Mongo` y servicios externos.
- Integrar ejecución de pruebas en CI con gates de cobertura.

Requisitos (REQ-2.x)
-------------------
- REQ-2.1: Cobertura objetivo mínima por capa (ejemplo: dominio >= 70%, aplicación >= 60%, integración >= 40%).
- REQ-2.2: Crear fixtures para datos de partido/predicción en `tests/fixtures/`.
- REQ-2.3: Añadir tests de contracto para endpoints críticos (`/matches/daily`, `/suggested-picks/feedback`).
- REQ-2.4: Documentar cómo ejecutar tests localmente y en CI.

Aceptación
----------
- AC-1: `pytest` se ejecuta localmente sin errores con entorno virtual estándar.
- AC-2: CI incorpora job que corre tests y falla el pipeline si la cobertura global baja del umbral definido.

Tareas
------
1. Añadir `tests/conftest.py` con fixtures principales (TestClient, fake DB, clock control).
2. Implementar factories y fixtures para partidos, equipos y predicciones.
3. Escribir tests unitarios para mappers, servicios y use-cases recién creados.
4. Añadir tests de integración para routers clave.
5. Configurar job de CI que ejecute `pytest --cov` y publique reportes.

Herramientas y convenciones
---------------------------
- `pytest`, `pytest-mock`, `pytest-asyncio` si aplica, `factory_boy` o `model_bakery`.
- Uso de fixtures de alcance `session` para recursos caros.

Riesgos
-------
- Riesgo: tests frágiles por datos reales cambiantes. Mitigación: usar datos sintéticos y control temporal (time-freeze).
