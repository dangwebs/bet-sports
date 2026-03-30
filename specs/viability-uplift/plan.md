# Plan: Viability Uplift — BJJ-BetSports

**Fecha**: 28 de marzo de 2026  
**Spec de referencia**: `specs/viability-uplift/spec.md`  
**Branch propuesta**: `feat/viability-uplift`  

---

## 1. Estructura de Ejecución

El plan se organiza en **3 fases secuenciales**. Cada fase tiene **bloques de trabajo** que pueden ejecutarse en paralelo dentro de la misma fase si no tienen dependencias entre sí. Cada bloque produce un PR atómico.

### Convención de PRs

| Prefijo | Significado |
|---|---|
| `ci:` | Configuración de CI/CD |
| `fix:` | Corrección de bugs o problemas de seguridad |
| `test:` | Adición de tests |
| `refactor:` | Mejora de código sin cambio funcional |
| `chore:` | Mantenimiento, limpieza, configuración |
| `feat:` | Funcionalidad nueva (modelo registry, etc.) |

---

## 2. Fase 1 — Fundamentos de Viabilidad

> **Requisito**: Completar todos los bloques de Fase 1 antes de iniciar Fase 2.  
> **PRs estimados**: 6

### Bloque 1.A — Desbloquear CI/CD

**Spec refs**: §5.1.1, §5.1.2  
**Dependencias**: Ninguna — este bloque desbloquea todo lo demás  
**PR**: `ci: desbloquear github workflows y crear CI de PRs`

#### Paso 1: Auditar contenido de `.github/`

**Acción**: Revisar TODOS los archivos en `.github/` en busca de:
- API keys, tokens, passwords hardcodeados
- URLs privadas o internas
- Datos personales

**Archivos a revisar**:
```
.github/
├── agents/
│   ├── README.md
│   ├── hypergenia-backend.agent.md
│   ├── hypergenia-frontend.agent.md
│   ├── hypergenia-architecture.agent.md
│   └── hypergenia-orchestrator.agent.md
├── copilot-instructions.md
├── prompts/  (si existe)
└── skills/
    ├── orchestrator/SKILL.md
    ├── frontend/SKILL.md
    ├── backend/SKILL.md
    ├── architecture/SKILL.md
    ├── general/SKILL.md
    ├── code-quality/SKILL.md
    ├── clean-code/SKILL.md
    ├── best-practices/SKILL.md
    ├── linting/SKILL.md
    ├── design-patterns/SKILL.md
    ├── software-architecture/SKILL.md
    ├── devops/SKILL.md
    └── conventional-commits/SKILL.md
```

**Criterio de OK**: Ningún archivo contiene secrets → proceder.  
**Si se encuentran secrets**: Excluir esos archivos específicos vía `.gitignore` selectivo.

#### Paso 2: Modificar `.gitignore`

**Archivo**: `.gitignore` (raíz)  
**Cambio exacto**: Reemplazar las líneas:
```
# Agent files
.github/
.claude/
```
Por:
```
# Agentes Claude (solo local, no versionar)
.claude/
```

**Validación**: `git status` muestra los archivos de `.github/` como untracked/nuevos.

#### Paso 3: Crear workflow CI

**Archivo nuevo**: `.github/workflows/ci.yml`

**Contenido completo**:
```yaml
name: CI — Pull Request Checks

on:
  pull_request:
    branches: [main, develop, "feature/**"]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend-lint-and-types:
    name: "Backend: Lint + Types"
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt
      - run: python -m black --check src/ tests/
      - run: python -m mypy src/ --ignore-missing-imports

  backend-tests:
    name: "Backend: Tests"
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt
      - run: python -m pytest -v --tb=short

  frontend-lint:
    name: "Frontend: Lint + Build"
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run build

  frontend-tests:
    name: "Frontend: Tests"
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npx vitest run
```

**Validación**:
- `yamllint .github/workflows/ci.yml` sin errores (o validar YAML manualmente)
- Push a una rama y abrir PR → los 4 jobs se ejecutan

#### Paso 4: Commit y PR

**Commit message**: `ci: desbloquear .github/ del gitignore y crear workflow CI para PRs`  
**Archivos en el commit**:
- `.gitignore` (modificado)
- `.github/workflows/ci.yml` (nuevo)
- Todos los archivos en `.github/agents/`, `.github/skills/`, `.github/copilot-instructions.md` (ahora tracked)

---

### Bloque 1.B — Seguridad API

**Spec refs**: §5.2.1, §5.2.2  
**Dependencias**: Ninguna (paralelo con 1.A)  
**PR**: `fix(backend): agregar API key para endpoints admin y rate limiting`

#### Paso 1: Instalar `slowapi`

**Archivo**: `backend/requirements.txt`  
**Agregar línea**: `slowapi==0.1.9`

#### Paso 2: Crear módulo de seguridad

**Archivo nuevo**: `backend/src/api/security.py`

**Contenido**:
```python
"""Seguridad de la API: autenticación por API key y rate limiting."""

import os
from typing import Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")


async def require_admin_key(
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """Dependency que exige API key válida para endpoints administrativos.

    Raises:
        HTTPException 403 si la key falta o no coincide.
    """
    if not _ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Admin API key not configured on server",
        )
    if api_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return api_key
```

#### Paso 3: Integrar en `main.py`

**Archivo**: `backend/src/api/main.py`  

**Cambios**:
1. Importar al inicio:
   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address
   from slowapi.middleware import SlowAPIMiddleware
   from src.api.security import require_admin_key
   ```

2. Configurar limiter después de crear `app`:
   ```python
   limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
   app.state.limiter = limiter
   app.add_middleware(SlowAPIMiddleware)
   ```

3. Proteger endpoints admin con `Depends(require_admin_key)`:
   ```python
   @app.post("/api/v1/train/run-now")
   async def trigger_training(_: str = Depends(require_admin_key)):
   ```

4. Rate limit específico para endpoints admin:
   ```python
   @app.post("/api/v1/train/run-now")
   @limiter.limit("5/minute")
   async def trigger_training(request: Request, _: str = Depends(require_admin_key)):
   ```

5. Exemption para health check:
   ```python
   @app.get("/health")
   @limiter.exempt
   async def health_check():
   ```

#### Paso 4: Actualizar `.env.example`

**Archivo**: `backend/.env.example`  
**Agregar**:
```bash
# --- Seguridad API ---
ADMIN_API_KEY=cambiar-por-un-valor-aleatorio-seguro
```

#### Paso 5: Actualizar Docker Compose

**Archivo**: `docker-compose.dev.yml`  
**En el servicio `backend-api`**, agregar en `environment`:
```yaml
ADMIN_API_KEY: ${ADMIN_API_KEY:-dev-admin-key-local}
```

#### Paso 6: Tests de seguridad

**Archivo nuevo**: `backend/tests/unit/test_api_security.py`

**Tests**:
```python
"""Tests para seguridad de la API."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """TestClient con ADMIN_API_KEY configurada."""
    with patch.dict("os.environ", {"ADMIN_API_KEY": "test-secret-key"}):
        from src.api.main import app
        yield TestClient(app)


def test_train_endpoint_requires_api_key(client):
    response = client.post("/api/v1/train/run-now")
    assert response.status_code == 403


def test_train_endpoint_accepts_valid_key(client):
    response = client.post(
        "/api/v1/train/run-now",
        headers={"X-API-Key": "test-secret-key"},
    )
    assert response.status_code in (200, 202)


def test_train_endpoint_rejects_wrong_key(client):
    response = client.post(
        "/api/v1/train/run-now",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 403


def test_public_endpoints_no_auth_needed(client):
    response = client.get("/health")
    assert response.status_code == 200

    response = client.get("/api/v1/leagues")
    assert response.status_code == 200
```

#### Paso 7: Validación local

```bash
cd backend
pip install slowapi==0.1.9
ADMIN_API_KEY=test pytest tests/unit/test_api_security.py -v
```

#### Paso 8: Commit

**Commit message**: `fix(backend): agregar API key para endpoints admin y rate limiting con slowapi`

---

### Bloque 1.C — Error Handling Global

**Spec refs**: §5.3.1, §5.3.2  
**Dependencias**: Ninguna (paralelo con 1.A y 1.B)  
**PR**: `fix(backend): middleware global de excepciones y limpieza de bare excepts`

#### Paso 1: Agregar exception handler en `main.py`

**Archivo**: `backend/src/api/main.py`  
**Agregar después de configurar CORS**:
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _logger.error(
        "Excepción no manejada en %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )
```

#### Paso 2: Corregir 3 bare `except:`

**Archivo**: `backend/src/infrastructure/data_sources/espn.py`

- **Línea ~148**: Cambiar `except:` → `except (ValueError, TypeError):`
- **Línea ~426**: Cambiar `except:` → `except (ValueError, TypeError):`

**Archivo**: `backend/src/domain/services/ml_feature_extractor.py`

- **Línea ~144**: Cambiar `except:` → `except statistics.StatisticsError:`  
  (Verificar que `import statistics` está presente al inicio del archivo)

#### Paso 3: Agregar logging mínimo a `except Exception: pass`

Para cada uno de los siguientes archivos, reemplazar `except Exception: pass` o `except Exception:\n    pass` por un `except Exception` con `logger.debug(...)` mínimo:

| # | Archivo | Línea(s) | Cambio |
|---|---|---|---|
| 1 | `application/use_cases/use_cases.py` | L911 | `except Exception:\n    pass` → `except Exception as exc:\n    logger.debug("Ignorando error no crítico: %s", exc)` |
| 2 | `application/use_cases/use_cases.py` | L1188 | Idem |
| 3 | `application/use_cases/use_cases.py` | L1198 | Idem |
| 4 | `application/use_cases/suggested_picks_use_case.py` | L447 | `except Exception:\n    return []` → `except Exception as exc:\n    logger.debug("Fallback a lista vacía: %s", exc)\n    return []` |
| 5 | `application/use_cases/suggested_picks_use_case.py` | L462 | Idem |
| 6 | `application/use_cases/live_predictions_use_case.py` | L421 | `except Exception:\n    ...` → agregar `logger.debug(...)` antes del return/pass |
| 7 | `application/use_cases/live_predictions_use_case.py` | L436 | Idem |
| 8 | `application/use_cases/live_predictions_use_case.py` | L469 | Idem |
| 9 | `application/use_cases/live_predictions_use_case.py` | L513 | Idem |
| 10 | `application/use_cases/get_parleys_use_case.py` | L45 | Idem |

#### Paso 4: Validación

```bash
cd backend
# Verificar 0 bare excepts:
grep -rn "except:" src/ | grep -v "except Exception" | grep -v "except (" | grep -v "#"
# Debe devolver 0 resultados

# Verificar 0 pass silenciosos tras except:
grep -Pzn "except.*:\s*\n\s*pass\s*$" src/
# Debe devolver 0 resultados

# Ejecutar tests:
pytest -v --tb=short
```

#### Paso 5: Commit

**Commit message**: `fix(backend): middleware global de errores y eliminar bare excepts/pass silenciosos`

---

### Bloque 1.D — Tests Unitarios Backend (Lógica de Dinero y Dominio)

**Spec refs**: §5.4.1, §5.4.2, §5.4.3  
**Dependencias**: Bloque 1.C completado (error handling limpio para que los tests sean confiables)  
**PR**: `test(backend): tests unitarios para lógica de dominio, riesgo y scoring`

#### Paso 1: Crear test fixtures compartidas

**Archivo nuevo**: `backend/tests/conftest.py`

```python
"""Fixtures compartidas para tests del backend."""
import pytest
from datetime import datetime
from src.domain.entities.entities import (
    Team, League, Match, Prediction, TeamStatistics, MatchPrediction,
)
from src.domain.entities.suggested_pick import (
    MarketType, ConfidenceLevel, SuggestedPick, MatchSuggestedPicks,
)
from src.domain.value_objects.value_objects import Probability, Odds, Score


@pytest.fixture
def sample_team_home() -> Team:
    return Team(id="team_1", name="Arsenal", short_name="ARS")


@pytest.fixture
def sample_team_away() -> Team:
    return Team(id="team_2", name="Chelsea", short_name="CHE")


@pytest.fixture
def sample_league() -> League:
    return League(id="E0", name="Premier League", country="England")


@pytest.fixture
def sample_match(sample_team_home, sample_team_away, sample_league) -> Match:
    return Match(
        id="match_001",
        home_team=sample_team_home,
        away_team=sample_team_away,
        league=sample_league,
        date=datetime(2026, 3, 28, 15, 0),
        status="NS",
    )


@pytest.fixture
def sample_prediction() -> Prediction:
    return Prediction(
        match_id="match_001",
        home_win_probability=0.45,
        draw_probability=0.25,
        away_win_probability=0.30,
        predicted_home_goals=1.5,
        predicted_away_goals=1.0,
        over_25_probability=0.55,
        under_25_probability=0.45,
        confidence=0.72,
        data_sources=["football_data_uk", "espn"],
        created_at=datetime(2026, 3, 28),
    )


@pytest.fixture
def sample_home_stats() -> TeamStatistics:
    return TeamStatistics(
        team_id="team_1",
        matches_played=20,
        wins=12,
        draws=4,
        losses=4,
        goals_scored=35,
        goals_conceded=18,
        avg_goals_scored=1.75,
        avg_goals_conceded=0.9,
        avg_corners=5.5,
        avg_cards=1.8,
    )


@pytest.fixture
def sample_away_stats() -> TeamStatistics:
    return TeamStatistics(
        team_id="team_2",
        matches_played=20,
        wins=10,
        draws=5,
        losses=5,
        goals_scored=28,
        goals_conceded=22,
        avg_goals_scored=1.4,
        avg_goals_conceded=1.1,
        avg_corners=4.8,
        avg_cards=2.1,
    )
```

**Nota**: Adaptar las fixtures según las firmas reales de los dataclasses. Las firmas exactas deben leerse de `backend/src/domain/entities/entities.py` antes de implementar.

#### Paso 2: Tests de Value Objects

**Archivo nuevo**: `backend/tests/unit/test_value_objects.py`

```python
"""Tests para value objects del dominio."""
import pytest
from src.domain.value_objects.value_objects import Probability, Odds, Score


class TestProbability:
    def test_valid_probability(self):
        p = Probability(value=0.5)
        assert p.value == 0.5

    def test_probability_zero(self):
        p = Probability(value=0.0)
        assert p.value == 0.0

    def test_probability_one(self):
        p = Probability(value=1.0)
        assert p.value == 1.0

    def test_probability_negative_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            Probability(value=-0.1)

    def test_probability_over_one_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            Probability(value=1.1)

    def test_frozen_immutability(self):
        p = Probability(value=0.5)
        with pytest.raises(AttributeError):
            p.value = 0.9  # type: ignore[misc]


class TestOdds:
    def test_valid_odds(self):
        o = Odds(value=2.5)
        assert o.value == 2.5

    def test_odds_minimum(self):
        o = Odds(value=1.01)
        assert o.value == 1.01

    def test_odds_below_one_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            Odds(value=0.5)

    def test_frozen_immutability(self):
        o = Odds(value=2.0)
        with pytest.raises(AttributeError):
            o.value = 3.0  # type: ignore[misc]


class TestScore:
    def test_valid_score(self):
        s = Score(home=2, away=1)
        assert s.home == 2
        assert s.away == 1

    def test_score_zero(self):
        s = Score(home=0, away=0)
        assert s.home == 0

    def test_negative_score_raises(self):
        with pytest.raises((ValueError, AssertionError)):
            Score(home=-1, away=0)

    def test_frozen_immutability(self):
        s = Score(home=1, away=0)
        with pytest.raises(AttributeError):
            s.home = 5  # type: ignore[misc]
```

**Nota**: Las validaciones específicas (`ValueError` vs `AssertionError`) dependen de cómo estén implementadas las validaciones en `__post_init__`. Leer el código real antes de fijar.

#### Paso 3: Tests de Entities

**Archivo nuevo**: `backend/tests/unit/test_entities.py`

**Tests a implementar** (el agente debe leer las firmas reales primero):
- `test_match_creation`: Crear un `Match` con los campos mínimos, verificar que los atributos existen.
- `test_prediction_dataclass_fields`: Verificar que `Prediction` tiene los campos esperados.
- `test_suggested_pick_market_types`: Verificar que `MarketType` enum contiene al menos `WINNER`, `GOALS`, `CORNERS`, `CARDS`.
- `test_betting_feedback_creation`: Crear un `BettingFeedback` y verificar campos.
- `test_parley_creation`: Crear un `Parley` con picks válidos.

#### Paso 4: Tests de RiskManager

**Archivo nuevo**: `backend/tests/unit/test_risk_manager.py`

**Tests a implementar** (leer `risk_manager.py` primero para adaptar las llamadas):
- `test_max_stake_hard_cap`: Verificar que el stake sugerido nunca excede 5% del bankroll (RULES.md §11).
- `test_circuit_breaker_activates`: Simular racha de pérdidas consecutivas → verificar que el breaker se activa.
- `test_ev_positive_accepted`: Pick con `prob=0.6, odds=2.0` → EV = 1.2 → aceptado.
- `test_ev_negative_rejected`: Pick con `prob=0.3, odds=1.5` → EV = 0.45 → rechazado (RULES.md §11).
- `test_anomalous_odds_rejected`: Cuotas < 1.01 o > 1000 → rechazadas (RULES.md §13).

#### Paso 5: Tests de BankrollService

**Archivo nuevo**: `backend/tests/unit/test_bankroll_service.py`

**Tests a implementar**:
- `test_initial_bankroll_positive`: Bankroll inicial debe ser > 0.
- `test_bankroll_after_win`: Bankroll aumenta correctamente.
- `test_bankroll_after_loss`: Bankroll disminuye correctamente.
- `test_stake_percentage_calculation`: Verificar cálculo de stake como % del bankroll.

#### Paso 6: Tests de PicksService

**Archivo nuevo**: `backend/tests/unit/test_picks_service.py`

**Tests a implementar** (los más importantes por RULES.md §16):
- `test_generate_picks_all_four_markets`: Verificar que se generan picks para WINNER, GOALS, CORNERS y CARDS.
- `test_no_empty_corners_picks`: Dado un match válido → nunca devolver lista vacía para corners.
- `test_no_empty_cards_picks`: Dado un match válido → nunca devolver lista vacía para tarjetas.
- `test_pick_has_required_fields`: Cada pick tiene `market_type`, `market_label`, `probability`, `confidence_level`.
- `test_pick_probability_bounds`: Probabilidad de cada pick entre 0 y 1.

#### Paso 7: Tests de ConfidenceCalculator

**Archivo nuevo**: `backend/tests/unit/test_confidence_calculator.py`

**Tests**:
- `test_high_confidence_many_sources`: Muchas fuentes de datos → confidence alta.
- `test_low_confidence_sparse_data`: Pocas fuentes → confidence baja.
- `test_confidence_always_between_0_and_1`: Nunca devuelve valor fuera de rango.

#### Paso 8: Tests de PredictionService

**Archivo nuevo**: `backend/tests/unit/test_prediction_service.py`

**Tests**:
- `test_prediction_returns_valid_probabilities`: Probabilidades suman ~1.0.
- `test_insufficient_data_raises`: Con < mínimo de matches → `InsufficientDataException`.
- `test_zero_stats_fallback`: Si stats de equipo son 0, debe usar promedios de liga (RULES.md §2B).
- `test_prediction_goals_non_negative`: Goles predichos siempre ≥ 0.

#### Paso 9: Configurar coverage

**Archivo**: `backend/pyproject.toml`  
**Cambiar** `addopts` a:
```toml
addopts = "-v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=30"
```

#### Paso 10: Validación

```bash
cd backend
pytest -v
# Debe ejecutar >30 tests, todos pasando
# Coverage debe ser ≥30%
```

#### Paso 11: Commit

**Commit message**: `test(backend): tests unitarios para dominio, risk management y scoring`

---

### Bloque 1.E — Tests Frontend Críticos

**Spec refs**: §5.5.1, §5.5.2, §5.5.3  
**Dependencias**: Bloque 1.A (para que CI valide)  
**PR**: `test(frontend): tests de componentes, hooks y stores principales`

#### Paso 1: Tests de stores (no requieren renderizado)

**Archivos nuevos**:

1. `frontend/src/application/stores/usePredictionStore.test.ts`
2. `frontend/src/application/stores/useParleyStore.test.ts`

**Contenido para `usePredictionStore.test.ts`**:
```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { usePredictionStore } from "./usePredictionStore";

describe("usePredictionStore", () => {
  beforeEach(() => {
    usePredictionStore.getState().reset?.();
    // O limpiar estado manualmente si no hay reset
  });

  it("debería inicializar con estado vacío", () => {
    const state = usePredictionStore.getState();
    expect(state.predictions).toBeDefined();
  });

  it("debería setear predicciones", () => {
    // Adaptar según la API real del store
    const { setPredictions } = usePredictionStore.getState();
    if (setPredictions) {
      setPredictions([/* mock predictions */]);
      expect(usePredictionStore.getState().predictions.length).toBeGreaterThan(0);
    }
  });

  // ... más tests según la interfaz real del store
});
```

**Nota**: El agente implementador DEBE leer la interfaz real de cada store antes de escribir los tests.

**Contenido para `useParleyStore.test.ts`**:
- `test_add_pick`: Agregar 1 pick → store tiene 1 pick.
- `test_remove_pick`: Agregar y remover → store vacío.
- `test_max_10_picks`: Intentar agregar 11 picks → solo 10 presentes.
- `test_clear_parley`: Limpiar → estado vacío.

#### Paso 2: Tests de hooks

**Archivos nuevos**:

1. `frontend/src/hooks/usePredictions.test.ts`
2. `frontend/src/hooks/useLeagues.test.ts`

**Patrón para tests de hooks**:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { usePredictions } from "./usePredictions";

// Mock de la API
vi.mock("../infrastructure/api/predictions", () => ({
  fetchPredictions: vi.fn(),
}));

describe("usePredictions", () => {
  it("debería inicializar en estado loading", () => {
    const { result } = renderHook(() => usePredictions("E0"));
    expect(result.current.loading).toBe(true);
  });

  it("debería manejar error de API", async () => {
    // Configurar mock para fallar
    // Verificar que error se setea correctamente
  });
});
```

#### Paso 3: Tests de componentes

**Archivos nuevos**:

1. `frontend/src/presentation/components/MatchCard/MatchCard.test.tsx`
2. `frontend/src/presentation/components/PredictionGrid/PredictionGrid.test.tsx`
3. `frontend/src/presentation/components/Parley/ParleySlip.test.tsx`
4. `frontend/src/presentation/components/BotDashboard/BotDashboard.test.tsx`

**Patrón para tests de componentes**:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MatchCard from "./MatchCard";

// Mock de datos según tipos reales de src/types/
const mockMatchPrediction = {
  // ... adaptar a la interfaz real de MatchPrediction
};

describe("MatchCard", () => {
  it("debería renderizar nombre de equipos", () => {
    render(<MatchCard matchPrediction={mockMatchPrediction} />);
    expect(screen.getByText(/Arsenal/i)).toBeInTheDocument();
    expect(screen.getByText(/Chelsea/i)).toBeInTheDocument();
  });

  it("debería mostrar predicción cuando existe", () => {
    render(<MatchCard matchPrediction={mockMatchPrediction} />);
    // Verificar que hay elementos de predicción visibles
  });
});
```

**Nota importante**: Muchos componentes MUI pueden necesitar un `ThemeProvider` wrapper. Crear un helper:

**Archivo nuevo**: `frontend/src/test-utils.tsx`
```tsx
import { ReactNode } from "react";
import { ThemeProvider } from "@mui/material/styles";
import { render, RenderOptions } from "@testing-library/react";
import { theme } from "./theme";  // Ajustar path al tema existente

function Wrapper({ children }: { children: ReactNode }) {
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}

export function renderWithTheme(ui: React.ReactElement, options?: RenderOptions) {
  return render(ui, { wrapper: Wrapper, ...options });
}
```

#### Paso 4: Validación

```bash
cd frontend
npx vitest run
# Debe ejecutar >20 tests, todos pasando
```

#### Paso 5: Commit

**Commit message**: `test(frontend): tests de componentes, hooks y stores principales`

---

### Bloque 1.F — Merge y Validación de Fase 1

**Dependencias**: Todos los bloques 1.A-1.E  
**Acciones**:

1. Rebase de todos los PRs de Fase 1 (resolver conflictos si existen)
2. Merge secuencial: 1.A → 1.B → 1.C → 1.D → 1.E
3. Verificar que CI pasa en `main` después de todos los merges
4. Validar métricas de §9:
   - Tests backend: >30 ✓
   - Tests frontend: >20 ✓
   - Coverage backend: ≥30% ✓
   - Bare excepts: 0 ✓
   - CI pipeline: 1 ✓
   - API auth: API key admin ✓

---

## 3. Fase 2 — Calidad Profesional

> **Requisito**: Fase 1 completada y mergeada a `main`.  
> **PRs estimados**: 7

### Bloque 2.A — Prettier + Pre-commit

**Spec refs**: §6.1, §6.2  
**Dependencias**: Fase 1 completada  
**PR**: `chore(frontend): configurar Prettier y pre-commit hooks con husky`

#### Pasos:
1. Instalar: `cd frontend && npm install -D prettier husky lint-staged`
2. Crear `frontend/.prettierrc` con configuración del spec
3. Agregar scripts `format` y `format:check` a `package.json`
4. Configurar `lint-staged` en `package.json`
5. Inicializar husky: `npx husky init && echo "cd frontend && npx lint-staged" > .husky/pre-commit`
6. Ejecutar `npm run format` para formatear todo el código existente
7. Agregar `format:check` al workflow CI (en el job `frontend-lint`)
8. Validar: commit de un `.tsx` ejecuta eslint + prettier automáticamente

**Commit**: `chore(frontend): configurar Prettier, husky y lint-staged`

---

### Bloque 2.B — Eliminar `any` en Frontend

**Spec refs**: §6.3  
**Dependencias**: Ninguna (paralelo con 2.A)  
**PR**: `refactor(frontend): eliminar 8 usos de any con tipado estricto`

#### Pasos detallados:

1. **Definir `LiveMatchRaw` en `src/types/index.ts`**:
   - Leer la forma real del dato en `useLiveMatches.ts` L307 para inferir la interfaz
   - Agregar la interfaz con todos los campos necesarios

2. **Corregir `useLiveMatches.ts`**:
   - Cambiar `(match: any)` → `(match: LiveMatchRaw)` 

3. **Corregir `useCacheStore.ts`**:
   - Cambiar `predictions: any[]` → `predictions: MatchPrediction[]`
   - Importar `MatchPrediction` de `../../types`

4. **Corregir `matchMatching.ts`**:
   - Cambiar `prediction?: any` → `prediction?: MatchPrediction`

5. **Corregir `marketUtils.ts`**:
   - Cambiar `picks: any[]` → `picks: SuggestedPick[]`

6. **Corregir `LocalStorageObserver.ts`** (hacer genérico):
   ```typescript
   type StorageCallback<T = unknown> = (data: T) => void;
   ```

7. **Validar**: `npm run lint` → 0 errores, 0 warnings de `@typescript-eslint/no-explicit-any`
8. **Validar**: `npm run build` → exitoso

**Commit**: `refactor(frontend): reemplazar 8 usos de any por tipos estrictos`

---

### Bloque 2.C — Eliminar API Legacy

**Spec refs**: §6.4  
**Dependencias**: Bloque 2.B completado (tipos limpios)  
**PR**: `refactor(frontend): eliminar api legacy y consolidar infrastructure/api/`

#### Pasos:
1. Buscar todos los imports de `services/api`:
   ```bash
   grep -rn "from.*services/api\|import.*services/api" frontend/src/
   ```
2. Para cada import encontrado, identificar el equivalente en `infrastructure/api/`
3. Migrar cada import
4. Eliminar `frontend/src/services/api.ts`
5. Si `frontend/src/services/` queda vacío, eliminar la carpeta
6. Validar: `npm run build` + `npm run lint` + `npx vitest run`

**Commit**: `refactor(frontend): eliminar services/api.ts legacy y consolidar en infrastructure/api/`

---

### Bloque 2.D — ML Model Versioning

**Spec refs**: §6.6.1, §6.6.2, §6.6.3  
**Dependencias**: Ninguna (paralelo)  
**PR**: `feat(backend): model registry con métricas y sacar .joblib del repo`

#### Pasos:

1. **Crear registry vacío**: `backend/ml_models/registry.json`
   ```json
   {"models": [], "last_updated": null}
   ```

2. **Crear `.gitkeep`**: `backend/ml_models/.gitkeep`

3. **Modificar `train_model_optimized.py`**:
   - Después de entrenar cada modelo, calcular métricas con `sklearn.metrics`:
     ```python
     from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
     ```
   - Escribir/actualizar `registry.json` con las métricas del modelo recién entrenado
   - Incluir: league, target, version (timestamp), file, metrics, training_date, training_days

4. **Agregar al `.gitignore`**:
   ```
   # Modelos ML (generados por pipeline local)
   backend/ml_models/*.joblib
   backend/ml_picks_classifier.joblib
   backend/learning_weights.json
   ```

5. **Quitar modelos del tracking de Git** (sin borrar los archivos locales):
   ```bash
   git rm --cached backend/ml_models/*.joblib backend/ml_picks_classifier.joblib backend/learning_weights.json
   ```

6. **Actualizar endpoint `/api/v1/train/status`** en `main.py`:
   - Leer `registry.json` y devolver `model_version` y `accuracy` del último modelo

7. **Validar**: `run_dev_pipeline.sh` genera modelos + actualiza `registry.json`

**Commit**: `feat(backend): model registry JSON con métricas y excluir .joblib del repo`

---

### Bloque 2.E — Structured Logging

**Spec refs**: §6.7  
**Dependencias**: Bloque 1.C completado (error handling limpio)  
**PR**: `refactor(backend): structured logging JSON con formatter centralizado`

#### Pasos:

1. **Crear** `backend/src/core/logging_config.py` con `JSONFormatter` + `configure_logging()` (código del spec §6.7)

2. **Modificar `backend/src/api/main.py`**:
   - Agregar al inicio (antes de crear la app):
     ```python
     from src.core.logging_config import configure_logging
     configure_logging(os.getenv("LOG_LEVEL", "INFO"))
     ```
   - Eliminar cualquier `logging.basicConfig(...)` existente

3. **Modificar `backend/src/worker.py`**:
   - Agregar al inicio:
     ```python
     from src.core.logging_config import configure_logging
     configure_logging(os.getenv("LOG_LEVEL", "INFO"))
     ```
   - Eliminar la línea `logging.basicConfig(level=logging.INFO, format=...)`

4. **Buscar y eliminar** TODOS los `logging.basicConfig(...)` en `backend/src/`:
   ```bash
   grep -rn "logging.basicConfig" backend/src/
   ```
   Eliminar cada uno encontrado (la configuración centralizada se encarga).

5. **Tests**:
   ```python
   # backend/tests/unit/test_logging_config.py
   def test_json_formatter_output():
       import json
       from src.core.logging_config import JSONFormatter
       import logging
       formatter = JSONFormatter()
       record = logging.LogRecord("test", logging.INFO, "module", 1, "test msg", (), None)
       output = formatter.format(record)
       parsed = json.loads(output)
       assert parsed["level"] == "INFO"
       assert parsed["message"] == "test msg"
       assert "timestamp" in parsed
   ```

6. **Validar**: Levantar la API y verificar que los logs salen en JSON

**Commit**: `refactor(backend): structured logging JSON centralizado`

---

### Bloque 2.F — Coverage Ampliado Backend

**Spec refs**: §6.5  
**Dependencias**: Bloque 1.D completado  
**PR**: `test(backend): tests adicionales para coverage ≥60%`

#### Tests adicionales:
- `tests/unit/test_learning_service.py`: Weights update, feedback loop
- `tests/unit/test_statistics_service.py`: Team stats calculation correcta
- `tests/unit/test_match_aggregator.py`: Agregación multi-fuente con prioridad (UK > Org > Open)
- `tests/integration/test_api_endpoints.py`: GET /health (200), GET /leagues (200, JSON array), GET /predictions (200 o 404)
- `tests/integration/test_mongo_repository.py`: CRUD operations con mock/in-memory

**Subir umbral**: `pyproject.toml` → `--cov-fail-under=60`

**Commit**: `test(backend): tests adicionales, coverage ≥60%`

---

### Bloque 2.G — Coverage Ampliado Frontend

**Spec refs**: §6.5  
**Dependencias**: Bloque 1.E completado  
**PR**: `test(frontend): tests adicionales para coverage ≥40%`

#### Tests adicionales:
- Tests de `LeagueSelector`, `MatchDetailsModal`
- Tests de hooks restantes: `useSmartPolling`, `useAppVisibility`
- Tests de utils: `matchMatching.ts`, `marketUtils.ts`
- Configurar `vitest` con coverage threshold:
  ```typescript
  // vite.config.ts - sección test
  coverage: {
    provider: "v8",
    thresholds: { lines: 40 },
  }
  ```

**Commit**: `test(frontend): tests adicionales, coverage ≥40%`

---

### Bloque 2.H — Merge y Validación de Fase 2

**Acciones**:
1. Merge secuencial de 2.A → 2.B → 2.C → 2.D → 2.E → 2.F → 2.G
2. Validar métricas de §9:
   - `any` en TS: 0 ✓
   - Coverage backend: ≥60% ✓
   - Coverage frontend: ≥40% ✓
   - ML model versioning: Registry JSON ✓
   - Structured logging: JSON ✓
   - Prettier: Configurado ✓

---

## 4. Fase 3 — Madurez Operativa

> **Requisito**: Fase 2 completada.  
> **PRs estimados**: 6

### Bloque 3.A — Alembic (Migraciones PostgreSQL)

**Spec refs**: §7.1  
**PR**: `feat(backend): alembic para migraciones de PostgreSQL`

### Bloque 3.B — Multi-Stage Dockerfile

**Spec refs**: §7.2  
**PR**: `chore(devops): dockerfile multi-stage para imagen ≤500MB`

### Bloque 3.C — Sentry Monitoring

**Spec refs**: §7.3  
**Dependencia**: Bloque 2.E (structured logging)  
**PR**: `feat(backend): integrar Sentry para monitoreo de errores`

### Bloque 3.D — Accesibilidad WCAG 2.1 AA

**Spec refs**: §7.4  
**PR**: `feat(frontend): accesibilidad WCAG 2.1 AA con ARIA y eslint-plugin-jsx-a11y`

### Bloque 3.E — Desacoplar Domain de Infrastructure

**Spec refs**: §7.5  
**Dependencia**: Bloque 1.D (tests protegen el refactor)  
**PR**: `refactor(backend): desacoplar domain services de infrastructure via interfaces`

### Bloque 3.F — Limpieza de Deuda Técnica

**Spec refs**: §7.6  
**PR**: `chore: limpiar deuda técnica (.bak, stubs, CORS fallback, .env.example)`

---

## 5. Resumen de PRs Totales

| Fase | Bloque | PR Title | Tipo |
|---|---|---|---|
| 1 | 1.A | `ci: desbloquear .github/ y crear workflow CI para PRs` | CI |
| 1 | 1.B | `fix(backend): API key admin + rate limiting` | Seguridad |
| 1 | 1.C | `fix(backend): middleware global de errores + limpieza bare excepts` | Calidad |
| 1 | 1.D | `test(backend): tests unitarios dominio, riesgo, scoring` | Testing |
| 1 | 1.E | `test(frontend): tests componentes, hooks, stores` | Testing |
| 2 | 2.A | `chore(frontend): Prettier + husky + lint-staged` | Tooling |
| 2 | 2.B | `refactor(frontend): eliminar 8 usos de any` | Tipado |
| 2 | 2.C | `refactor(frontend): consolidar API en infrastructure/` | Cleanup |
| 2 | 2.D | `feat(backend): model registry + sacar .joblib del repo` | ML Ops |
| 2 | 2.E | `refactor(backend): structured logging JSON` | Observabilidad |
| 2 | 2.F | `test(backend): coverage ≥60%` | Testing |
| 2 | 2.G | `test(frontend): coverage ≥40%` | Testing |
| 3 | 3.A | `feat(backend): Alembic migraciones PostgreSQL` | DB |
| 3 | 3.B | `chore(devops): Dockerfile multi-stage` | Infra |
| 3 | 3.C | `feat(backend): Sentry monitoring` | Observabilidad |
| 3 | 3.D | `feat(frontend): accesibilidad WCAG 2.1 AA` | a11y |
| 3 | 3.E | `refactor(backend): desacoplar domain via interfaces` | Arquitectura |
| 3 | 3.F | `chore: limpieza deuda técnica` | Cleanup |
| **Total** | | **18 PRs** | |

---

## 6. Diagrama de Dependencias entre Bloques

```
FASE 1:
  1.A (CI/CD) ─────────────────────────────┐
  1.B (Seguridad) ──────────────────────────┤
  1.C (Error Handling) ────┐                │
                           ├── 1.D (Tests Backend)
                           │                │
  1.A ─────────────────────┴── 1.E (Tests Frontend)
                                            │
                    ┌───────────────────────┘
                    ▼
FASE 2:
  2.A (Prettier) ──── 2.C (API Legacy) ────┐
  2.B (any) ──────────┘                     │
  2.D (ML Registry) ────────────────────────┤
  2.E (Logging) ────────────────────────────┤
  1.D → 2.F (Coverage Backend) ────────────┤
  1.E → 2.G (Coverage Frontend) ───────────┘
                                            │
                    ┌───────────────────────┘
                    ▼
FASE 3:
  3.A (Alembic) ────────────────────────────┐
  3.B (Docker Multi-stage) ─────────────────┤
  2.E → 3.C (Sentry) ──────────────────────┤
  3.D (a11y) ───────────────────────────────┤
  1.D → 3.E (Desacoplar Domain) ───────────┤
  3.F (Cleanup) ────────────────────────────┘
```

---

*Siguiente artefacto*: `tasks.md` con cada tarea atómica, asignación de agente, y checklist de verificación.
