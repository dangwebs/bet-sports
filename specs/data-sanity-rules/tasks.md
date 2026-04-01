# Tasks: Data Sanity Rules

1. Implementar validador central
   - Crear `src/infrastructure/validators` con validadores Pydantic/JSON para timestamps, ranges y formatos.
   - Estimación: 2h

2. Añadir checks en endpoints de ingest
   - Integrar validadores en puntos de entrada (APIRouters / handlers / jobs de ingest).
   - Estimación: 2h

3. Canonicalizer de nombres de equipos
   - Usar `data/team_short_names.json` y crear `team_aliases` para normalizar nombres.
   - Estimación: 2–3h

4. Implementar scanner nocturno
   - Job nightly que escanee DB y reporte anomalías a logs/metrics.
   - Estimación: 3h

5. Tests y métricas
   - Tests unitarios para validadores y métricas Prometheus para % rechazados.
   - Estimación: 2h

6. Dashboard/alertas
   - Configurar alertas básicas para anomalías críticas.
   - Estimación: 1–2h
