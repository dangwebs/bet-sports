# Tasks: Viability Uplift — BJJ-BetSports

**Plan de referencia**: `specs/viability-uplift/plan.md`  
**Spec de referencia**: `specs/viability-uplift/spec.md`  

---

## Convenciones

- **ID**: `F{fase}-{bloque}{secuencial}` (ej. `F1-A1`, `F2-B3`)
- **Tamaño**: S (< 30 min), M (30-90 min), L (> 90 min)
- **Agente**: Backend, Frontend, Architecture, Orchestrator
- **Estado**: `[ ]` pendiente, `[x]` completado
- **Dependencia**: ID de la tarea que debe estar completada antes

---

## Fase 1 — Fundamentos de Viabilidad

### Bloque 1.A — Desbloquear CI/CD

#### F1-A1: Auditar contenido de `.github/` por secrets

- [ ] **Estado**: Pendiente
- **Agente**: Architecture
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivos a leer**:
  - `.github/agents/*.md`
  - `.github/copilot-instructions.md`
  - `.github/skills/**/*.md`
  - `.github/prompts/**` (si existe)
- **Acción**: Verificar que ningún archivo contiene API keys, tokens, passwords, URLs privadas o datos personales.
- **Criterio de aceptación**:
  - Revisión documentada (lista de archivos revisados + resultado OK/NO OK)
  - Si se encuentra algún secret → crear tarea adicional para sanitizar antes de continuar
- **Commit**: N/A (solo lectura)

---

#### F1-A2: Remover `.github/` del `.gitignore`

- [ ] **Estado**: Pendiente
- **Agente**: Architecture
- **Tamaño**: S
- **Dependencias**: F1-A1
- **Archivo a modificar**: `.gitignore` (raíz)
- **Cambio exacto**:
  ```diff
  - # Agent files
  - .github/
  - .claude/
  + # Agentes Claude (solo local, no versionar)
  + .claude/
  ```
- **Criterio de aceptación**:
  - `git status` muestra archivos de `.github/` como untracked/nuevos
  - `.claude/` sigue ignorada
- **Validación**: `git diff .gitignore` muestra exactamente el cambio esperado
- **Commit**: `ci: remover .github/ del gitignore para habilitar CI/CD`

---

#### F1-A3: Crear workflow CI para Pull Requests

- [ ] **Estado**: Pendiente
- **Agente**: Architecture
- **Tamaño**: M
- **Dependencias**: F1-A2
- **Archivo nuevo**: `.github/workflows/ci.yml`
- **Contenido**: Ver plan.md §Bloque 1.A, Paso 3 (YAML completo)
- **Jobs del workflow**:
  1. `backend-lint-and-types`: Python 3.11, `pip install -r requirements.txt`, `black --check src/ tests/`, `mypy src/`
  2. `backend-tests`: Python 3.11, `pytest -v --tb=short`
  3. `frontend-lint`: Node 20, `npm ci`, `npm run lint`, `npm run build`
  4. `frontend-tests`: Node 20, `npm ci`, `npx vitest run`
- **Criterio de aceptación**:
  - YAML válido (sin errores de sintaxis)
  - Trigger: `pull_request` a `[main, develop, "feature/**"]`
  - `concurrency` configurada para cancelar runs anteriores
  - Cache configurado para pip y npm
  - Timeout de 10 min en cada job
- **Validación**:
  - Push a rama test → abrir PR → 4 jobs se ejecutan
  - Los jobs de lint pueden fallar (se arreglarán en fases posteriores), pero deben EJECUTARSE
- **Commit**: `ci: crear workflow CI con lint, types y tests para PRs`

---

### Bloque 1.B — Seguridad API

#### F1-B1: Instalar `slowapi`

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivo a modificar**: `backend/requirements.txt`
- **Cambio**: Agregar `slowapi==0.1.9` al final del archivo
- **Criterio de aceptación**: `pip install -r requirements.txt` incluye slowapi
- **Commit**: Incluir en el commit de F1-B2

---

#### F1-B2: Crear módulo de seguridad API

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-B1
- **Archivo nuevo**: `backend/src/api/security.py`
- **Contenido**: Ver plan.md §Bloque 1.B, Paso 2
- **Funciones a implementar**:
  - `require_admin_key(api_key: Optional[str]) -> str`: Dependency de FastAPI que verifica `X-API-Key`
  - Lee `ADMIN_API_KEY` de variables de entorno
  - Devuelve 503 si key no configurada en servidor
  - Devuelve 403 si key incorrecta
- **Criterio de aceptación**:
  - `from src.api.security import require_admin_key` importa sin error
  - La función usa `os.getenv`, NO hardcodea secrets
  - Tiene type hints completos
  - Sin `any` o tipos ambiguos
- **Commit**: Incluir en el commit de F1-B4

---

#### F1-B3: Integrar seguridad y rate limiting en `main.py`

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-B2
- **Archivo a modificar**: `backend/src/api/main.py`
- **Cambios**:
  1. **Imports nuevos** (al inicio del archivo):
     ```python
     from slowapi import Limiter
     from slowapi.util import get_remote_address
     from slowapi.middleware import SlowAPIMiddleware
     from src.api.security import require_admin_key
     ```
  2. **Configurar Limiter** (después de crear `app`):
     ```python
     limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
     app.state.limiter = limiter
     app.add_middleware(SlowAPIMiddleware)
     ```
  3. **Proteger endpoints admin**: TODOS los endpoints `POST`/`PUT`/`DELETE` deben recibir `_: str = Depends(require_admin_key)` como parámetro
  4. **Rate limit en admin**: `@limiter.limit("5/minute")` para endpoints de entrenamiento
  5. **Exempt health check**: `@limiter.exempt` para `/health`
- **Criterio de aceptación**:
  - `POST /api/v1/train/run-now` sin header `X-API-Key` → 403
  - `POST /api/v1/train/run-now` con key correcta → 200/202
  - `GET /health` funciona sin auth ni rate limit
  - `GET /api/v1/leagues` y `GET /api/v1/predictions/*` funcionan sin auth (son públicos)
  - Rate limit de 60/min aplica globalmente
- **Commit**: Incluir en el commit de F1-B4

---

#### F1-B4: Actualizar env y Docker Compose

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: F1-B3
- **Archivos a modificar**:
  1. `backend/.env.example` — agregar: `ADMIN_API_KEY=cambiar-por-un-valor-aleatorio-seguro`
  2. `docker-compose.dev.yml` — en servicio `backend-api`, en `environment`, agregar:
     ```yaml
     ADMIN_API_KEY: ${ADMIN_API_KEY:-dev-admin-key-local}
     ```
- **Criterio de aceptación**:
  - `.env.example` documenta la variable
  - Docker Compose inyecta la variable con valor default para dev
  - NO se commitean secrets reales
- **Commit**: `fix(backend): agregar API key para endpoints admin y rate limiting con slowapi`

---

#### F1-B5: Tests de seguridad API

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-B4
- **Archivo nuevo**: `backend/tests/unit/test_api_security.py`
- **Tests a implementar**:

  | Test | Descripción | Assert |
  |---|---|---|
  | `test_train_endpoint_requires_api_key` | POST sin header → 403 | `status_code == 403` |
  | `test_train_endpoint_accepts_valid_key` | POST con key correcta → 200/202 | `status_code in (200, 202)` |
  | `test_train_endpoint_rejects_wrong_key` | POST con key incorrecta → 403 | `status_code == 403` |
  | `test_public_endpoints_no_auth_needed` | GET /health y GET /api/v1/leagues → 200 | `status_code == 200` |
  | `test_missing_admin_key_server_side` | Sin `ADMIN_API_KEY` env var → 503 | `status_code == 503` |

- **Setup**:
  ```python
  @pytest.fixture
  def client():
      with patch.dict("os.environ", {"ADMIN_API_KEY": "test-secret-key"}):
          from src.api.main import app
          yield TestClient(app)
  ```
- **Criterio de aceptación**: 5 tests, todos pasando
- **Validación**: `cd backend && ADMIN_API_KEY=test pytest tests/unit/test_api_security.py -v`
- **Commit**: Incluir en el commit de F1-B4

---

### Bloque 1.C — Error Handling Global

#### F1-C1: Crear exception handler global en `main.py`

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivo a modificar**: `backend/src/api/main.py`
- **Cambio**: Agregar después de configurar CORS middleware:
  ```python
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
- **Imports requeridos**: `from fastapi import Request`, `from fastapi.responses import JSONResponse`
- **Criterio de aceptación**:
  - Cualquier excepción no manejada → 500 con JSON `{"detail": "Error interno del servidor"}`
  - Stack trace completo en logs (no expuesto al cliente)
  - No se expone detalle técnico al cliente
- **Commit**: Incluir en el commit de F1-C3

---

#### F1-C2: Corregir 3 bare `except:` por excepciones específicas

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivos a modificar**:

  | Archivo | Línea | Cambio |
  |---|---|---|
  | `backend/src/infrastructure/data_sources/espn.py` | ~148 | `except:` → `except (ValueError, TypeError):` |
  | `backend/src/infrastructure/data_sources/espn.py` | ~426 | `except:` → `except (ValueError, TypeError):` |
  | `backend/src/domain/services/ml_feature_extractor.py` | ~144 | `except:` → `except statistics.StatisticsError:` |

- **Pre-requisito**: Leer el contexto alrededor de cada línea para confirmar que la excepción específica es la correcta. Si el bloque `try` hace parsing de datos, usar `(ValueError, TypeError, KeyError)`. Si hace operaciones estadísticas, usar `statistics.StatisticsError`.
- **Criterio de aceptación**:
  - `grep -rn "except:" backend/src/ | grep -v "except " | grep -v "#"` devuelve 0 resultados
  - Cada `except` captura la excepción más específica posible
  - El comportamiento no cambia (mismo flujo de control)
- **Commit**: Incluir en el commit de F1-C3

---

#### F1-C3: Agregar logging a `except Exception: pass` silenciosos

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: Ninguna
- **Archivos a modificar** (10 correcciones):

  | # | Archivo | Línea | Patrón actual | Patrón nuevo |
  |---|---|---|---|---|
  | 1 | `application/use_cases/use_cases.py` | ~L911 | `except Exception:\n    pass` | `except Exception as exc:\n    logger.debug("Ignorando error no crítico en use_cases: %s", exc)` |
  | 2 | `application/use_cases/use_cases.py` | ~L1188 | Idem | Idem |
  | 3 | `application/use_cases/use_cases.py` | ~L1198 | Idem | Idem |
  | 4 | `application/use_cases/suggested_picks_use_case.py` | ~L447 | `except Exception:\n    return []` | `except Exception as exc:\n    logger.debug("Fallback a lista vacía: %s", exc)\n    return []` |
  | 5 | `application/use_cases/suggested_picks_use_case.py` | ~L462 | Idem | Idem |
  | 6 | `application/use_cases/live_predictions_use_case.py` | ~L421 | `except Exception:` + lógica | Agregar `logger.debug("Error en live predictions: %s", exc)` al inicio del bloque except |
  | 7 | `application/use_cases/live_predictions_use_case.py` | ~L436 | Idem | Idem |
  | 8 | `application/use_cases/live_predictions_use_case.py` | ~L469 | Idem | Idem |
  | 9 | `application/use_cases/live_predictions_use_case.py` | ~L513 | Idem | Idem |
  | 10 | `application/use_cases/get_parleys_use_case.py` | ~L45 | Idem | Idem |

- **Regla**: cada `except` DEBE:
  - Capturar la excepción: `as exc`
  - Loguear al menos a nivel `debug`
  - Mantener el mismo flujo de control (si antes hacía `pass`, sigue sin propagarse; si retornaba `[]`, sigue retornando `[]`)

- **Pre-requisito**: Verificar que el módulo tiene logger configurado. Si no, agregar al inicio:
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```

- **Criterio de aceptación**:
  - `grep -Pzn "except.*:\s*\n\s*pass\s*$" backend/src/` devuelve 0 resultados
  - Los tests existentes siguen pasando sin cambio
  - Cada except tiene logging

- **Validación**:
  ```bash
  cd backend
  grep -rn "except:" src/ | grep -v "except " | grep -v "#" # → 0 resultados (bare)
  grep -Pc "except.*:\s*$" src/**/*.py | grep -v ":0$"       # verificar manualmente
  pytest -v --tb=short                                         # todos pasan
  ```

- **Commit**: `fix(backend): middleware global de errores y eliminar bare excepts/pass silenciosos`

---

### Bloque 1.D — Tests Unitarios Backend

#### F1-D1: Crear fixtures compartidas en conftest.py

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-C3 (error handling limpio)
- **Archivo nuevo**: `backend/tests/conftest.py`
- **Pre-requisito**: Leer PRIMERO estos archivos para entender las firmas exactas:
  - `backend/src/domain/entities/entities.py`
  - `backend/src/domain/entities/suggested_pick.py`
  - `backend/src/domain/value_objects/value_objects.py`
- **Fixtures a crear**:
  - `sample_team_home` → `Team` instance
  - `sample_team_away` → `Team` instance
  - `sample_league` → `League` instance
  - `sample_match` → `Match` instance (usa team + league fixtures)
  - `sample_prediction` → `Prediction` instance
  - `sample_home_stats` → `TeamStatistics` instance
  - `sample_away_stats` → `TeamStatistics` instance
- **Criterio de aceptación**:
  - Todas las fixtures se importan correctamente en tests
  - Usan las firmas REALES de los dataclasses (no inventar campos)
  - Datos de ejemplo son realistas (nombres de equipos reales, probabilidades que suman ~1.0)
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D2: Tests de Value Objects

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-D1
- **Archivo nuevo**: `backend/tests/unit/test_value_objects.py`
- **Pre-requisito**: Leer `backend/src/domain/value_objects/value_objects.py` para conocer la implementación real
- **Tests**:

  | Clase | Test | Assert |
  |---|---|---|
  | `Probability` | `test_valid_probability` | `Probability(0.5).value == 0.5` |
  | `Probability` | `test_probability_zero` | `Probability(0.0).value == 0.0` |
  | `Probability` | `test_probability_one` | `Probability(1.0).value == 1.0` |
  | `Probability` | `test_probability_negative_raises` | `pytest.raises(ValueError)` |
  | `Probability` | `test_probability_over_one_raises` | `pytest.raises(ValueError)` |
  | `Probability` | `test_probability_frozen` | `pytest.raises(AttributeError)` al mutarlo |
  | `Odds` | `test_valid_odds` | `Odds(2.5).value == 2.5` |
  | `Odds` | `test_odds_minimum` | `Odds(1.01).value == 1.01` |
  | `Odds` | `test_odds_below_one_raises` | `pytest.raises(ValueError)` |
  | `Odds` | `test_odds_frozen` | `pytest.raises(AttributeError)` al mutarlo |
  | `Score` | `test_valid_score` | `Score(2, 1).home == 2` |
  | `Score` | `test_score_zero` | `Score(0, 0)` crea OK |
  | `Score` | `test_negative_score_raises` | `pytest.raises(ValueError)` |
  | `Score` | `test_score_frozen` | `pytest.raises(AttributeError)` al mutarlo |

- **Nota**: Si los value objects no tienen validación en `__post_init__`, los tests negativos se omiten y se documenta que la validación está pendiente.
- **Criterio de aceptación**: ≥10 tests pasando
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D3: Tests de Entities

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-D1
- **Archivo nuevo**: `backend/tests/unit/test_entities.py`
- **Pre-requisito**: Leer `backend/src/domain/entities/entities.py` y `backend/src/domain/entities/suggested_pick.py`
- **Tests**:

  | Test | Descripción | Assert |
  |---|---|---|
  | `test_match_creation` | Crear `Match` con fields mínimos | Todos los atributos accesibles |
  | `test_prediction_fields` | Crear `Prediction` | Campos de probabilidad sumados ≈ 1.0 |
  | `test_suggested_pick_market_types` | Verificar `MarketType` enum | Contiene `WINNER`, `GOALS`, `CORNERS`, `CARDS` |
  | `test_suggested_pick_creation` | Crear `SuggestedPick` válido | `market_type` y `confidence_level` presentes |
  | `test_match_suggested_picks_creation` | Crear `MatchSuggestedPicks` con picks | `len(picks) > 0` |
  | `test_betting_feedback_creation` | Crear `BettingFeedback` | Campos accesibles |
  | `test_parley_creation` | Crear `Parley` con picks | `len(picks) > 0` |

- **Criterio de aceptación**: ≥7 tests pasando
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D4: Tests de RiskManager

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: L
- **Dependencias**: F1-D1
- **Archivo nuevo**: `backend/tests/unit/test_risk_manager.py`
- **Pre-requisito**: Leer `backend/src/domain/services/risk_manager.py` (o la clase de riesgo que exista). Buscar con:
  ```bash
  grep -rn "class.*Risk\|class.*Bankroll\|class.*Stake" backend/src/
  ```
- **Tests críticos** (RULES.md §11, §13):

  | Test | Descripción | Assert |
  |---|---|---|
  | `test_max_stake_hard_cap_5_percent` | Bankroll 1000, stake calculado ≤ 50 | `stake <= bankroll * 0.05` |
  | `test_circuit_breaker_consecutive_losses` | 5 pérdidas consecutivas | Breaker se activa, siguiente stake = 0 o mínimo |
  | `test_ev_positive_accepted` | prob=0.6, odds=2.0, EV=1.2 | Pick aceptado (EV > 1.0) |
  | `test_ev_negative_rejected` | prob=0.3, odds=1.5, EV=0.45 | Pick rechazado (EV < 1.0) |
  | `test_anomalous_odds_rejected` | odds=0.5 (< 1.01) | Pick rechazado |
  | `test_anomalous_high_odds_rejected` | odds=1500 (> 1000) | Pick rechazado |
  | `test_kelly_criterion_calculation` | prob=0.6, odds=2.0 | Kelly = (0.6×2 - 1)/(2-1) = 0.2 (±delta) |

- **Criterio de aceptación**: ≥7 tests pasando, los tests de RULES.md §11 y §13 NUNCA deben fallar
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D5: Tests de PicksService / SuggestedPicks

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: L
- **Dependencias**: F1-D1
- **Archivo nuevo**: `backend/tests/unit/test_picks_service.py`
- **Pre-requisito**: Leer:
  - `backend/src/application/use_cases/suggested_picks_use_case.py`
  - `backend/src/domain/services/` (buscar `picks`, `suggested`)
- **Tests** (RULES.md §16 — esquinas/tarjetas siempre presentes):

  | Test | Descripción | Assert |
  |---|---|---|
  | `test_generate_picks_four_markets` | Match+stats → picks | Picks existen para WINNER, GOALS, CORNERS, CARDS |
  | `test_no_empty_corners_picks` | Match con stats válidos | `len(corners_picks) > 0` |
  | `test_no_empty_cards_picks` | Match con stats válidos | `len(cards_picks) > 0` |
  | `test_pick_has_required_fields` | Cada pick resultado | `market_type`, `market_label`, `probability`, `confidence_level` presentes |
  | `test_pick_probability_bounds` | Cada pick resultado | `0.0 <= probability <= 1.0` |
  | `test_pick_confidence_valid_level` | Cada pick | `confidence_level in ['low', 'medium', 'high']` (o enum equivalente) |

- **Criterio de aceptación**: ≥6 tests pasando. Tests de §16 marcados como `@pytest.mark.critical`
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D6: Tests de PredictionService / ConfidenceCalculator

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-D1
- **Archivos nuevos**:
  - `backend/tests/unit/test_prediction_service.py`
  - `backend/tests/unit/test_confidence_calculator.py`
- **Pre-requisito**: Leer los archivos de servicio en `backend/src/domain/services/` y `backend/src/application/services/`
- **Tests PredictionService**:

  | Test | Assert |
  |---|---|
  | `test_prediction_valid_probabilities` | `abs(home_win + draw + away_win - 1.0) < 0.01` |
  | `test_prediction_goals_non_negative` | `home_goals >= 0 and away_goals >= 0` |
  | `test_insufficient_data_raises` | `InsufficientDataException` cuando < 5 matches |
  | `test_zero_stats_uses_league_average` | Stats vacíos → usa promedios liga (RULES.md §2B) |

- **Tests ConfidenceCalculator**:

  | Test | Assert |
  |---|---|
  | `test_high_confidence_many_sources` | 3+ fuentes → confidence > 0.7 |
  | `test_low_confidence_sparse_data` | 1 fuente → confidence < 0.5 |
  | `test_confidence_between_0_and_1` | `0.0 <= confidence <= 1.0` |

- **Criterio de aceptación**: ≥7 tests pasando
- **Commit**: Incluir en commit de F1-D7

---

#### F1-D7: Configurar coverage y validar

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: F1-D2, F1-D3, F1-D4, F1-D5, F1-D6
- **Archivo a modificar**: `backend/pyproject.toml`
- **Cambio**:
  ```toml
  [tool.pytest.ini_options]
  addopts = "-v --tb=short --cov=src --cov-report=term-missing --cov-fail-under=30"
  ```
- **Dependencia pip**: Agregar `pytest-cov` a `backend/requirements.txt` si no existe
- **Validación**:
  ```bash
  cd backend && pytest -v
  # Esperado: >30 tests, todos pasando, coverage ≥30%
  ```
- **Criterio de aceptación**:
  - `pytest` ejecuta exitosamente
  - Coverage report se muestra en terminal
  - Coverage total ≥ 30%
  - 0 tests fallando
- **Commit**: `test(backend): tests unitarios para dominio, riesgo y scoring`

---

### Bloque 1.E — Tests Frontend

#### F1-E1: Crear test-utils con ThemeProvider

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivo nuevo**: `frontend/src/test-utils.tsx`
- **Pre-requisito**: Leer `frontend/src/theme/` para encontrar el export del tema
- **Contenido**:
  ```tsx
  import { ReactNode } from "react";
  import { ThemeProvider } from "@mui/material/styles";
  import { render, RenderOptions } from "@testing-library/react";
  import { theme } from "./theme";  // Ajustar al path real

  function Wrapper({ children }: { children: ReactNode }) {
    return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
  }

  export function renderWithTheme(ui: React.ReactElement, options?: RenderOptions) {
    return render(ui, { wrapper: Wrapper, ...options });
  }
  ```
- **Criterio de aceptación**: `renderWithTheme` se importa sin error
- **Commit**: Incluir en commit de F1-E5

---

#### F1-E2: Tests de Zustand stores

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: Ninguna
- **Pre-requisito**: Leer los stores en `frontend/src/application/stores/`
- **Archivos nuevos**:
  - `frontend/src/application/stores/__tests__/usePredictionStore.test.ts`
  - `frontend/src/application/stores/__tests__/useParleyStore.test.ts`
  - `frontend/src/application/stores/__tests__/useCacheStore.test.ts`
- **Tests usePredictionStore**:

  | Test | Assert |
  |---|---|
  | `test_initial_state` | predictions definido (vacío o iniciado) |
  | `test_set_predictions` | `setPredictions([...])` → state actualizado |
  | `test_loading_state` | Existe flag `loading` y se puede cambiar |

- **Tests useParleyStore**:

  | Test | Assert |
  |---|---|
  | `test_add_pick` | 1 pick agregado → `picks.length === 1` |
  | `test_remove_pick` | Agregar + remover → `picks.length === 0` |
  | `test_max_10_picks` | 11 intentos → `picks.length <= 10` |
  | `test_clear_parley` | Clear → estado vacío |

- **Tests useCacheStore**:

  | Test | Assert |
  |---|---|
  | `test_set_cache` | Setear valor → `getCache()` lo devuelve |
  | `test_cache_expiry` | Cache expirado → `getCache()` devuelve null |

- **Criterio de aceptación**: ≥8 tests pasando. Tests NO requieren renderizado DOM.
- **Commit**: Incluir en commit de F1-E5

---

#### F1-E3: Tests de hooks

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: F1-E1
- **Pre-requisito**: Leer hooks en `frontend/src/hooks/` para conocer la interfaz
- **Archivos nuevos**:
  - `frontend/src/hooks/__tests__/usePredictions.test.ts`
  - `frontend/src/hooks/__tests__/useLeagues.test.ts`
  - `frontend/src/hooks/__tests__/useSmartPolling.test.ts`
- **Patrón**: Usar `renderHook` de `@testing-library/react` + mocks de la API
- **Tests resumidos**:

  | Hook | Test | Assert |
  |---|---|---|
  | `usePredictions` | `test_initial_loading` | `loading === true` inicialmente |
  | `usePredictions` | `test_data_received` | Mock API → predictions no vacías |
  | `usePredictions` | `test_api_error` | Mock error → error state set |
  | `useLeagues` | `test_initial_loading` | `loading === true` |
  | `useLeagues` | `test_leagues_loaded` | Mock → leagues array |
  | `useSmartPolling` | `test_polls_on_interval` | Verifica setTimeout/setInterval |

- **Criterio de aceptación**: ≥6 tests pasando
- **Commit**: Incluir en commit de F1-E5

---

#### F1-E4: Tests de componentes principales

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: L
- **Dependencias**: F1-E1, F1-E2
- **Pre-requisito**: Leer los componentes reales para conocer sus props
- **Archivos nuevos**:
  - `frontend/src/presentation/components/MatchCard/__tests__/MatchCard.test.tsx`
  - `frontend/src/presentation/components/PredictionGrid/__tests__/PredictionGrid.test.tsx`
  - `frontend/src/presentation/components/Parley/__tests__/ParleySlip.test.tsx`
  - `frontend/src/presentation/components/BotDashboard/__tests__/BotDashboard.test.tsx`

- **Tests MatchCard**:

  | Test | Assert |
  |---|---|
  | `test_renders_team_names` | Texto de equipos visible |
  | `test_renders_prediction` | Datos de predicción visibles |
  | `test_renders_without_crash` | No throws |

- **Tests PredictionGrid**:

  | Test | Assert |
  |---|---|
  | `test_renders_match_cards` | N matches → N cards renderizados |
  | `test_renders_empty_state` | 0 matches → mensaje vacío |
  | `test_renders_loading_state` | `loading=true` → skeleton/spinner |

- **Tests ParleySlip**:

  | Test | Assert |
  |---|---|
  | `test_renders_picks` | Picks visibles |
  | `test_clear_button_works` | Click clear → picks vacíos |

- **Tests BotDashboard**:

  | Test | Assert |
  |---|---|
  | `test_renders_stats_summary` | Stats visibles |
  | `test_loading_state` | `loading=true` → skeleton |

- **Usar**: `renderWithTheme` de F1-E1
- **Criterio de aceptación**: ≥10 tests pasando
- **Commit**: Incluir en commit de F1-E5

---

#### F1-E5: Validar suite completa frontend

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: F1-E2, F1-E3, F1-E4
- **Validación**:
  ```bash
  cd frontend
  npx vitest run
  # Esperado: >20 tests, todos pasando
  npm run lint
  # Esperado: 0 errores
  npm run build
  # Esperado: build exitoso
  ```
- **Criterio de aceptación**: ≥20 tests pasando, lint limpio, build exitoso
- **Commit**: `test(frontend): tests de componentes, hooks y stores principales`

---

## Fase 2 — Calidad Profesional

### Bloque 2.A — Prettier + Pre-commit

#### F2-A1: Instalar dependencias de desarrollo

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: Fase 1 completada
- **Comando**:
  ```bash
  cd frontend && npm install -D prettier husky lint-staged
  ```
- **Criterio de aceptación**: `package.json` devDependencies incluye prettier, husky, lint-staged
- **Commit**: Incluir en F2-A4

---

#### F2-A2: Crear `.prettierrc`

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: F2-A1
- **Archivo nuevo**: `frontend/.prettierrc`
- **Contenido** (ver spec §6.1):
  ```json
  {
    "semi": true,
    "singleQuote": false,
    "tabWidth": 2,
    "trailingComma": "all",
    "printWidth": 100,
    "bracketSpacing": true,
    "arrowParens": "always",
    "endOfLine": "lf"
  }
  ```
- **Criterio de aceptación**: `npx prettier --check .` funciona sin error de config
- **Commit**: Incluir en F2-A4

---

#### F2-A3: Agregar scripts y configurar lint-staged

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: F2-A2
- **Archivo a modificar**: `frontend/package.json`
- **Cambios**:
  1. En `"scripts"`, agregar:
     ```json
     "format": "prettier --write \"src/**/*.{ts,tsx,css,json}\"",
     "format:check": "prettier --check \"src/**/*.{ts,tsx,css,json}\""
     ```
  2. Agregar sección `"lint-staged"`:
     ```json
     "lint-staged": {
       "src/**/*.{ts,tsx}": ["eslint --fix", "prettier --write"],
       "src/**/*.{css,json}": ["prettier --write"]
     }
     ```
- **Criterio de aceptación**: `npm run format` ejecuta sin error, `npm run format:check` detecta archivos sin formatear
- **Commit**: Incluir en F2-A4

---

#### F2-A4: Inicializar husky, formatear codebase, actualizar CI

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: F2-A3
- **Acciones**:
  1. `cd frontend && npx husky init`
  2. `echo "cd frontend && npx lint-staged" > .husky/pre-commit`
  3. `npm run format` (formatear todo el codebase existente)
  4. Agregar `npm run format:check` al job `frontend-lint` del workflow CI:
     ```yaml
     - run: npm run format:check
     ```
- **Criterio de aceptación**:
  - `git commit` de un `.tsx` ejecuta lint-staged automáticamente
  - `npm run format:check` pasa (todo formateado)
  - CI incluye check de formato
- **Commit**: `chore(frontend): configurar Prettier, husky y lint-staged`

---

### Bloque 2.B — Eliminar `any` en Frontend

#### F2-B1: Definir tipos faltantes

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: Ninguna
- **Pre-requisito**: Leer estos archivos para entender la forma de los datos:
  - `frontend/src/hooks/useLiveMatches.ts` (L307 para ver la forma de `match: any`)
  - `frontend/src/application/stores/useCacheStore.ts` (para ver `predictions: any[]`)
  - `frontend/src/utils/matchMatching.ts` (para ver `prediction?: any`)
  - `frontend/src/utils/marketUtils.ts` (para ver `picks: any[]`)
  - `frontend/src/infrastructure/LocalStorageObserver.ts` (para ver callbacks)
- **Archivo a modificar**: `frontend/src/types/index.ts` (o archivo de tipos apropiado)
- **Interfaces nuevas a crear**:
  - `LiveMatchRaw`: Forma del dato crudo de live matches
  - Cualquier otra interfaz necesaria que no exista
- **Criterio de aceptación**: Todos los tipos existen y son importables
- **Commit**: Incluir en F2-B2

---

#### F2-B2: Reemplazar 8 usos de `any`

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: F2-B1
- **Archivos a modificar**:

  | # | Archivo | Cambio |
  |---|---|---|
  | 1 | `hooks/useLiveMatches.ts` | `(match: any)` → `(match: LiveMatchRaw)` |
  | 2 | `hooks/useLiveMatches.ts` | Segundo `any` si existe |
  | 3 | `stores/useCacheStore.ts` | `predictions: any[]` → `predictions: MatchPrediction[]` |
  | 4 | `utils/matchMatching.ts` | `prediction?: any` → `prediction?: MatchPrediction` |
  | 5 | `utils/marketUtils.ts` | `picks: any[]` → `picks: SuggestedPick[]` |
  | 6 | `infrastructure/LocalStorageObserver.ts` | `callback: (data: any)` → `callback: StorageCallback<T>` |
  | 7-8 | (otros encontrados en auditoría) | Reemplazar según forma del dato |

- **Validación**:
  ```bash
  cd frontend
  grep -rn "any" src/ --include="*.ts" --include="*.tsx" | grep -v node_modules | grep -v "\.test\." | grep -v "// " | wc -l
  # Debe reducir de 8 a 0 (o documentar los que sean intencionalmente `unknown`)
  npm run lint   # 0 errores
  npm run build  # build exitoso
  ```
- **Criterio de aceptación**: 0 usos de `any` en código de producción (excpeotions documentadas con `// eslint-disable-next-line` y justificación)
- **Commit**: `refactor(frontend): reemplazar 8 usos de any por tipos estrictos`

---

### Bloque 2.C — Eliminar API Legacy

#### F2-C1: Auditar imports de `services/api`

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: F2-B2 (tipos limpios primero)
- **Acción**:
  ```bash
  grep -rn "from.*services/api\|import.*services/api" frontend/src/
  ```
- **Resultado esperado**: Lista de archivos que importan de la API legacy
- **Criterio de aceptación**: Lista completa de todos los imports a migrar
- **Commit**: N/A (solo lectura)

---

#### F2-C2: Migrar imports y eliminar API legacy

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: F2-C1
- **Acciones por cada import encontrado**:
  1. Identificar la función importada (ej. `fetchPredictions`, `fetchLeagues`)
  2. Buscar el equivalente en `frontend/src/infrastructure/api/`
  3. Cambiar el import
  4. Verificar que la interfaz es compatible (mismos parámetros, mismo return type)
- **Después de migrar todos**:
  1. Eliminar `frontend/src/services/api.ts`
  2. Si `frontend/src/services/` queda vacío, eliminar
- **Validación**:
  ```bash
  cd frontend
  grep -rn "services/api" src/  # → 0 resultados
  npm run build                 # exitoso
  npx vitest run                # todos pasan
  npm run lint                  # 0 errores
  ```
- **Criterio de aceptación**: 0 imports de `services/api`, build + tests + lint pasando
- **Commit**: `refactor(frontend): eliminar services/api.ts legacy y consolidar en infrastructure/api/`

---

### Bloque 2.D — ML Model Versioning

#### F2-D1: Crear model registry base

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Archivos nuevos**:
  - `backend/ml_models/registry.json`:
    ```json
    {"models": [], "last_updated": null}
    ```
  - `backend/ml_models/.gitkeep` (archivo vacío)
- **Criterio de aceptación**: Los archivos existen y `registry.json` es JSON válido
- **Commit**: Incluir en F2-D3

---

#### F2-D2: Integrar métricas en entrenamiento

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: L
- **Dependencias**: F2-D1
- **Pre-requisito**: Leer `backend/scripts/train_model_optimized.py` completo
- **Archivo a modificar**: `backend/scripts/train_model_optimized.py`
- **Cambios**:
  1. Agregar imports:
     ```python
     from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
     import json
     from datetime import datetime
     ```
  2. Después de cada `model.fit()` y `joblib.dump()`, calcular métricas con el test split:
     ```python
     y_pred = model.predict(X_test)
     metrics = {
         "accuracy": round(accuracy_score(y_test, y_pred), 4),
         "precision": round(precision_score(y_test, y_pred, average="weighted", zero_division=0), 4),
         "recall": round(recall_score(y_test, y_pred, average="weighted", zero_division=0), 4),
         "f1": round(f1_score(y_test, y_pred, average="weighted", zero_division=0), 4),
     }
     ```
  3. Escribir en `registry.json`:
     ```python
     registry_path = Path("ml_models/registry.json")
     registry = json.loads(registry_path.read_text()) if registry_path.exists() else {"models": [], "last_updated": None}
     
     registry["models"].append({
         "league": league_code,
         "target": target,
         "version": datetime.now().isoformat(),
         "file": model_filename,
         "metrics": metrics,
         "training_date": datetime.now().strftime("%Y-%m-%d"),
         "training_samples": len(X_train),
     })
     registry["last_updated"] = datetime.now().isoformat()
     
     # Mantener solo las últimas 5 versiones por league+target
     # ... (lógica de purga)
     
     registry_path.write_text(json.dumps(registry, indent=2))
     ```
- **Criterio de aceptación**:
  - Después de entrenar, `registry.json` contiene las métricas del modelo
  - Incluye accuracy, precision, recall, F1
  - Timestamps presentes
- **Commit**: Incluir en F2-D3

---

#### F2-D3: Excluir .joblib del repo y actualizar endpoint

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F2-D2
- **Archivos a modificar**:
  1. `.gitignore` (raíz) — agregar:
     ```
     # Modelos ML (generados por pipeline local)
     backend/ml_models/*.joblib
     backend/ml_picks_classifier.joblib
     backend/learning_weights.json
     ```
  2. `backend/src/api/main.py` — actualizar endpoint `/api/v1/train/status` para leer `registry.json`:
     ```python
     @app.get("/api/v1/train/status")
     async def train_status():
         registry_path = Path("ml_models/registry.json")
         if not registry_path.exists():
             return {"status": "No models trained yet"}
         registry = json.loads(registry_path.read_text())
         return {
             "last_updated": registry.get("last_updated"),
             "models_count": len(registry.get("models", [])),
             "latest_models": registry.get("models", [])[-5:],
         }
     ```
- **Acciones git** (ejecutar manualmente, NO automatizar):
  ```bash
  git rm --cached backend/ml_models/*.joblib backend/ml_picks_classifier.joblib backend/learning_weights.json
  ```
  **⚠️ IMPORTANTE**: `--cached` solo quita del tracking, NO borra los archivos locales.
- **Validación**:
  ```bash
  git status  # .joblib aparece como deleted en staging, pero archivos siguen en disco
  curl http://localhost:8000/api/v1/train/status  # JSON con info del registry
  ```
- **Criterio de aceptación**: .joblib no tracked por git, registry.json sí tracked, endpoint devuelve métricas
- **Commit**: `feat(backend): model registry JSON con métricas y excluir .joblib del repo`

---

### Bloque 2.E — Structured Logging

#### F2-E1: Crear módulo de logging centralizado

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-C3 (error handling limpio)
- **Archivo nuevo**: `backend/src/core/logging_config.py`
- **Contenido** (ver spec §6.7 para implementación completa):
  ```python
  """Configuración centralizada de logging JSON."""
  import json
  import logging
  from datetime import datetime, timezone


  class JSONFormatter(logging.Formatter):
      """Formatter que produce JSON por línea para fácil parseo."""

      def format(self, record: logging.LogRecord) -> str:
          log_entry = {
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "level": record.levelname,
              "logger": record.name,
              "message": record.getMessage(),
              "module": record.module,
              "function": record.funcName,
              "line": record.lineno,
          }
          if record.exc_info and record.exc_info[1]:
              log_entry["exception"] = self.formatException(record.exc_info)
          return json.dumps(log_entry)


  def configure_logging(level: str = "INFO") -> None:
      """Configura logging global con formato JSON."""
      handler = logging.StreamHandler()
      handler.setFormatter(JSONFormatter())
      root = logging.getLogger()
      root.handlers.clear()
      root.addHandler(handler)
      root.setLevel(getattr(logging, level.upper(), logging.INFO))
  ```
- **Criterio de aceptación**: `from src.core.logging_config import configure_logging` importa OK
- **Commit**: Incluir en F2-E2

---

#### F2-E2: Integrar logging JSON en API y Worker

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F2-E1
- **Archivos a modificar**:
  1. `backend/src/api/main.py`:
     - Agregar al inicio (ANTES de crear `app`):
       ```python
       from src.core.logging_config import configure_logging
       configure_logging(os.getenv("LOG_LEVEL", "INFO"))
       ```
     - Eliminar cualquier `logging.basicConfig(...)` existente
  2. `backend/src/worker.py`:
     - Agregar al inicio:
       ```python
       from src.core.logging_config import configure_logging
       configure_logging(os.getenv("LOG_LEVEL", "INFO"))
       ```
     - Eliminar `logging.basicConfig(level=logging.INFO, format=...)` existente
  3. Buscar y eliminar TODOS los `logging.basicConfig(...)` en `backend/src/`:
     ```bash
     grep -rn "logging.basicConfig" backend/src/
     ```
- **Test nuevo**: `backend/tests/unit/test_logging_config.py`
  ```python
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
- **Validación**:
  ```bash
  cd backend
  pytest tests/unit/test_logging_config.py -v  # pasa
  python -c "from src.core.logging_config import configure_logging; configure_logging('INFO')"  # OK
  ```
- **Criterio de aceptación**: Logging en JSON, sin `logging.basicConfig` remanentes, test pasa
- **Commit**: `refactor(backend): structured logging JSON centralizado`

---

### Bloque 2.F — Coverage Backend ≥60%

#### F2-F1: Tests adicionales de servicios

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: L
- **Dependencias**: F1-D7
- **Archivos nuevos**:
  - `backend/tests/unit/test_learning_service.py`:
    - `test_weights_update`: Feedback positivo → weight aumenta
    - `test_weights_decrease_on_loss`: Feedback negativo → weight disminuye
    - `test_weights_bounded`: Weight nunca < 0 ni > 1
    - `test_feedback_loop_idempotent`: Mismo feedback 2 veces no aplica doble
  - `backend/tests/unit/test_statistics_service.py`:
    - `test_team_stats_calculation`: Datos crudos → stats correctos
    - `test_league_average_fallback`: Sin stats equipo → usa promedio liga
    - `test_zero_matches_empty_stats`: 0 matches → stats vacíos/default
  - `backend/tests/unit/test_match_aggregator.py`:
    - `test_priority_uk_over_org`: Datos UK y Org → UK prevalece
    - `test_multi_source_merge`: 3 fuentes → merge correcto sin duplicados
    - `test_deduplication`: Mismo match de 2 fuentes → 1 resultado
- **Criterio de aceptación**: ≥12 tests nuevos pasando
- **Commit**: Incluir en F2-F3

---

#### F2-F2: Tests de integración API

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F1-B5 (seguridad configurada)
- **Archivo nuevo**: `backend/tests/integration/test_api_endpoints.py`
- **Tests**:

  | Test | Endpoint | Assert |
  |---|---|---|
  | `test_health` | GET /health | 200, JSON con status |
  | `test_leagues` | GET /api/v1/leagues | 200, JSON array |
  | `test_predictions_valid_league` | GET /api/v1/predictions/E0 | 200 o 404 (si no hay datos) |
  | `test_predictions_invalid_league` | GET /api/v1/predictions/INVALID | 404 |
  | `test_train_status` | GET /api/v1/train/status | 200, JSON |
  | `test_train_trigger_auth` | POST /api/v1/train/run-now sin key | 403 |

- **Setup**: Usar `TestClient` de FastAPI, mockear las dependencias de BD si necesario
- **Criterio de aceptación**: ≥6 tests pasando
- **Commit**: Incluir en F2-F3

---

#### F2-F3: Subir umbral de coverage a 60%

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: F2-F1, F2-F2
- **Archivo a modificar**: `backend/pyproject.toml`
- **Cambio**: `--cov-fail-under=30` → `--cov-fail-under=60`
- **Validación**:
  ```bash
  cd backend && pytest -v
  # Coverage ≥60%, 0 failing
  ```
- **Criterio de aceptación**: Coverage ≥60%, CI pasa
- **Commit**: `test(backend): tests adicionales, coverage ≥60%`

---

### Bloque 2.G — Coverage Frontend ≥40%

#### F2-G1: Tests adicionales de componentes y utils

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: L
- **Dependencias**: F1-E5
- **Archivos nuevos**:
  - Tests de componentes secundarios:
    - `LeagueSelector.test.tsx`
    - `MatchDetailsModal.test.tsx`
  - Tests de utils:
    - `matchMatching.test.ts` (funciones de matching puro)
    - `marketUtils.test.ts` (funciones de formato de mercados)
  - Tests de hooks adicionales:
    - `useSmartPolling.test.ts`
    - `useAppVisibility.test.ts`
- **Criterio de aceptación**: ≥12 tests nuevos pasando
- **Commit**: Incluir en F2-G2

---

#### F2-G2: Configurar coverage threshold

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: F2-G1
- **Archivo a modificar**: `frontend/vite.config.ts` (sección test):
  ```typescript
  test: {
    // ... config existente
    coverage: {
      provider: "v8",
      thresholds: { lines: 40 },
    },
  }
  ```
- **Validación**:
  ```bash
  cd frontend
  npx vitest run --coverage
  # Coverage ≥40%
  ```
- **Criterio de aceptación**: Coverage ≥40%, CI pasa
- **Commit**: `test(frontend): tests adicionales, coverage ≥40%`

---

## Fase 3 — Madurez Operativa

### Bloque 3.A — Migraciones PostgreSQL con Alembic

#### F3-A1: Instalar Alembic y configurar

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: Fase 2 completada
- **Acciones**:
  1. Agregar `alembic` y `sqlalchemy` a `requirements.txt`
  2. `cd backend && alembic init alembic`
  3. Configurar `alembic.ini` y `alembic/env.py` para leer `DATABASE_URL` de env
  4. Crear modelos SQLAlchemy si no existen (basándose en los entities del dominio)
- **Criterio de aceptación**: `alembic current` ejecuta sin error
- **Commit**: Incluir en F3-A2

---

#### F3-A2: Crear migración inicial

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F3-A1
- **Acciones**:
  1. `alembic revision --autogenerate -m "initial schema"`
  2. Revisar el archivo generado
  3. `alembic upgrade head` (verificar que aplica sin error)
- **Criterio de aceptación**: Migración crea las tablas esperadas en PostgreSQL
- **Commit**: `feat(backend): Alembic migraciones con esquema inicial PostgreSQL`

---

### Bloque 3.B — Multi-Stage Dockerfile

#### F3-B1: Crear Dockerfile multi-stage

- [ ] **Estado**: Pendiente
- **Agente**: Architecture
- **Tamaño**: M
- **Dependencias**: Ninguna (paralelo)
- **Archivo a modificar**: `backend/Dockerfile` (o crear `backend/Dockerfile.multistage`)
- **Stages**:
  1. `builder`: Python 3.11-slim, instalar dependencias, compilar
  2. `runtime`: Python 3.11-slim, copiar solo lo necesario del builder
- **Criterio de aceptación**:
  - `docker build -t bjj-backend .` exitoso
  - `docker images bjj-backend` → ≤500MB (vs ~800MB actual)
  - La app funciona correctamente en el container
- **Commit**: `chore(devops): Dockerfile multi-stage para imagen ≤500MB`

---

### Bloque 3.C — Sentry Monitoring

#### F3-C1: Integrar Sentry en backend

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: M
- **Dependencias**: F2-E2 (structured logging)
- **Acciones**:
  1. Agregar `sentry-sdk[fastapi]` a `requirements.txt`
  2. Inicializar Sentry en `main.py`:
     ```python
     import sentry_sdk
     sentry_sdk.init(
         dsn=os.getenv("SENTRY_DSN", ""),
         traces_sample_rate=float(os.getenv("SENTRY_TRACES_RATE", "0.1")),
         environment=os.getenv("ENVIRONMENT", "development"),
     )
     ```
  3. Actualizar `.env.example` con `SENTRY_DSN` y `SENTRY_TRACES_RATE`
- **Criterio de aceptación**: Errores 500 aparecen en Sentry dashboard
- **Commit**: `feat(backend): integrar Sentry para monitoreo de errores`

---

#### F3-C2: Integrar Sentry en frontend

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: M
- **Dependencias**: F3-C1
- **Acciones**:
  1. `npm install @sentry/react`
  2. Inicializar en `main.tsx`:
     ```typescript
     import * as Sentry from "@sentry/react";
     Sentry.init({
       dsn: import.meta.env.VITE_SENTRY_DSN || "",
       environment: import.meta.env.MODE,
     });
     ```
  3. Wrappear `<App />` con `<Sentry.ErrorBoundary>`
- **Criterio de aceptación**: Errores JS se reportan en Sentry
- **Commit**: `feat(frontend): integrar Sentry para monitoreo de errores`

---

### Bloque 3.D — Accesibilidad WCAG 2.1 AA

#### F3-D1: Instalar y configurar eslint-plugin-jsx-a11y

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: S
- **Dependencias**: Ninguna
- **Acciones**:
  1. `npm install -D eslint-plugin-jsx-a11y`
  2. Agregar plugin y reglas a `.eslintrc`/`eslint.config.js`
- **Criterio de aceptación**: `npm run lint` muestra warnings/errores de a11y
- **Commit**: Incluir en F3-D2

---

#### F3-D2: Corregir issues de accesibilidad

- [ ] **Estado**: Pendiente
- **Agente**: Frontend
- **Tamaño**: L
- **Dependencias**: F3-D1
- **Acciones**:
  1. Ejecutar `npm run lint` → lista de issues a11y
  2. Para cada issue:
     - Agregar `aria-label` a botones de solo ícono
     - Agregar `role` donde falta
     - Asegurar contraste de colores (ratio 4.5:1 mínimo)
     - Agregar `alt` a todas las imágenes
     - Asegurar navegación por teclado
  3. Verificar con `axe-core` (opcional pero recomendado)
- **Criterio de aceptación**:
  - `npm run lint` → 0 errores de jsx-a11y
  - Navegación por teclado funcional en todos los componentes interactivos
  - Todos los `<img>` tienen `alt`
  - Todos los botones de ícono tienen `aria-label`
- **Commit**: `feat(frontend): accesibilidad WCAG 2.1 AA con ARIA y eslint-plugin-jsx-a11y`

---

### Bloque 3.E — Desacoplar Domain de Infrastructure

#### F3-E1: Auditar imports directos del dominio a infraestructura

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: S
- **Dependencias**: F1-D7 (tests protegen el refactor)
- **Acción**:
  ```bash
  grep -rn "from src.infrastructure\|import src.infrastructure" backend/src/domain/
  ```
- **Resultado esperado**: Lista de violaciones DIP (domain no debe importar infrastructure)
- **Criterio de aceptación**: Lista completa de imports a corregir
- **Commit**: N/A (solo lectura)

---

#### F3-E2: Crear interfaces ABC faltantes e invertir dependencias

- [ ] **Estado**: Pendiente
- **Agente**: Backend
- **Tamaño**: L
- **Dependencias**: F3-E1
- **Acciones**:
  1. Para cada import encontrado, crear/verificar que existe una ABC en `domain/interfaces/`
  2. Modificar el servicio del dominio para importar la ABC en vez de la implementación
  3. Registrar la implementación en `dependencies.py` (inyección de dependencias)
- **Criterio de aceptación**:
  - `grep -rn "from src.infrastructure" backend/src/domain/` → 0 resultados
  - Todos los tests siguen pasando
  - `domain/` solo importa de `domain/` y stdlib
- **Commit**: `refactor(backend): desacoplar domain services de infrastructure via interfaces`

---

### Bloque 3.F — Limpieza de Deuda Técnica

#### F3-F1: Limpiar archivos obsoletos y configuración

- [ ] **Estado**: Pendiente
- **Agente**: Architecture
- **Tamaño**: M
- **Dependencias**: Todos los bloques anteriores
- **Acciones**:
  1. Buscar y eliminar archivos `.bak`, `.old`, stubs sin uso:
     ```bash
     find backend/ frontend/ -name "*.bak" -o -name "*.old" -o -name "*.orig"
     ```
  2. Verificar CORS en `main.py`:
     - Si tiene `allow_origins=["*"]`, cambiar a lista explícita de orígenes:
       ```python
       ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
       ```
  3. Verificar que `.env.example` está completo con TODAS las variables usadas
  4. Revisar `requirements.txt` por dependencias no usadas:
     ```bash
     pip install pipreqs
     pipreqs backend/ --print | diff - backend/requirements.txt
     ```
- **Criterio de aceptación**:
  - 0 archivos `.bak`/`.old`
  - CORS no usa `*` en producción
  - `.env.example` completo
  - Sin dependencias huérfanas
- **Commit**: `chore: limpiar deuda técnica (archivos obsoletos, CORS, env)`

---

## Resumen de Tareas

### Conteo por fase y agente

| Fase | Backend | Frontend | Architecture | Total |
|---|---|---|---|---|
| Fase 1 | 12 | 5 | 3 | 20 |
| Fase 2 | 7 | 6 | 0 | 13 |
| Fase 3 | 5 | 3 | 2 | 10 |
| **Total** | **24** | **14** | **5** | **43** |

### Conteo por tamaño

| Tamaño | Cantidad |
|---|---|
| S (< 30 min) | 17 |
| M (30-90 min) | 19 |
| L (> 90 min) | 7 |
| **Total** | **43** |

### Hitos de validación

| Hito | Tareas Gate | Métricas |
|---|---|---|
| Fase 1 completada | F1-A3, F1-B5, F1-C3, F1-D7, F1-E5 | CI activo, API segura, >50 tests, coverage 30% |
| Fase 2 completada | F2-A4, F2-B2, F2-C2, F2-D3, F2-E2, F2-F3, F2-G2 | Prettier, 0 any, API unificada, ML registry, logging JSON, coverage 60%/40% |
| Fase 3 completada | F3-A2, F3-B1, F3-C2, F3-D2, F3-E2, F3-F1 | Migraciones, Docker ≤500MB, Sentry, a11y, DIP, limpio |
