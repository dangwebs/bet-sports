# Reglas del Proyecto (BJJ-BetSports)

Estas reglas deben ser seguidas **A TODA COSTA** por el asistente de IA y el equipo de desarrollo.

## 1. Idioma y Comunicación

- **SIEMPRE** responde en **ESPAÑOL**.
- Mantén un tono profesional, técnico y directo.

## 2. Reglas de Negocio (Backend)

### A. Agregación Estricta de Datos (CRÍTICO)

- **Regla**: Nunca depender de una sola fuente de datos para los partidos.
- **Implementación**: Al buscar partidos (históricos o futuros), se DEBEN consultar **TODOS** los orígenes configurados (`FootballDataUK`, `FootballDataOrg`, `OpenFootball`) en paralelo.
- **Fusión**: Fusionar los resultados priorizando la fuente con datos más ricos (UK > Org > Open).

### B. "Zero Stats" (Prohibido)

- **Regla**: Nunca mostrar ceros (`0`) en estadísticas proyectadas (corners, tarjetas) para partidos futuros.
- **Implementación**: Si la data histórica de un equipo falta o es cero (ej. viene de OpenFootball), se DEBE inyectar el valor predicho por el modelo de IA (`prediction.predicted_home_corners`), el cual usa promedios de liga como base.

### C. Verificación de Caché (Frescura)

- **Regla**: Nunca servir datos obsoletos si la base de datos tiene información más reciente.
- **Implementación**: Comparar siempre el timestamp de generación del caché (`generated_at`) contra la última actualización de la DB (`db_last_updated`).
- **Condición**: Si `db_last_updated > cached_timestamp` (con buffer de 10s), se considera STALE y se debe recalcular.

## 3. Desarrollo y Mantenimiento

- **No Hardcoding**: Evitar datos estadísticos "quemados" en código. Usar siempre cálculos dinámicos o configuraciones.
- **Seguridad**: Respetar tokens de administración para endpoints críticos (ej. limpieza de caché).

## 4. Estándares de Arquitectura y Calidad (High Standards)

- **Calidad de Código**: Seguir siempre los estándares de desarrollo más altos (Clean Code).
- **Integridad**: Verificar SIEMPRE que los cambios no rompan funcionalidades existentes.
- **Principios SOLID**: Aplicar estrictamente los principios SOLID en cada refactorización o nueva implementación.
- **Arquitectura Limpia & DDD**: Respetar la arquitectura Hexagonal/Clean (Domain, Application, Infrastructure) y Domain-Driven Design.

## 5. Verificación y Entrega (Pre-Commit)

- **Validación Obligatoria**: Antes de finalizar cualquier tarea, confirmar cambios o solicitar revisión, SE DEBE:
  1. **Sintaxis y Tipado**: Ejecutar verificaciones de sintaxis (compilación) y tipado para asegurar que no hay errores groseros.
  2. **Imports**: Limpiar importaciones no utilizadas.
  3. **Formato**: Asegurar un formato limpio y consistente.

## 6. Calidad y Robustez (Testing & Typing)

- **Prohibido `any`**: En TypeScript, el uso de `any` está prohibido salvo excepciones extremas documentadas.
- **Tipado Completo en Backend**: Todas las firmas de funciones en Python deben tener _type hints_ completos.
- **Test de Regla de Negocio**: Cualquier lógica que involucre cálculo de dinero o Scoring debe tener Unit Test.

## 7. Manejo de Errores y Logging

- **No "Swallowing" Exceptions**: Está prohibido atrapar excepciones con un simple `pass`. Loguear con `logger.error` y traza completa.
- **Fail Fast**: Si falta una configuración crítica, el servicio debe fallar inmediatamente.
- **Resiliencia (Graceful Degradation)**: El sistema DEBE continuar operando con funcionalidad reducida si fallan componentes no críticos (ej. Modelo ML, APIs de terceros). Implementar _fallbacks_ a lógica estadística base.
- **Timeouts Explícitos**: Todas las llamadas a servicios externos (HTTP, DB) deben tener un timeout configurado para evitar bloqueos indefinidos.
- **Frontend Error Boundaries**: En React, envolver módulos principales en `ErrorBoundaries` para prevenir que errores de renderizado rompan toda la aplicación (White Screen of Death).
- **Estados de Carga y Error**: La UI debe gestionar explícitamente los estados de `loading` (Skeletons/Spinners) y `error` (Toasts/Alerts) para dar feedback inmediato al usuario.

## 8. Rendimiento (Performance)

- **Cómputo Pesado en Background**: Tareas >500ms (ej. entrenar modelo) deben ir a `BackgroundTasks` o `Celery`.
- **Optimización de Renders**: En React, virtualizar o memoizar listas grandes (>50 items).

## 9. Seguridad

- **Input Validation**: Todo dato de entrada debe ser validado (Pydantic).
- **Secretos**: Prohibido hardcoding de keys o tokens. Usar variables de entorno.

## 10. Estándar de Commits

- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `chore:`.

## 11. Gestión de Riesgo Financiero (CRÍTICO)

- **Límites Duros (Hard Caps)**: Stake máximo predefinido (ej. 5% Bankroll). Circuit Breakers en `RiskManager`.
- **Validación de Valor (EV+)**: Solo sugerir apuestas donde `(Probabilidad * Cuota) > 1.0`.

## 12. Integridad del Modelo y Auditoría (ML Ops)

- **Trazabilidad de Predicciones**: Cada predicción guardada debe incluir metadatos del modelo (`model_version`, `training_date`, `accuracy`).
- **Inmutabilidad Histórica**: Picks sugeridos son INMUTABLES. Solo se actualiza el resultado (`WIN`/`LOSS`).

## 13. Sanidad de Datos (Data Sanity)

- **Detección de Anomalías**: Descartar cuotas < 1.01 o > 1000, Goles > 15, etc.
- **Consistencia de Fuentes**: Abstenerse si discrepancia > 20% entre fuentes.

## 14. Frescura de Cuotas (Odds Freshness)

- **Regla**:
  - **Pre-match**: Max 60 mins antigüedad.
  - **Live**: Max 30 segs antigüedad.

## 15. Restricciones Operativas (GitHub Actions & Scope)

### A. Compliance con GitHub Free Tier

- **Runner**: `ubuntu-latest`.
- **Timeout**: Límite estricto de **60 minutos** por job.
- **Paralelismo**: Máximo 20 jobs concurrentes.

### B. Restricción de Ligas (Scope Activo)

El proyecto se limita EXCLUSIVAMENTE a las siguientes ligas Top-Tier:

- 🇪🇸 **España**: La Liga (`SP1`)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Inglaterra**: Premier League (`E0`)
- 🇩🇪 **Alemania**: Bundesliga (`D1`)
- 🇮🇹 **Italia**: Serie A (`I1`)
- 🇫🇷 **Francia**: Ligue 1 (`F1`)
- 🇵🇹 **Portugal**: Liga Portugal (`P1`)
