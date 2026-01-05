---
trigger: always_on
---

# Reglas del Proyecto (BJJ-BetSports)

Estas reglas deben ser seguidas **A TODA COSTA** por el asistente de IA.

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

- **Prohibido `any`**: En TypeScript, el uso de `any` está prohibido salvo excepciones extremas documentadas. (Mejora la seguridad de tipos).
- **Tipado Completo en Backend**: Todas las firmas de funciones en Python deben tener _type hints_ completos (argumentos y retornos).
- **Test de Regla de Negocio**: Cualquier lógica que involucre cálculo de dinero (Stake, Bankroll) o Scoring de predicciones DEBE tener un Unit Test asociado antes de entregarse.

## 7. Manejo de Errores y Logging

- **No "Swallowing" Exceptions**: Está prohibido atrapar excepciones con un simple `pass` o imprimir un print y continuar. Se debe loguear con `logger.error` y traza completa, o relanzar una excepción de dominio.
- **Fail Fast**: Si falta una configuración crítica (ej. API Key) al inicio, el servicio debe fallar inmediatamente, no arrancar a medias.

## 8. Rendimiento (Performance)

- **Cómputo Pesado en Background**: Cualquier tarea que tome >500ms (ej. entrenar modelo, fetch masivo) NO puede bloquear el hilo principal. Debe ir a `BackgroundTasks` o `Celery`.
- **Optimización de Renders**: En React, componentes que reciban listas grandes (>50 items) deben usar virtualización o estar memoizados (`React.memo`).

## 9. Seguridad

- **Input Validation**: Todo dato que entre a la API debe ser validado por un esquema Pydantic. Nunca confiar en el frontend.
- **Secretos**: Prohibido hardodear keys o tokens en el código, ni siquiera para "probar rápido". Siempre variables de entorno.

## 10. Estándar de Commits

- **Conventional Commits**: Exigir formato estándar en mensajes de git (ej. `feat:`, `fix:`, `refactor:`, `chore:`).

## 11. Gestión de Riesgo Financiero (CRÍTICO)

- **Límites Duros (Hard Caps)**:

  - **Regla**: Ninguna sugerencia de apuesta (`SuggestedPick`) puede exceder un Stake máximo predefinido (ej. 5% del Bankroll), independientemente de la confianza del modelo o el criterio de Kelly.
  - **Implementación**: Implementar "Circuit Breakers" en `RiskManager`. Si el cálculo de stake arroja `NaN`, `Infinity` o valores absurdos, forzar a `0.0`.

- **Validación de Valor (EV+)**:
  - **Regla**: Solo sugerir apuestas donde la Esperanza Matemática sea positiva (`(Probabilidad * Cuota) > 1.0`).
  - **Excepción**: Coberturas (Hedging) explícitamente marcadas.

## 12. Integridad del Modelo y Auditoría (ML Ops)

- **Trazabilidad de Predicciones**:

  - **Regla**: Cada predicción guardada en DB debe incluir metadatos del modelo utilizado: `model_version` (hash o fecha), `training_date` y `accuracy_at_training`.
  - **Objetivo**: Poder auditar post-mortem por qué el modelo falló una racha específica.

- **Inmutabilidad Histórica**:
  - **Regla**: Una vez que un `Pick` se ha sugerido al usuario o guardado en DB, sus valores (cuota inicial, probabilidad calculada) son INMUTABLES. Solo se actualiza el resultado (`WIN`/`LOSS`).

## 13. Sanidad de Datos (Data Sanity)

- **Detección de Anomalías (Outliers)**:

  - **Regla**: Descartar datos de entrada que violen rangos lógicos antes de alimentar al modelo.
  - **Ejemplos**: Cuotas < 1.01 o > 1000, Goles > 15, Posesión > 100%.
  - **Acción**: Si se detecta una anomalía crítica en un partido, marcarlo como `SUSPICIOUS` y no generar predicciones.

- **Consistencia de Fuentes (Data Discrepancy)**:
  - **Regla**: Si al consultar múltiples fuentes (Regla 2A) hay una discrepancia mayor al 20% en estadísticas clave (ej. Tiros a puerta), el sistema debe ABSTENERSE de predecir en mercados relacionados.

## 14. Frescura de Cuotas (Odds Freshness)

- **Regla**: Para sugerencias de apuestas, está PROHIBIDO usar cuotas cacheadas con más de:
  - **Pre-match**: 60 minutos de antigüedad.
  - **Live**: 30 segundos de antigüedad.
- **Implementación**: Verificar siempre `odds_last_updated` antes de calcular el EV. Si el dato es viejo, se asume "No Bet" o se fuerza una actualización en tiempo real.

## 15. Restricciones Operativas (GitHub Actions & Scope)

### A. Compliance con GitHub Free Tier

- **Runner**: Debe ser estrictamente `ubuntu-latest`. Prohibido usar runners de pago.
- **Timeout**: Límite estricto de **60 minutos** por job. Configurar `timeout-minutes: 60` o menos.
- **Paralelismo**: Máximo 20 jobs concurrentes (preferiblemente <10 para estabilidad).

### B. Restricción de Ligas (Scope Activo)

El proyecto se limita EXCLUSIVAMENTE a las siguientes ligas Top-Tier. **Cualquier otra liga debe ser explícitamente ignorada en entrenamiento y predicción**:

- 🇪🇸 **España**: La Liga (`SP1`)
- 🏴󠁧󠁢󠁥󠁮󠁧󠁿 **Inglaterra**: Premier League (`E0`)
- 🇩🇪 **Alemania**: Bundesliga (`D1`)
- 🇮🇹 **Italia**: Serie A (`I1`)
- 🇫🇷 **Francia**: Ligue 1 (`F1`)
- 🇧🇪 **Bélgica**: Jupiler Pro League (`B1`)
- 🇵🇹 **Portugal**: Liga Portugal (`P1`)
