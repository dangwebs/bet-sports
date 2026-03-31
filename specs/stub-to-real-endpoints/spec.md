# Spec: Stub → Real Endpoints

Resumen
-------
Convertir endpoints actualmente con respuestas stub en implementaciones completas alineadas a `use_cases` y persistencia real. Prioridad alta: endpoints usados por frontend y pipeline de auto-labeling.

Prioridad (orden)
-----------------
1. `GET /api/v1/matches/daily`  — alimentar auto-labeler y UI.
2. `GET /api/v1/matches/team/{team}` — búsqueda y listados.
3. `GET /api/v1/suggested-picks/match/{match_id}` — estructura de picks.
4. `POST /api/v1/suggested-picks/feedback` — persistir feedback (learning).
5. `GET /api/v1/suggested-picks/learning-stats` — resumen de learning.

Requisitos funcionales
----------------------
- Cada endpoint debe delegar a un `UseCase` en `src/application/use_cases`.
- Validaciones de inputs y errores HTTP claros (400/404/500).
- Operaciones idempotentes donde aplique (feedback duplicates).

Requisitos no funcionales
-------------------------
- Latencia objetivo: <150ms en promedio para endpoints read-only en staging.
- Logging estructurado para requests/response de endpoints críticos.

Aceptación
----------
- Tests de integración que validen comportamiento con repositorios en memoria/mocks.
- Frontend no requiere cambios para consumir nuevos endpoints (compatibilidad).

Desglose de tareas
------------------
1. Implementar `GetDailyMatchesUseCase` y adaptadores (3–4h).
2. Integrar `GET /matches/daily` router a use case y escribir tests (2–3h).
3. Implementar `RegisterFeedbackUseCase` (persistencia, dedupe) (3–4h).
4. Implementar `learning-stats` con consulta agregada (2h).

Riesgos
-------
- Datos incompletos para `daily` → Mitigación: fallback y flags de warned-data.
# Spec: Stub→Real Endpoints (Epic 3)

Fecha: 2026-03-31

Resumen
-------
Convertir los endpoints `stub` existentes en implementaciones completas que llamen a use-cases y repositorios reales. Garantizar contratos estables y cobertura de pruebas.

Objetivos
---------
- Implementar endpoints: `/matches/daily`, `/matches/team/{team_name}`, `/predictions/...`, `/api/v1/suggested-picks/feedback`, `/api/v1/suggested-picks/learning-stats`.
- Reemplazar retornos por defecto por llamadas a `application.use_cases` y `infrastructure.repositories`.

Requisitos (REQ-3.x)
-------------------
- REQ-3.1: `/matches/daily` devuelve partidos del día con predicciones adjuntas cuando existan.
- REQ-3.2: `/matches/team/{team_name}` busca por coincidencia de nombre (canónico + alias fuzzy) y devuelve partidos filtrados.
- REQ-3.3: `/suggested-picks/feedback` invoca `RegisterFeedbackUseCase` y persiste cambios mediante `LearningService`.
- REQ-3.4: `/learning-stats` lee desde `LearningService` y devuelve resumen por mercado.
- REQ-3.5: Todos los endpoints incluyen trazabilidad `request_id` y timestamps UTC ISO.

Aceptación
----------
- AC-1: Tests de integración demuestran que endpoints llaman a los use-cases y retornan JSON esperado.
- AC-2: Endpoints mantienen contratos (nombres y tipos de campos).

Tareas
------
1. Inventariar stubs existentes y mapear al use-case objetivo.
2. Implementar adaptadores entre routers y `application.use_cases`.
3. Añadir validaciones de entrada (Pydantic) y manejo de errores uniforme.
4. Escribir tests de integración que mockeen repositorios y verifiquen call-graph.
