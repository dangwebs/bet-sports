# Spec: System Health Uplift — De 6.5 a 8.5+

**Fecha**: 2026-03-31
**Estado**: Draft
**Autor**: Orchestrator
**Evaluación actual**: 6.5/10
**Objetivo**: 8.5/10

---

## Resumen ejecutivo

Este spec define las intervenciones necesarias para llevar el sistema BJJ-BetSports de su estado actual (6.5/10) a un objetivo de 8.5+/10. Se organiza en **6 epics** priorizados por impacto y dependencias, cada uno con requerimientos, criterios de aceptación, y estimación de esfuerzo relativo.

La evaluación actual arrojó:

| Área | Nota actual | Nota objetivo |
|------|-------------|---------------|
| Arquitectura | 7 | 8.5 |
| API Completeness | 6 | 8.5 |
| Modelo de Dominio | 7 | 8 |
| Infraestructura | 7 | 8.5 |
| **Testing** | **3** | **8** |
| Frontend | 7 | 8 |
| DevOps | 8 | 9 |
| ML Pipeline | 7 | 8 |
| Auto-labeling | 5 | 8 |
| Calidad de Código | 6 | 8.5 |
| Documentación | 8 | 9 |
| **Promedio** | **6.5** | **8.5** |

---

## Dependencias entre Epics

```
Epic 1 (API Decomposition)
    ↓
Epic 2 (Testing Foundation) ← depende de routers separados para test por módulo
    ↓
Epic 3 (Stub Endpoints) ← depende de tests como red de seguridad
    ↓
Epic 4 (Auto-labeling Pipeline) ← depende de endpoints funcionales
    ↓
Epic 5 (Frontend Hardening) ← puede ir en paralelo con 3-4
    ↓
Epic 6 (DevOps & Compliance) ← cierra el ciclo, valida todo en CI
```

---

## Epic 1: API Decomposition — Descomponer `main.py`

**Impacto**: Arquitectura 7→8.5, Calidad 6→7.5
**Esfuerzo**: M (medio)
**Reglas RULES.md afectadas**: §4 (SOLID/SRP)

### Problema

`backend/src/api/main.py` tiene 509 líneas con 13 modelos Pydantic, ~10 helpers, y 15 endpoints mezclados en un único archivo. Viola SRP masivamente y dificulta testing unitario, navegación, y mantenimiento.

### Requerimientos

#### REQ-1.1: Extraer modelos Pydantic a `src/api/schemas/`

Mover los 13 modelos Pydantic definidos inline en `main.py` a archivos organizados por dominio:

| Modelo(s) | Destino |
|-----------|---------|
| `LeagueModel`, `CountryModel` | `src/api/schemas/leagues.py` |
| `TeamModel`, `MatchModel`, `PredictionModel`, `MatchPredictionModel`, `PredictionsResponse` | `src/api/schemas/predictions.py` |
| `MatchSuggestedPicksResponse`, `BettingFeedbackRequest`, `BettingFeedbackResponse`, `LearningStatsResponse` | `src/api/schemas/picks.py` |
| `TrainingStatusPayload`, `TrainingCachedPayload` | `src/api/schemas/training.py` |
| `HealthResponse` | `src/api/schemas/health.py` |

Cada archivo de schemas debe:
- Exportar todos sus modelos públicos en `__all__`
- Mantener la validación y default values existentes
- Incluir type hints estrictos (cero `Any` innecesarios)

**Criterio de aceptación**: `main.py` no define ningún modelo Pydantic. Todos los schemas se importan desde `src/api/schemas/`.

#### REQ-1.2: Extraer helpers a módulos especializados

| Helper(s) | Destino |
|-----------|---------|
| `_serialize_timestamp`, `_serialize_datetimes` | `src/api/utils/serializers.py` |
| `_normalize_prediction_document` | `src/api/mappers/prediction_mapper.py` |
| `_build_leagues_response`, `_find_league` | `src/api/mappers/league_mapper.py` |
| `_load_predictions_for_league`, `_load_training_result` | `src/api/services/data_loader.py` |

**Criterio de aceptación**: `main.py` no contiene funciones `_helper`. Cada helper vive en un módulo importable e independientemente testeable.

#### REQ-1.3: Separar endpoints en APIRouters

Crear routers de FastAPI:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `src/api/routers/health.py` | `/` | `GET /health` |
| `src/api/routers/leagues.py` | `/api/v1` | `GET /leagues`, `GET /leagues/{league_id}` |
| `src/api/routers/predictions.py` | `/api/v1` | `GET /predictions/league/{league_id}`, `GET /predictions/match/{match_id}` |
| `src/api/routers/matches.py` | `/api/v1` | `GET /matches/live`, `GET /matches/live/with-predictions`, `GET /matches/daily`, `GET /matches/team/{team_name}` |
| `src/api/routers/picks.py` | `/api/v1` | `GET /suggested-picks/match/{match_id}`, `POST /suggested-picks/feedback`, `GET /suggested-picks/learning-stats` |
| `src/api/routers/training.py` | `/api/v1` | `GET /train/status`, `GET /train/cached`, `POST /train/run-now` |

Cada router:
- Declara su propio `APIRouter` con prefix y tags
- Importa schemas, mappers, y data loaders
- NO contiene lógica de negocio — solo orquesta
- Tiene su propio archivo de tests

**Criterio de aceptación**: `main.py` queda con ≤60 líneas (app creation, middleware, CORS, exception handlers, router includes). Todos los endpoints mantienen las mismas rutas, status codes, y response models.

#### REQ-1.4: Validación de no-regresión

- Todos los endpoints mantienen exactamente las mismas URLs, métodos HTTP, y response schemas
- Rate limiting se preserva en los mismos endpoints
- `require_admin_key` se aplica igual en `POST /train/run-now`
- CORS y exception handlers no cambian

**Criterio de aceptación**: Un script de smoke test (`backend/tests/integration/test_api_smoke.py`) verifica que los 15 endpoints responden con el status code correcto.

---

## Epic 2: Testing Foundation — Plan de Testing Estratégico

**Impacto**: Testing 3→8, Calidad 6→8
**Esfuerzo**: L (grande)
**Reglas RULES.md afectadas**: §6 (Tests de regla de negocio)

### Problema

19 tests de backend para ~18,500 líneas. 4 tests de frontend para ~13,800 líneas. Zero tests de integración. La lógica financiera (picks, risk, predictions) tiene CERO tests. Cualquier cambio es una ruleta rusa.

### Estrategia de testing

```
Pirámide:
                    /  E2E  \          ← 0 (fuera de scope por ahora)
                   / Integración \      ← Epic 2.3 (API endpoints)
                  /   Unitarios   \     ← Epic 2.1 + 2.2 (dominio + use cases)
```

### Requerimientos

#### REQ-2.1: Tests unitarios del Dominio — Tier 1 (CRÍTICO)

Tests para TODA la lógica de dominio pura (sin I/O). Prioridad por riesgo financiero:

**Prioridad P0 (lógica financiera — §6 obligatorio):**

| Target | Archivo | Qué testar | Tests mínimos |
|--------|---------|-------------|----------------|
| `picks_service.py` | `tests/unit/domain/test_picks_service.py` | Generación de picks por mercado, Kelly criterion, EV calculation, deduplicación | 25 |
| `risk_manager.py` | `tests/unit/domain/test_risk_manager.py` | Circuit breakers, límites de riesgo, staking | 10 |
| `prediction_service.py` | `tests/unit/domain/test_prediction_service.py` | Poisson distribution, probabilidad 1X2, over/under, BTTS | 20 |
| `pick_resolution_service.py` | `tests/unit/domain/test_pick_resolution_service.py` | Resolución WIN/LOSS/VOID por tipo de mercado | 15 |

**Prioridad P1 (lógica de negocio core):**

| Target | Tests mínimos |
|--------|----------------|
| `statistics_service.py` | 12 |
| `ai_picks_service.py` | 8 |
| `learning_service.py` | 6 |
| `match_aggregator_service.py` | 8 |
| `parley_service.py` | 6 |
| `confidence_calculator.py` | 5 |
| `context_analyzer.py` | 5 |

**Prioridad P2 (modelo de dominio):**

| Target | Tests mínimos |
|--------|----------------|
| `entities.py` (Match, Team, League) | 10 |
| `value_objects/` (Probability, Odds, Score) | 12 |
| `exceptions.py` | 3 |

**Criterios por test unitario de dominio:**
- Cada test tiene un SOLO assert (o grupo lógico cohesivo)
- Naming: `test_{method}_{scenario}_{expected}` (e.g., `test_kelly_criterion_negative_ev_returns_zero`)
- Fixtures se definen en `conftest.py` por directorio
- No I/O, no mocking de DB — solo lógica pura
- Edge cases obligatorios: valores en fronteras (0.0, 1.0, odds=1.01), inputs nulos, listas vacías

**Criterio de aceptación**: ≥135 tests unitarios de dominio. Todos pasan en <10 segundos.

#### REQ-2.2: Tests unitarios de Application Layer — Tier 2

Tests para use cases con mocking de repositorios e infraestructura:

| Target | Tests mínimos |
|--------|----------------|
| `use_cases.py` (GetLeagues, GetPredictions, GetMatchPrediction) | 12 |
| `live_predictions_use_case.py` | 10 |
| `suggested_picks_use_case.py` | 10 |
| `get_parleys_use_case.py` | 6 |
| `ml_training_orchestrator.py` | 8 |
| `training_data_service.py` | 6 |

**Criterios:**
- Usar `unittest.mock.patch` o `pytest-mock` para aislar de I/O
- Testear caminos happy path Y error paths
- Verificar que excepciones de dominio se propagan correctamente

**Criterio de aceptación**: ≥52 tests de application layer. Mock coverage incluye todas las dependencias inyectadas.

#### REQ-2.3: Tests de integración de la API — Tier 3

Tests contra endpoints reales usando `TestClient` de FastAPI (depende de Epic 1):

| Router | Tests mínimos |
|--------|----------------|
| `health.py` | 2 |
| `leagues.py` | 4 |
| `predictions.py` | 6 |
| `matches.py` | 6 |
| `picks.py` | 6 |
| `training.py` | 4 |

**Criterios:**
- Usar `TestClient(app)` con MongoDB mockeado via `mongomock` o fixture de test DB
- Verificar status codes, response schemas, y error responses
- Testear rate limiting y auth en `POST /train/run-now`
- Smoke test: todos los 15 endpoints responden sin 500

**Criterio de aceptación**: ≥28 tests de integración API. Zero 500 errors en ningún endpoint.

#### REQ-2.4: Tests del Frontend — Tier 2

| Target | Tests mínimos |
|--------|----------------|
| Stores Zustand (7 stores) | 14 (2 por store: estado inicial + acción principal) |
| Hooks (10 hooks) | 10 (1 test por hook: happy path) |
| Componentes presentacionales (MatchCard, ParleySlip, LeagueSelector) | 9 (3 por componente: render, interacción, edge case) |
| App.tsx (routing) | 3 |

**Criterios:**
- Eliminar TODOS los `as any` de tests existentes — tipar correctamente
- Usar `@testing-library/react` con `renderHook` para hooks
- Stores: testear con acto directo de Zustand (`useStore.getState().action()`)
- NO testear implementación interna — testear comportamiento visible

**Criterio de aceptación**: ≥36 tests frontend. Zero `as any` en archivos de test.

#### REQ-2.5: Infraestructura de Testing

Configuración necesaria para que los tests sean mantenibles:

| Elemento | Detalle |
|----------|---------|
| `backend/tests/conftest.py` | Fixtures globales: `fake_match()`, `fake_prediction()`, `fake_team()`, `mock_repository()` |
| `backend/tests/unit/domain/conftest.py` | Fixtures de dominio: value objects pre-construidos, matches con variaciones de score |
| `backend/tests/integration/conftest.py` | Fixture de `TestClient(app)` con mock de MongoDB |
| `frontend/src/test/helpers.ts` | Utility: `renderWithProviders()`, `createMockStore()` |
| `pytest.ini` / `pyproject.toml [tool.pytest]` | Configurar `testpaths`, `markers`, `--strict-markers` |
| Coverage config | `--cov=src --cov-report=html --cov-fail-under=40` (target inicial) |

**Criterio de aceptación**: `pytest -v` descubre y ejecuta todos los tests. `npm test` en frontend ejecuta todos los tests. Coverage report se genera.

---

## Epic 3: Stub Endpoints → Implementación Real

**Impacto**: API 6→8.5
**Esfuerzo**: M
**Reglas RULES.md afectadas**: §3 (API funcional)
**Depende de**: Epic 1 (routers separados), Epic 2 (tests como red de seguridad)

### Problema

5 endpoints retornan datos vacíos o no persisten nada. El frontend probablemente consume estas rutas y muestra UX vacía o rota.

### Requerimientos

#### REQ-3.1: `GET /api/v1/matches/daily`

**Comportamiento esperado**: Retorna los partidos del día actual (o de una fecha pasada por query param) con sus predicciones.

**Especificación:**
```
GET /api/v1/matches/daily?date=2026-03-31&league_id=D1

Response 200:
[
  {
    "match_id": "espn_746962",
    "league_id": "D1",
    "match_date": "2026-03-31T14:30:00Z",
    "home_team": { "name": "Bayern Munich", ... },
    "away_team": { "name": "VfB Stuttgart", ... },
    "status": "scheduled",
    "prediction": { ... } | null
  }
]
```

**Implementación:**
1. Consultar `match_predictions` donde `data.match.match_date` está entre `date 00:00:00 UTC` y `date 23:59:59 UTC`
2. Si `league_id` presente, filtrar por `league_id`
3. Normalizar y retornar usando `_normalize_prediction_document`

**Query params:**
- `date` (opcional, default: hoy, formato: YYYY-MM-DD)
- `league_id` (opcional, filtra por liga)

**Errores:**
- 400 si `date` tiene formato inválido

**Criterio de aceptación**: Endpoint retorna partidos del día. Test de integración verifica con datos seed.

#### REQ-3.2: `GET /api/v1/matches/team/{team_name}`

**Comportamiento esperado**: Retorna las últimas predicciones donde un equipo participa (home o away).

**Especificación:**
```
GET /api/v1/matches/team/Bayern%20Munich?limit=10

Response 200:
[
  {
    "match_id": "...",
    "league_id": "D1",
    "match_date": "...",
    "home_team": { ... },
    "away_team": { ... },
    "prediction": { ... }
  }
]
```

**Implementación:**
1. Usar `team_service.search_team()` para normalizar el nombre del equipo
2. Buscar en `match_predictions` donde `data.match.home_team.name` o `data.match.away_team.name` match (case-insensitive regex o text index)
3. Ordenar por `data.match.match_date` descendente
4. Limitar a `limit` resultados (default 10, max 50)

**Query params:**
- `limit` (opcional, default: 10, max: 50)

**Errores:**
- 404 si no se encuentran partidos para el equipo

**Criterio de aceptación**: Búsqueda por nombre parcial funciona. Test verifica con datos seed.

#### REQ-3.3: `GET /api/v1/suggested-picks/match/{match_id}`

**Comportamiento esperado**: Retorna los picks sugeridos para un partido específico.

**Especificación:**
```
GET /api/v1/suggested-picks/match/espn_746962

Response 200:
{
  "match_id": "espn_746962",
  "picks": [
    {
      "market_type": "MATCH_WINNER_HOME",
      "probability": 0.65,
      "odds": 1.85,
      "expected_value": 0.2025,
      "kelly_percentage": 0.1094,
      "confidence": "high",
      "reasoning": "..."
    }
  ],
  "generated_at": "2026-03-31T12:00:00Z"
}
```

**Implementación:**
1. Obtener la predicción existente via `GetMatchPredictionUseCase`
2. Si existe, ejecutar `SuggestedPicksUseCase.execute(match_id)` que ya tiene toda la lógica en `suggested_picks_use_case.py`
3. Mapear el resultado a `MatchSuggestedPicksResponse`

**Errores:**
- 404 si el `match_id` no existe en `match_predictions`

**Criterio de aceptación**: Retorna picks con probabilidades, EV, y Kelly. Test verifica estructura del response.

#### REQ-3.4: `POST /api/v1/suggested-picks/feedback`

**Comportamiento esperado**: Persiste feedback del usuario sobre predicciones para el sistema de aprendizaje.

**Especificación:**
```
POST /api/v1/suggested-picks/feedback
Body:
{
  "match_id": "espn_746962",
  "market_type": "MATCH_WINNER_HOME",
  "actual_result": "WIN",
  "odds_taken": 1.85,
  "stake": 1.0
}

Response 201:
{
  "status": "recorded",
  "message": "Feedback recorded successfully"
}
```

**Implementación:**
1. Validar que `match_id` existe en `match_predictions`
2. Crear documento en nueva colección `betting_feedback` en MongoDB:
   ```json
   {
     "match_id": "...",
     "market_type": "...",
     "actual_result": "WIN|LOSS|VOID",
     "odds_taken": 1.85,
     "stake": 1.0,
     "profit_loss": 0.85,
     "recorded_at": "2026-03-31T12:00:00Z"
   }
   ```
3. Actualizar pesos de `learning_service` si está configurado

**Errores:**
- 400 si body inválido
- 404 si `match_id` no existe
- 422 si `actual_result` no es WIN/LOSS/VOID

**Criterio de aceptación**: Feedback se persiste en MongoDB. Segundo POST con mismo `match_id` y `market_type` actualiza en vez de duplicar. Test verifica persistencia.

#### REQ-3.5: `GET /api/v1/suggested-picks/learning-stats`

**Comportamiento esperado**: Retorna estadísticas agregadas del sistema de aprendizaje.

**Especificación:**
```
GET /api/v1/suggested-picks/learning-stats

Response 200:
{
  "total_feedback_records": 42,
  "accuracy_by_market": {
    "MATCH_WINNER_HOME": { "total": 15, "correct": 10, "accuracy": 0.667 },
    "OVER_UNDER_25": { "total": 12, "correct": 8, "accuracy": 0.667 }
  },
  "overall_roi": 0.12,
  "profit_loss_total": 5.2,
  "last_updated": "2026-03-31T12:00:00Z"
}
```

**Implementación:**
1. Agregar desde colección `betting_feedback` usando pipeline de agregación de MongoDB
2. Calcular accuracy por `market_type`, ROI total, P&L total
3. Cachear resultado (TTL 5 min) para evitar queries pesadas

**Errores:**
- 200 con datos vacíos si no hay feedback registrado

**Criterio de aceptación**: Estadísticas reflejan el feedback persistido. Test verifica cálculos con datos seed.

---

## Epic 4: Auto-Labeling Pipeline — Cerrar el Ciclo de Retroalimentación

**Impacto**: Auto-labeling 5→8, ML Pipeline 7→8
**Esfuerzo**: M
**Reglas RULES.md afectadas**: §12 (Trazabilidad), §13 (Detección de anomalías)

### Problema

Las predicciones en `match_predictions` tienen un TTL implícito via `expires_at`. Si el labeler no ejecuta dentro de la ventana de expiración, las predicciones se pierden sin ser etiquetadas. Además, no hay automatización — el labeler es manual.

### Requerimientos

#### REQ-4.1: Preservar predicciones para labeling

**Cambio en el schema de `match_predictions`:**

Agregar campo `labeled` (boolean, default `false`) al documento de predicción.

```python
# En MongoRepository.save_match_prediction():
doc = {
    "match_id": match_id,
    "league_id": league_id,
    "data": data,
    "expires_at": expires_at,
    "last_updated": now,
    "labeled": False,  # NUEVO
    "label_result": None,  # NUEVO: WIN/LOSS/DRAW cuando se etiquete
    "labeled_at": None,  # NUEVO: timestamp de cuando se etiquetó
}
```

**Cambio en `get_match_prediction()`:**
- El endpoint de lectura SIGUE filtrando por `expires_at` (comportamiento actual preservado)
- El labeler consulta `{"labeled": False}` SIN filtrar por `expires_at`

**Criterio de aceptación**: Predicciones expiradas siguen disponibles para el labeler. Lecturas del API siguen respetando TTL.

#### REQ-4.2: Automatizar el labeler como cron job

El servicio `labeler` en `docker-compose.dev.yml` ya existe pero ejecuta manualmente. Convertirlo en un cron real:

**Flujo del labeler automático:**
1. Cada `LABELER_INTERVAL_SEC` (default 600s = 10 min):
   a. Consultar `match_predictions` donde `labeled = false` y `data.match.match_date < now - 3h` (dar tiempo a que termine el partido)
   b. Para cada predicción no etiquetada, buscar el resultado en fuentes externas (`gather_finished_matches`)
   c. Si el partido terminó:
      - Escribir `home_goals`, `away_goals`, `status = "finished"` en `data.match`
      - Calcular `label_result` (HOME_WIN / DRAW / AWAY_WIN)
      - Escribir `labeled = true`, `labeled_at = now`, `label_result = resultado`
   d. Si el partido aún no terminó: skip (se reintenta en el próximo ciclo)

**Criterio de aceptación**: Predicciones se etiquetan automáticamente dentro de las 24h de terminar el partido. Colección `match_predictions` tiene documentos con `labeled: true` y resultados.

#### REQ-4.3: Agregar metadatos de trazabilidad ML (§12)

Al generar una predicción, agregar metadatos al documento:

```json
{
  "model_metadata": {
    "model_version": "rf_v1_D1_winner_20260331",
    "training_date": "2026-03-30T08:00:00Z",
    "training_accuracy": 0.67,
    "feature_count": 42,
    "data_sources": ["football_data_uk", "espn", "thesportsdb"]
  }
}
```

**Criterio de aceptación**: Toda predicción nueva incluye `model_metadata`. Se puede trazar desde un pick hasta el modelo y datos que lo generaron.

#### REQ-4.4: Validaciones de sanidad de datos (§13)

Agregar validaciones en el pipeline de ingesta (`match_aggregator_service.py`):

| Validación | Acción |
|-----------|--------|
| Cuotas < 1.01 | Log WARNING, marcar como `anomalous` |
| Cuotas > 1000 | Log WARNING, marcar como `anomalous` |
| Goles > 15 en un partido | Log WARNING, descartar resultado |
| Posesión > 100% o < 0% | Log WARNING, descartar stat |
| Fecha del partido en el pasado lejano (>7 días) | Log WARNING, skip |

**Criterio de aceptación**: Pipeline rechaza datos anómalos con logging. Tests unitarios verifican cada regla de validación.

#### REQ-4.5: Conectar labeling con pipeline de métricas

El script `metrics_baseline.py` debe consultar predicciones etiquetadas (`labeled: true`) para calcular:

- Brier score por outcome (home/draw/away)
- ECE (Expected Calibration Error)
- Accuracy de clasificación 1X2
- ROI por mercado (si hay datos de odds)
- P&L acumulado

Conectar con el endpoint `GET /api/v1/suggested-picks/learning-stats` (REQ-3.5).

**Criterio de aceptación**: El dashboard muestra métricas basadas en datos REALES de predicciones etiquetadas.

---

## Epic 5: Frontend Hardening

**Impacto**: Frontend 7→8, Calidad 6→8
**Esfuerzo**: M
**Reglas RULES.md afectadas**: §6 (prohibido `any`), §7 (Error Boundaries)

### Problema

28 usos de `as any` en el frontend. Solo 1 ErrorBoundary global. Stores sin tipado correcto.

### Requerimientos

#### REQ-5.1: Eliminar todos los `as any`

**28 ocurrencias identificadas:**

| Archivo | Ocurrencias | Solución |
|---------|-------------|----------|
| `predictionUtils.ts` | 12 | Tipar correctamente las transformaciones de predicción. Definir interfaces explícitas para los raw API responses |
| `matchMatching.ts` | 4 | Tipar los objetos de matching con interfaces de dominio |
| `App.tsx` | 3 | Exportar tipos correctos desde los stores de Zustand |
| Hooks varios | 5 | Tipar los returns de hooks con interfaces específicas |
| Tests | 4 | Usar factories tipadas en lugar de `as any` |

**Estrategia:**
1. Para stores Zustand: definir el type del store y exportarlo explícitamente
2. Para API responses: crear interfaces en `src/types/` que mapean las respuestas del backend
3. Para cada `as any`: determinar el tipo correcto y reemplazar
4. Si un tipo es genuinamente desconocido: usar `unknown` con narrowing, NUNCA `any`

**Criterio de aceptación**: `grep -r "as any" frontend/src/ | wc -l` retorna 0. `npm run build` pasa sin errores de tipo.

#### REQ-5.2: Error Boundaries por módulo

Agregar Error Boundaries individuales a los módulos principales:

| Módulo | Boundary |
|--------|----------|
| `PredictionGrid` | Muestra fallback "No se pudieron cargar las predicciones" |
| `LiveMatches` | Muestra fallback "Partidos en vivo no disponibles" |
| `BotDashboard` | Muestra fallback "Dashboard del bot no disponible" |
| `ParleySlip` | Muestra fallback "Parley no disponible" |
| `MatchCard` | Muestra fallback card con mensaje de error |
| `LeagueSelector` | Muestra fallback con reload button |

**Implementación:**
- Crear `ErrorBoundaryWrapper` genérico reutilizable con props: `fallback`, `onError`, `resetKeys`
- Envolver cada módulo principal en el wrapper
- Log de errores a `console.error` (y eventualmente a un servicio de reporting)

**Criterio de aceptación**: Si un módulo lanza un error de runtime, solo ese módulo muestra fallback. El resto de la app sigue funcionando.

#### REQ-5.3: Centralizar interfaces del frontend

Migrar las 17+ interfaces declaradas localmente en componentes a `src/types/`:

| Archivo destino | Interfaces |
|----------------|------------|
| `src/types/match.ts` | `Match`, `Team`, `MatchEvent`, `Score` |
| `src/types/prediction.ts` | `Prediction`, `MatchPrediction`, `PredictionResponse` |
| `src/types/picks.ts` | `SuggestedPick`, `PickFeedback`, `LearningStats` |
| `src/types/league.ts` | `League`, `LeagueMetadata` |
| `src/types/store.ts` | `PredictionStoreState`, `LiveStoreState`, `UIStoreState` |

**Criterio de aceptación**: Componentes importan interfaces de `@/types/`. Zero interfaces definidas inline en archivos de componentes (excepto props de componentes).

---

## Epic 6: DevOps & Compliance — Cerrar el Ciclo

**Impacto**: DevOps 8→9, Documentación 8→9
**Esfuerzo**: S (pequeño)
**Reglas RULES.md afectadas**: §5 (Pre-commit), §14 (Freshness)

### Problema

CI sin cobertura, inconsistencia MongoDB vs PostgreSQL en documentación, sin pre-commit hooks configurados, workflows duplicados.

### Requerimientos

#### REQ-6.1: Resolver inconsistencia MongoDB vs PostgreSQL

**Decisión requerida**: El proyecto usa MongoDB en TODA la base de código. PostgreSQL solo aparece en documentación y `render.yaml`:

**Acciones:**
1. Actualizar `backend/ARCHITECTURE.md`: cambiar sección "The Memory (PostgreSQL)" a "The Memory (MongoDB)"
2. Actualizar `render.yaml`: remover o marcar como deprecated la referencia a `bjj-betsports-db` (PostgreSQL)
3. Buscar y eliminar `database_service.py` (implementa PostgreSQL, código muerto) o moverlo a `infrastructure/database/deprecated/`
4. Documentar en `ARCHITECTURE.md` la decisión: "Seleccionamos MongoDB para el almacenamiento de datos textuales y no-relacionales (predicciones, matches, feedback). Si en el futuro se requiere datos relacionales fuertes, se evaluará PostgreSQL."

**Criterio de aceptación**: Cero referencias a PostgreSQL como DB activa en documentación. `render.yaml` refleja la realidad del deployment.

#### REQ-6.2: CI con cobertura y umbrales

Actualizar `.github/workflows/ci.yml`:

```yaml
# Backend
- name: Run tests with coverage
  run: |
    cd backend
    pytest --cov=src --cov-report=xml --cov-fail-under=40 -v

# Frontend
- name: Run frontend tests with coverage
  run: |
    cd frontend
    npx vitest run --coverage --reporter=verbose
```

**Umbrales progresivos:**
- Fase 1 (post Epic 2): `--cov-fail-under=40`
- Fase 2 (3 meses después): `--cov-fail-under=60`
- Fase 3 (6 meses después): `--cov-fail-under=75`

**Criterio de aceptación**: CI falla si coverage baja del umbral. Badge de coverage en README.

#### REQ-6.3: Consolidar workflows de lint

Fusionar `ci.yml` y `lint.yml` en un solo workflow con jobs separados:

```yaml
jobs:
  lint:
    steps: [black, isort, ruff, mypy]
  test-backend:
    needs: lint
    steps: [pytest con coverage]
  test-frontend:
    needs: lint
    steps: [vitest con coverage]
  build-frontend:
    needs: test-frontend
    steps: [npm run build]
```

**Criterio de aceptación**: Un solo workflow cubre lint + test + build. No hay workflows duplicados.

#### REQ-6.4: Limpiar directorios vacíos e código muerto

| Elemento | Acción |
|----------|--------|
| `backend/src/domain/interfaces/` (vacío) | Eliminar directorio |
| `backend/src/domain/patterns/` (vacío) | Eliminar directorio |
| `backend/src/infrastructure/notifications/` (vacío) | Eliminar directorio |
| `backend/src/infrastructure/providers/` (vacío) | Eliminar directorio |
| `backend/src/infrastructure/database/database_service.py` | Eliminar (PostgreSQL muerto) |

**Criterio de aceptación**: `find backend/src -type d -empty` retorna 0 resultados. No hay imports a código eliminado.

#### REQ-6.5: Implementar repository interfaces (DIP)

Hacer que `MongoRepository` implemente formalmente las interfaces abstractas del dominio:

```python
# domain/repositories/repositories.py define:
class MatchRepository(ABC):
    @abstractmethod
    def get_match_prediction(self, match_id: str) -> Optional[dict]: ...
    @abstractmethod
    def save_match_prediction(self, match_id: str, ...) -> None: ...

# infrastructure/repositories/mongo_repository.py:
class MongoRepository(MatchRepository, LeagueRepository, ...):
    ...
```

**Criterio de aceptación**: `MongoRepository` hereda de todas las ABCs de dominio. `mypy` verifica que todos los métodos abstractos están implementados.

#### REQ-6.6: Documentar la arquitectura real

Actualizar `ARCHITECTURE.md` del backend para reflejar:
- MongoDB como DB única (no PostgreSQL)
- Los nuevos servicios (labeler, updater) en Docker Compose
- El flujo de auto-labeling
- El pipeline de métricas

Actualizar `ARCHITECTURE.md` del frontend para reflejar:
- Estado real de Error Boundaries
- Patrón de stores tipados
- Interfaces centralizadas

**Criterio de aceptación**: ARCHITECTURE.md refleja con exactitud el estado actual del código y la infraestructura.

---

## Resumen de Impact Map

| Epic | Áreas impactadas | Nota antes → después |
|------|-------------------|---------------------|
| 1. API Decomposition | Arquitectura, Calidad | 7→8.5, 6→7.5 |
| 2. Testing Foundation | Testing, Calidad | 3→8, 6→8 |
| 3. Stub Endpoints | API | 6→8.5 |
| 4. Auto-labeling | Auto-labeling, ML | 5→8, 7→8 |
| 5. Frontend Hardening | Frontend, Calidad | 7→8, 6→8 |
| 6. DevOps & Compliance | DevOps, Docs | 8→9, 8→9 |

---

## Criterios de Éxito Global

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Tests backend | 19 | ≥215 |
| Tests frontend | 7 | ≥43 |
| Coverage backend | ~1% | ≥40% |
| Endpoints funcionales | 7/15 | 15/15 |
| `as any` en frontend | 28 | 0 |
| Error Boundaries | 1 | 7 |
| `main.py` líneas | 509 | ≤60 |
| Directorios vacíos | 4 | 0 |
| Archivos de código muerto | 1 | 0 |
| Pre-commit hooks | no | sí |
| CI con coverage | no | sí |
| Auto-labeling automático | no | sí |
| Trazabilidad ML | no | sí |
| Nota general | 6.5 | 8.5+ |

---

## Orden de Ejecución Recomendado

```
Semana 1-2:  Epic 1 (API Decomposition) — desbloquea testing modular
Semana 2-4:  Epic 2 (Testing Foundation) — P0 primero (lógica financiera)
Semana 3-4:  Epic 5 (Frontend Hardening) — en paralelo con Epic 2
Semana 4-5:  Epic 3 (Stub Endpoints) — con tests de integración
Semana 5-6:  Epic 4 (Auto-labeling) — cierra el ciclo ML
Semana 6:    Epic 6 (DevOps & Compliance) — consolida todo
```

---

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| Regresión al descomponer `main.py` | Media | REQ-1.4 exige smoke test antes y después |
| Tests lentos al crecer | Baja | Usar `pytest-xdist` para paralelismo. Dominio tests sin I/O (<10s) |
| Data gap persiste (no hay partidos que etiquetar) | Alta | REQ-4.1 preserva predicciones. REQ-4.2 automatiza labeling. Al llegar abril, los partidos se juegan y el pipeline se activa |
| Frontend regression al quitar `as any` | Media | Compilar `npm run build` después de cada archivo. Tests existentes como red mínima |
| Scope creep en endpoints | Media | Specs concretos por endpoint con schemas de response fijos |

---

## Apéndice A: Reglas RULES.md Actualmente Violadas

| Regla | Epic(s) que la resuelven |
|-------|-------------------------|
| §4 SRP (main.py God File) | Epic 1 |
| §5 Pre-commit hooks | Epic 6 |
| §6 Prohibido `any` | Epic 5 |
| §6 Tests de regla de negocio | Epic 2 |
| §7 Error Boundaries por módulo | Epic 5 |
| §7 No swallowing exceptions | Epic 2 (tests exponen), Epic 3 (fix en implementación) |
| §8 Cómputo en background | Epic 3 (REQ-3.3 usa use case existente) |
| §12 Trazabilidad ML | Epic 4 |
| §13 Detección de anomalías | Epic 4 |
| §14 Frescura de cuotas | Fuera de scope — requiere spec separado |

## Apéndice B: Archivos Nuevos a Crear

```
backend/src/api/schemas/
    __init__.py
    health.py
    leagues.py
    predictions.py
    picks.py
    training.py
backend/src/api/routers/
    __init__.py
    health.py
    leagues.py
    predictions.py
    matches.py
    picks.py
    training.py
backend/src/api/mappers/
    __init__.py
    prediction_mapper.py
    league_mapper.py
backend/src/api/utils/
    __init__.py
    serializers.py
backend/src/api/services/
    __init__.py
    data_loader.py
backend/tests/conftest.py
backend/tests/unit/domain/
    conftest.py
    test_picks_service.py
    test_risk_manager.py
    test_prediction_service.py
    test_pick_resolution_service.py
    test_statistics_service.py
    test_ai_picks_service.py
    test_learning_service.py
    test_match_aggregator_service.py
    test_parley_service.py
    test_confidence_calculator.py
    test_context_analyzer.py
    test_entities.py
    test_value_objects.py
    test_exceptions.py
backend/tests/unit/application/
    test_use_cases.py
    test_live_predictions_use_case.py
    test_suggested_picks_use_case.py
    test_get_parleys_use_case.py
    test_ml_training_orchestrator.py
    test_training_data_service.py
backend/tests/integration/
    conftest.py
    test_api_smoke.py
    test_health_router.py
    test_leagues_router.py
    test_predictions_router.py
    test_matches_router.py
    test_picks_router.py
    test_training_router.py
frontend/src/test/
    helpers.ts
frontend/src/presentation/components/common/
    ErrorBoundaryWrapper.tsx
frontend/src/types/
    match.ts
    prediction.ts
    picks.ts
    league.ts
    store.ts
```
