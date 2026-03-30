# Spec: Viability Uplift — BJJ-BetSports

**Fecha**: 28 de marzo de 2026  
**Autor**: Orchestrator (Copilot)  
**Branch propuesta**: `feat/viability-uplift`  
**Estado**: Draft  

---

## 1. Resumen Ejecutivo

Este spec define el plan maestro para llevar BJJ-BetSports de un prototipo funcional a un producto viable y mantenible. Tras una auditoría completa del proyecto se identificaron **16 déficits** organizados en 3 fases de ejecución. Cada fase produce valor incremental y deja el proyecto en un estado estable.

---

## 2. Contexto y Motivación

### 2.1 Estado actual del proyecto

| Dimensión | Estado | Evidencia |
|---|---|---|
| Test coverage backend | ~1% (3 tests en `test_time_utils.py`) | Solo 1 archivo en `tests/unit/` |
| Test coverage frontend | ~5% (4 tests de renderizado básico) | 4 archivos `.test.tsx` |
| CI/CD | **Inexistente** | No hay `.github/workflows/` — `.github/` está en `.gitignore` |
| Autenticación API | **Ninguna** | Todos los endpoints públicos, incluyendo `POST /train/run-now` |
| Rate limiting | **Ninguno** | Sin `slowapi` ni equivalente |
| Error handling | **Deficiente** | 3 bare `except:`, 7+ `except Exception: pass`, sin middleware global |
| ML Ops | **Inmaduro** | Sin versionado de modelos, sin métricas guardadas, sin drift detection |
| Migraciones DB | **Inexistentes** | MongoDB sin schema validation, PostgreSQL con `create_tables()` |
| Accesibilidad (a11y) | **Cero** | 0 atributos ARIA explícitos en ~33 componentes |
| Prettier frontend | **No configurado** | Sin `.prettierrc` ni dependencia |
| `any` en TypeScript | 8 violaciones | `useLiveMatches.ts`, `useCacheStore.ts`, `matchMatching.ts`, `marketUtils.ts`, `LocalStorageObserver.ts` |
| Duplicación API frontend | Presente | `services/api.ts` (legacy) + `infrastructure/api/` (nuevo) |
| Modelos ML en Git | **Sí** | 18 `.joblib` + `learning_weights.json` commiteados |
| Structured logging | **No** | Solo `logging.basicConfig()` plano |
| Monitoreo | **Ninguno** | Sin Sentry, sin Prometheus, sin alertas |
| Dockerfile | **No multi-stage** | `Dockerfile.portable` con una sola capa Python+Node |

### 2.2 Lo que ya funciona bien

- Arquitectura DDD con capas bien separadas (domain/application/infrastructure)
- Value objects inmutables con validación en `__post_init__`
- Repository interfaces como ABCs (DIP correcto)
- Stack moderno: React 19, Vite 7, MUI 7, Zustand 5, FastAPI
- PWA completa: manifest, workbox, auto-update, offline indicator
- TypeScript `strict: true` con `noUnusedLocals`
- Build optimization: SWC, code splitting, gzip + brotli
- Docker Compose portable con imagen única reutilizable
- RULES.md exhaustivas con reglas de negocio, riesgo y calidad

---

## 3. Alcance

### 3.1 Incluido

- **Fase 1**: Fundamentos de viabilidad (CI/CD, testing crítico, seguridad API, error handling)
- **Fase 2**: Calidad profesional (coverage amplio, ML Ops básico, linting, pre-commit)
- **Fase 3**: Madurez operativa (migraciones, monitoring, a11y, cleanup de deuda técnica)

### 3.2 Excluido

- Cambio de framework (migrar de FastAPI, cambiar React por otro)
- Nuevas funcionalidades de negocio (nuevas ligas, nuevos mercados)
- Migración de hosting (salir de Render)
- Rediseño de UI/UX

---

## 4. Restricciones Técnicas

| Restricción | Detalle |
|---|---|
| **Idioma** | Todo en español (respuestas, commits, documentación) |
| **TypeScript** | `any` prohibido — 0 tolerancia |
| **Python** | Type hints completos en todas las firmas (`mypy --disallow-untyped-defs`) |
| **Commits** | Conventional Commits: `feat:`, `fix:`, `refactor:`, `chore:`, `test:`, `ci:` |
| **PRs** | Atómicos, un concepto por PR |
| **RULES.md** | Fuente de verdad — todas las reglas son mandatorias |
| **Arquitectura** | Clean Architecture + DDD — no romper capas existentes |
| **Build** | PR no puede romper `cd frontend && npm run build` ni `cd backend && pytest -v` |

---

## 5. Fase 1 — Fundamentos de Viabilidad

> **Objetivo**: Sin esto el proyecto NO puede considerarse viable. Bloquea cualquier uso serio.

### 5.1 Desbloquear CI/CD

#### 5.1.1 Quitar `.github/` del `.gitignore`

**Archivo**: `.gitignore` (raíz)  
**Cambio**: Eliminar las líneas:
```
.github/
.claude/
```
**Reemplazar por**:
```
# Mantener agentes Claude locales (no versionar)
.claude/
```
**Justificación**: `.github/` contiene los workflows de CI, los agents de Copilot y los skills. Sin versionarlos, el CI no puede existir.

**Riesgo**: Los archivos en `.github/` podrían tener contenido sensible → auditar antes de commit.  
**Mitigación**: Revisar que no haya secrets en `.github/agents/`, `.github/skills/`, `.github/prompts/`.

#### 5.1.2 Crear workflow de CI para PRs

**Archivo nuevo**: `.github/workflows/ci.yml`  
**Triggers**: `pull_request` → branches `[main, develop, feature/*]`  
**Jobs**:

```yaml
jobs:
  backend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest -v --tb=short
      - run: cd backend && python -m mypy src/ --ignore-missing-imports
      - run: cd backend && python -m black --check src/ tests/

  frontend-checks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
      - run: cd frontend && npx vitest run
```

**Criterio de aceptación**:
- El workflow se ejecuta en cada PR
- Si falla lint, build, types o tests → PR no puede hacer merge
- Timeout máximo: 15 minutos por job

#### 5.1.3 Crear workflow de deploy (opcional, Fase 1b)

**Archivo nuevo**: `.github/workflows/deploy.yml`  
**Trigger**: Push a `main`  
**Acción**: Trigger deploy en Render via webhook o `render-deploy-action`

---

### 5.2 Seguridad API Mínima

#### 5.2.1 API Key para endpoints sensibles

**Archivos a modificar**:
- `backend/src/api/main.py`

**Diseño**:
```python
# Nuevo: middleware/dependencia de autenticación
import os
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

async def require_admin_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    if not ADMIN_API_KEY or api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return api_key
```

**Endpoints protegidos** (requieren `Depends(require_admin_key)`):
| Endpoint | Razón |
|---|---|
| `POST /api/v1/train/run-now` | Dispara entrenamiento ML costoso |
| `POST /api/v1/cache/clear` | Borra caché del sistema |
| `DELETE /api/v1/predictions/*` | Elimina datos |

**Endpoints públicos** (sin cambio):
| Endpoint | Razón |
|---|---|
| `GET /health` | Health check de infra |
| `GET /api/v1/leagues` | Lectura no sensitiva |
| `GET /api/v1/predictions/*` | Lectura no sensitiva |
| `GET /api/v1/matches/*` | Lectura no sensitiva |
| `GET /api/v1/train/status` | Solo lectura del estado |

**Variables de entorno nuevas**:
- `ADMIN_API_KEY`: String aleatorio para auth de admin

**Criterio de aceptación**:
- `POST /train/run-now` sin header → 403
- `POST /train/run-now` con `X-API-Key: <correcto>` → 200
- Endpoints GET siguen funcionando sin auth

#### 5.2.2 Rate Limiting

**Dependencia nueva**: `slowapi==0.1.9`  
**Archivos a modificar**: `backend/requirements.txt`, `backend/src/api/main.py`

**Diseño**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# Límites:
# - Endpoints de lectura: 60/minuto
# - Endpoints de escritura/admin: 5/minuto
# - Health check: sin límite
```

**Criterio de aceptación**:
- 61ª request en 1 minuto a `/api/v1/leagues` → 429 Too Many Requests
- Health check nunca recibe 429

---

### 5.3 Error Handling Global

#### 5.3.1 Middleware de excepciones en FastAPI

**Archivo**: `backend/src/api/main.py`

**Diseño**:
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

**Criterio de aceptación**:
- Error no manejado en un endpoint → 500 con JSON + log con traceback completo
- Nunca exponer stack trace al cliente

#### 5.3.2 Eliminar bare `except:` y `except: pass`

**Archivos afectados** (3 bare `except:` sin especificar excepción):

| Archivo | Línea | Cambio |
|---|---|---|
| `backend/src/infrastructure/data_sources/espn.py` | L148 | `except:` → `except (ValueError, TypeError):` |
| `backend/src/infrastructure/data_sources/espn.py` | L426 | `except:` → `except (ValueError, TypeError):` |
| `backend/src/domain/services/ml_feature_extractor.py` | L144 | `except:` → `except statistics.StatisticsError:` |

**Archivos con `except Exception: pass`** (mínimo 7 que silencian errores sin logging):

| Archivo | Línea(s) | Cambio |
|---|---|---|
| `backend/src/application/use_cases/use_cases.py` | L911, L1188, L1198 | Agregar `logger.debug(...)` mínimo |
| `backend/src/application/use_cases/suggested_picks_use_case.py` | L447, L462 | Agregar `logger.debug(...)` |
| `backend/src/application/use_cases/live_predictions_use_case.py` | L421, L436, L469, L513 | Agregar `logger.debug(...)` |
| `backend/src/application/use_cases/get_parleys_use_case.py` | L45 | Agregar `logger.debug(...)` |

**Criterio de aceptación**:
- `grep -rn "except:" backend/src/ | grep -v "except Exception" | grep -v "except ("` → 0 resultados de bare except
- `grep -rn "except.*:.*pass$\|except.*:\n.*pass$" backend/src/` → 0 resultados de error silenciado sin log
- Cada `except` tiene al mínimo un `logger.debug()` o `logger.warning()`

---

### 5.4 Tests Unitarios Críticos (Backend)

#### 5.4.1 Tests para lógica de dinero/scoring (obligatorio por RULES.md §6)

**Archivos nuevos**:

| Archivo de test | Módulo cubierto | Tests mínimos |
|---|---|---|
| `tests/unit/test_risk_manager.py` | `domain/services/risk_management/risk_manager.py` | - `test_max_stake_hard_cap` (5% bankroll) <br>- `test_circuit_breaker_activates_on_loss_streak` <br>- `test_ev_positive_filter` (solo `prob * odds > 1.0`) <br>- `test_reject_negative_ev_bet` |
| `tests/unit/test_bankroll_service.py` | `domain/services/risk_management/bankroll_service.py` | - `test_initial_bankroll` <br>- `test_bankroll_after_win` <br>- `test_bankroll_after_loss` <br>- `test_kelly_criterion_calculation` |
| `tests/unit/test_picks_service.py` | `domain/services/picks_service.py` | - `test_generate_picks_all_markets_present` (winner, goles, corners, tarjetas) <br>- `test_no_empty_picks_for_corners_cards` (RULES.md §16) <br>- `test_pick_recommendation_logic` <br>- `test_odds_anomaly_detection` (cuotas < 1.01 o > 1000) |
| `tests/unit/test_confidence_calculator.py` | `domain/services/confidence_calculator.py` | - `test_high_confidence_with_strong_data` <br>- `test_low_confidence_with_sparse_data` <br>- `test_confidence_bounds_0_to_1` |
| `tests/unit/test_prediction_service.py` | `domain/services/prediction_service.py` | - `test_prediction_with_sufficient_data` <br>- `test_prediction_raises_insufficient_data` <br>- `test_zero_stats_fallback` (RULES.md §2B) <br>- `test_probability_sum_equals_1` |

#### 5.4.2 Tests para entities y value objects

**Archivos nuevos**:

| Archivo de test | Tests mínimos |
|---|---|
| `tests/unit/test_entities.py` | - `test_match_creation` <br>- `test_prediction_dataclass_fields` <br>- `test_suggested_pick_market_types` <br>- `test_betting_feedback_immutability` |
| `tests/unit/test_value_objects.py` | - `test_probability_bounds_validation` <br>- `test_odds_minimum_validation` <br>- `test_score_non_negative` <br>- `test_frozen_immutability` |

#### 5.4.3 Configurar coverage mínimo

**Archivo**: `backend/pyproject.toml`  
**Cambio**: Agregar `--cov=src --cov-report=term-missing --cov-fail-under=30` a `addopts`

**Criterio de aceptación**:
- `cd backend && pytest -v` ejecuta >30 tests
- Coverage ≥30% del directorio `src/`
- Falla si coverage baja del umbral

---

### 5.5 Tests Críticos (Frontend)

#### 5.5.1 Tests de componentes principales

**Archivos nuevos**:

| Archivo de test | Componente | Tests mínimos |
|---|---|---|
| `src/presentation/components/MatchCard/MatchCard.test.tsx` | `MatchCard` | - Renderiza nombre de equipos <br>- Muestra predicción cuando existe <br>- Muestra estado loading |
| `src/presentation/components/PredictionGrid/PredictionGrid.test.tsx` | `PredictionGrid` | - Renderiza lista de predicciones <br>- Muestra empty state sin datos <br>- Filtra por liga |
| `src/presentation/components/Parley/ParleySlip.test.tsx` | `ParleySlip` | - Agrega pick al parley <br>- No permite más de 10 picks <br>- Calcula odds combinadas |
| `src/presentation/components/BotDashboard/BotDashboard.test.tsx` | `BotDashboard` | - Renderiza stats de entrenamiento <br>- Muestra skeleton durante loading <br>- Muestra error state |

#### 5.5.2 Tests de hooks

| Archivo de test | Hook | Tests mínimos |
|---|---|---|
| `src/hooks/usePredictions.test.ts` | `usePredictions` | - Fetch exitoso devuelve data <br>- Maneja error de API <br>- Devuelve loading true durante fetch |
| `src/hooks/useLeagues.test.ts` | `useLeagues` | - Carga ligas desde API <br>- Maneja error de red |

#### 5.5.3 Tests de stores

| Archivo de test | Store | Tests mínimos |
|---|---|---|
| `src/application/stores/usePredictionStore.test.ts` | `usePredictionStore` | - Set/get predicciones <br>- Filtra por liga <br>- Resetea estado |
| `src/application/stores/useParleyStore.test.ts` | `useParleyStore` | - Agrega pick <br>- Elimina pick <br>- No excede max 10 |

**Criterio de aceptación**:
- `cd frontend && npx vitest run` ejecuta >20 tests pasando
- 0 tests skipped o pending

---

## 6. Fase 2 — Calidad Profesional

> **Objetivo**: Alcanzar estándares de proyecto mantenible para un equipo.

### 6.1 Configurar Prettier en Frontend

**Archivos nuevos**: `frontend/.prettierrc`  
**Dependencias nuevas**: `prettier` (devDependency)  
**Scripts nuevos en `package.json`**: 
```json
"format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
"format:check": "prettier --check \"src/**/*.{ts,tsx,css}\""
```

**Configuración**:
```json
{
  "semi": true,
  "singleQuote": false,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100
}
```

**Criterio de aceptación**:
- `npm run format:check` pasa sin errores
- CI ejecuta `format:check` en cada PR

### 6.2 Pre-commit Hooks (husky + lint-staged)

**Dependencias nuevas**: `husky`, `lint-staged` (raíz o frontend)  
**Configuración** en `package.json` del frontend:
```json
"lint-staged": {
  "src/**/*.{ts,tsx}": ["eslint --fix", "prettier --write"],
  "src/**/*.css": ["prettier --write"]
}
```

**Criterio de aceptación**:
- `git commit` de un archivo `.tsx` ejecuta eslint + prettier automáticamente
- Bloquea commit si hay errores de lint

### 6.3 Eliminar 8 usos de `any` en Frontend

**Archivos y cambios específicos**:

| Archivo | Línea | `any` actual | Tipo correcto |
|---|---|---|---|
| `src/hooks/useLiveMatches.ts` | ~L307 | `(match: any)` | `(match: LiveMatchRaw)` — definir interfaz en `types/index.ts` |
| `src/application/stores/useCacheStore.ts` | ~L22 | `predictions: any[]` | `predictions: MatchPrediction[]` |
| `src/application/stores/useCacheStore.ts` | ~L89 | `action con any` | Tipar con `MatchPrediction[]` |
| `src/utils/matchMatching.ts` | ~L25 | `prediction?: any` | `prediction?: MatchPrediction` |
| `src/utils/marketUtils.ts` | ~L61 | `picks: any[]` | `picks: SuggestedPick[]` |
| `src/infrastructure/storage/LocalStorageObserver.ts` | ~L11 | `StorageCallback = (data: any)` | `StorageCallback<T> = (data: T)` genérico |
| `src/infrastructure/storage/LocalStorageObserver.ts` | ~L64 | `any` | Tipar con genérico |
| `src/infrastructure/storage/LocalStorageObserver.ts` | ~L85 | `any` | Tipar con genérico |

**Criterio de aceptación**:
- `grep -rn "any" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v "node_modules" | grep -v "//" | grep -v "Company"` → 0 resultados de `any` como tipo
- `npm run lint` pasa sin warnings

### 6.4 Eliminar API Legacy Duplicada

**Archivo a eliminar**: `frontend/src/services/api.ts`
**Cambio**: Buscar todos los imports de `../../services/api` o `../services/api` y redirigir a `infrastructure/api/`

**Pasos**:
1. Auditar quién importa de `services/api.ts` vs `infrastructure/api/`
2. Migrar cada import al módulo equivalente en `infrastructure/api/`
3. Eliminar `frontend/src/services/api.ts`
4. Eliminar `frontend/src/services/` si queda vacío

**Criterio de aceptación**:
- `frontend/src/services/api.ts` no existe
- `npm run build` pasa exitosamente
- Todos los componentes importan de `infrastructure/api/`

### 6.5 Coverage Ampliado

**Backend**: Subir `cov-fail-under` de 30 a 60 (en `pyproject.toml`)  
**Frontend**: Agregar `vitest.config` con `coverage.thresholds.lines: 40`

**Tests adicionales backend**:

| Archivo de test | Módulo | Tests |
|---|---|---|
| `tests/unit/test_learning_service.py` | `domain/services/learning_service.py` | Weights update, feedback loop |
| `tests/unit/test_statistics_service.py` | `domain/services/statistics_service.py` | Team stats calculation |
| `tests/unit/test_match_aggregator.py` | `domain/services/match_aggregator_service.py` | Multi-source aggregation, priority |
| `tests/integration/test_api_endpoints.py` | `src/api/main.py` | GET /health, GET /leagues, GET /predictions/:league |
| `tests/integration/test_mongo_repository.py` | `infrastructure/repositories/mongo_repository.py` | CRUD con testcontainers o mock |

**Criterio de aceptación**:
- Backend coverage ≥60%
- Frontend coverage ≥40%
- CI falla si coverage baja

### 6.6 Model Versioning (ML Ops Básico)

#### 6.6.1 Model Registry JSON

**Archivo nuevo**: `backend/ml_models/registry.json`  
**Estructura**:
```json
{
  "models": [
    {
      "league": "E0",
      "target": "winner",
      "version": "2026-03-28T06:00:00",
      "file": "E0_winner.joblib",
      "metrics": {
        "accuracy": 0.6745,
        "precision": 0.68,
        "recall": 0.65,
        "f1": 0.665,
        "samples": 4912
      },
      "training_date": "2026-03-28",
      "training_days": 550
    }
  ]
}
```

#### 6.6.2 Guardar métricas al entrenar

**Archivo a modificar**: `backend/scripts/train_model_optimized.py`  
**Cambio**: Después de entrenar cada modelo, calcular `accuracy`, `precision`, `recall`, `f1` y append al registry.

#### 6.6.3 Sacar `.joblib` del repo Git

**Archivo**: `.gitignore`  
**Agregar**:
```
backend/ml_models/*.joblib
backend/ml_picks_classifier.joblib
backend/learning_weights.json
```

**Archivo nuevo**: `backend/ml_models/.gitkeep`  
**Migración**: Los modelos se generan con `run_dev_pipeline.sh` — no necesitan estar commiteados.

**Criterio de aceptación**:
- `registry.json` se actualiza en cada entrenamiento con métricas
- `GET /api/v1/train/status` incluye `model_version` y `accuracy` del último entrenamiento
- Los `.joblib` no están en el repositorio Git

### 6.7 Structured Logging

**Dependencia nueva**: No — usar el módulo `logging` estándar con un formatter JSON.  
**Archivo nuevo**: `backend/src/core/logging_config.py`

**Diseño**:
```python
import logging
import json
import sys
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(getattr(logging, level.upper(), logging.INFO))
```

**Archivos a modificar**:
- `backend/src/api/main.py`: Llamar `configure_logging()` al inicio
- `backend/src/worker.py`: Llamar `configure_logging()` al inicio
- Eliminar todos los `logging.basicConfig()` individuales

**Criterio de aceptación**:
- Todos los logs del backend salen en formato JSON a stdout
- Cada log tiene: timestamp, level, logger, message, module, line
- Los logs de error incluyen traceback completo

---

## 7. Fase 3 — Madurez Operativa

> **Objetivo**: Preparar el proyecto para escala y mantenimiento a largo plazo.

### 7.1 Migraciones de DB con Alembic

**Dependencia nueva**: `alembic` en `requirements.txt`  
**Archivo nuevo**: `backend/alembic.ini`, `backend/alembic/` directory

**Pasos**:
1. `alembic init alembic` en `backend/`
2. Configurar `env.py` para leer `DATABASE_URL` de env
3. Crear migración inicial que refleje el schema actual de `create_tables()`
4. Reemplazar `create_tables()` en `database_service.py` por `alembic upgrade head`

**Criterio de aceptación**:
- `alembic current` muestra la versión actual
- `alembic upgrade head` aplica migraciones pendientes
- `alembic downgrade -1` revierte la última migración

### 7.2 Multi-Stage Dockerfile

**Archivo**: `Dockerfile.portable`  
**Diseño**:
```dockerfile
# Stage 1: Frontend build
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend + frontend dist
FROM python:3.11-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY backend/ ./backend/
RUN pip install --no-cache-dir -r backend/requirements-worker.txt
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY --from=frontend-build /app/frontend/package.json ./frontend/
```

**Criterio de aceptación**:
- Imagen resultante ≤500MB (vs actual ~800MB+)
- `docker compose up -d` funciona sin cambios adicionales
- Build time aceptable (<5 minutos en CI)

### 7.3 Monitoring Básico (Sentry)

**Dependencia nueva**: `sentry-sdk[fastapi]` en `requirements.txt`  
**Variable de entorno nueva**: `SENTRY_DSN`

**Diseño**:
```python
import sentry_sdk

if dsn := os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
```

**Criterio de aceptación**:
- Errores no capturados aparecen en Sentry dashboard
- No se envían datos en desarrollo local (sin `SENTRY_DSN`)

### 7.4 Frontend: Accesibilidad WCAG 2.1 AA

**Archivos a modificar**: Todos los componentes en `presentation/components/`

**Cambios clave por componente**:

| Componente | Cambio a11y |
|---|---|
| `MatchCard` | `aria-label="Partido {home} vs {away}"`, role en badges |
| `PredictionGrid` | `aria-live="polite"` en lista de predicciones |
| `LeagueSelector` | `aria-label` en selects |
| `LiveMatches` | `aria-live="assertive"` para actualizaciones en vivo |
| `ParleySlip` | `aria-label` en botones, `role="list"` en picks |
| `ErrorBoundary` | `role="alert"` en mensaje de error |
| `OfflineIndicator` | `role="status"`, `aria-live="polite"` |
| `SystemInitializationScreen` | `role="progressbar"`, `aria-busy="true"` |

**Dependencia nueva** (dev): `eslint-plugin-jsx-a11y`  
**Agregar al ESLint config**: Plugin `jsx-a11y` con `recommended` rules.

**Criterio de aceptación**:
- `eslint-plugin-jsx-a11y` con 0 errores
- Lighthouse a11y score ≥90
- Navegación completa con teclado funcional

### 7.5 Desacoplar Domain Services de Infrastructure

**Archivos a auditar**: `backend/src/domain/services/*.py`

**Patrón actual** (violación):
```python
# domain/services/match_aggregator_service.py
from src.infrastructure.data_sources.espn import ESPNSource  # ❌ Import directo de infra
```

**Patrón correcto**:
```python
# domain/interfaces/data_source.py
from abc import ABC, abstractmethod

class MatchDataSource(ABC):
    @abstractmethod
    async def get_upcoming_matches(self, league_id: str) -> list[Match]: ...

# domain/services/match_aggregator_service.py
class MatchAggregatorService:
    def __init__(self, sources: list[MatchDataSource]): ...  # ✅ DIP via interfaces
```

**Archivos afectados estimados**: `match_aggregator_service.py`, `cache_warmup_service.py`, `audit_service.py`

**Criterio de aceptación**:
- `grep -rn "from src.infrastructure" backend/src/domain/` → 0 resultados
- Todos los domain services reciben dependencias via constructor (DIP)

### 7.6 Limpieza de Deuda Técnica

| Tarea | Archivo |
|---|---|
| Eliminar `.bak` file | `backend/src/application/services/ml_training_orchestrator.py.bak` |
| Eliminar endpoints stub vacíos | `backend/src/api/main.py` (endpoints que devuelven `[]`) |
| Documentar schema MongoDB | `backend/docs/mongodb-schema.md` |
| Crear `frontend/.env.example` | Documentar `VITE_API_URL`, `VITE_API_PROXY_TARGET` |
| CORS: eliminar fallback a `*` | `backend/src/api/main.py` — `CORS_ORIGINS` obligatorio, no fallback |

---

## 8. Dependencias entre Fases

```
Fase 1 (Fundamentos)
├── 5.1 CI/CD ← Ninguna (desbloquea todo)
├── 5.2 Seguridad API ← Ninguna
├── 5.3 Error Handling ← Ninguna
├── 5.4 Tests Backend ← 5.3 (necesita error handling limpio)
└── 5.5 Tests Frontend ← 5.1 (CI para validar)

Fase 2 (Calidad)
├── 6.1 Prettier ← 5.1 (CI para validate)
├── 6.2 Pre-commit ← 6.1 (Prettier configurado)
├── 6.3 Eliminar `any` ← Ninguna
├── 6.4 Eliminar API legacy ← 6.3 (tipos limpios)
├── 6.5 Coverage ampliado ← 5.4, 5.5 (base de tests)
├── 6.6 Model versioning ← Ninguna
└── 6.7 Structured logging ← 5.3 (error handling limpio)

Fase 3 (Madurez)
├── 7.1 Alembic ← Ninguna
├── 7.2 Multi-stage Docker ← Ninguna
├── 7.3 Sentry ← 6.7 (logging estructurado)
├── 7.4 Accesibilidad ← Ninguna
├── 7.5 Desacoplar domain ← 5.4 (tests protegen refactor)
└── 7.6 Cleanup ← Ninguna
```

---

## 9. Criterios de Éxito Globales

| Métrica | Actual | Post-Fase 1 | Post-Fase 2 | Post-Fase 3 |
|---|---|---|---|---|
| Tests backend | 3 | >30 | >60 | >80 |
| Tests frontend | 4 | >20 | >35 | >50 |
| Coverage backend | ~1% | ≥30% | ≥60% | ≥70% |
| Coverage frontend | ~5% | ≥15% | ≥40% | ≥50% |
| CI pipelines | 0 | 1 (PR checks) | 2 (+deploy) | 3 (+monitoring) |
| API auth | Ninguna | API key admin | API key admin | API key + Sentry |
| Bare `except` | 3 | 0 | 0 | 0 |
| `except: pass` | 7+ | 0 | 0 | 0 |
| `any` en TS | 8 | 8 | 0 | 0 |
| ML model versioning | No | No | Registry JSON | Registry + alertas |
| a11y score | ~40 | ~40 | ~40 | ≥90 |
| Imagen Docker | ~800MB | ~800MB | ~800MB | ≤500MB |

---

## 10. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| `.github/` contiene datos sensibles | Baja | Alto | Auditar contenido antes de commit |
| Tests rompen CI por dependencias faltantes | Media | Medio | Fijar en `requirements.txt` exact versions |
| Rate limiting rompe polling del frontend | Media | Medio | Configurar límites generosos (60/min), exemption para health |
| Sacar `.joblib` de Git rompe pipeline | Baja | Alto | Asegurar que `run_dev_pipeline.sh` genera modelos antes de servir |
| Refactor de domain services rompe lógica | Media | Alto | Tests de Fase 1 deben cubrir antes del refactor de Fase 3 |
| Alembic y MongoDB coexisten confusamente | Baja | Bajo | Documentar claramente: Alembic = PostgreSQL prod, MongoDB = Docker dev |

---

## 11. Glosario

| Término | Definición |
|---|---|
| **RULES.md** | Fuente de verdad del proyecto con reglas de negocio, calidad y operación |
| **DIP** | Dependency Inversion Principle — depender de abstracciones, no de implementaciones |
| **Bare except** | `except:` sin especificar tipo de excepción — mala práctica |
| **EV+** | Expected Value positivo — `probabilidad × cuota > 1.0` |
| **Model Registry** | Archivo que rastrea versiones de modelos ML con métricas asociadas |
| **WCAG 2.1 AA** | Estándar de accesibilidad web nivel AA |
| **Structured Logging** | Logs en formato parseable (JSON) vs texto plano |

---

## 12. Aprobación

- [ ] Revisado por propietario del repositorio
- [ ] Fases priorizadas correctamente
- [ ] Criterios de aceptación claros para cada tarea
- [ ] Riesgos aceptables

---

*Siguiente paso*: Generar `plan.md` con cronograma y `tasks.md` con tareas atómicas accionables.
