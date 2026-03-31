# Especificación: Definir métricas y KPIs

- Fecha: 30-03-2026
- Autor: Orchestrador / Equipo Data

## 1. Propósito
Definir un conjunto priorizado de métricas y KPIs para medir, monitorizar y mejorar la calidad de las estadísticas, la probabilidad de acierto de picks y la rentabilidad del producto.

## 2. Alcance
- Métricas de negocio (ingresos/monetización)
- Métricas de modelos (calidad y calibración de probabilidades)
- Métricas operacionales (latencia, disponibilidad, frescura de datos)
- Métricas de calidad de datos y riesgo
- Dashboards, alertas y responsables

## 3. Stakeholders
- Product Owner
- Data Science (modelado y experimentación)
- ML/Backend Engineers (ETL, serving)
- Frontend (dashboards / UX)
- Operaciones / Infra
- Compliance / Legal (riesgo)

## 4. Objetivos medibles
- Incrementar la probabilidad de acierto de picks con EV positivo.
- Mejorar la calibración de probabilidades (hacerlas confiables).
- Aumentar el ROI neto por pick y los ingresos recurrentes.
- Reducir riesgo (drawdown, rachas negativas) y controlar exposición por evento.

## 5. KPIs propuestos
A. Negocio
- Hit Rate (tasa de aciertos) por tipo de pick
- ROI por pick = (beneficio neto / cantidad apostada)
- EV medio por pick
- ARPU / ingresos por usuario activo
- Volumen de apuestas y % de picks con EV>0

B. Modelado
- Brier Score (promedio, por tipo/porcentaje de prob)
- ECE (Expected Calibration Error) por buckets (p. ej., 10 bins)
- AUC-ROC / AUC-PR (donde aplique)
- LogLoss
- Precision@K / Recall@K para top-K picks
- Sharpness (dispersión de probabilidades)

C. Operacional
- Latencia de scoring (ms)
- Freshness: retraso medio entre evento real y predicción disponible
- Jobs: % ejecuciones exitosas, duración media
- Uptime del servicio de predicción

D. Calidad de datos
- Completeness (%) por campo crítico (odds, match_date, teams)
- Missing rate y duplicados
- Schema drift / PSI por feature

E. Riesgo
- Max drawdown sobre capital simulado
- Máximo número de pérdidas consecutivas
- Exposure promedio por evento
- VAR / pérdidas esperadas en ventanas (7/30 días)

## 6. Definiciones y fórmulas (ejemplos)
- Hit Rate = picks_acertados / picks_total
- ROI = (ganancias - apuestas) / apuestas
- EV medio = mean( (prob_model * payout) - (1 - prob_model) )
- Brier = mean((p - y)^2)
- ECE: promedio ponderado de |avg_prob_bin - freq_bin|

## 7. Fuentes de datos necesarias
- Colección `predictions` (Mongo): probabilidades, metadatos, created_at
- Catálogo `matches`: fecha, equipos, competición
- Odds de casas (momento de pick)
- Historial de eventos (córners, amarillas, rojas)
- Logs de apuestas/monetización (si aplica)

## 8. Frecuencias y granularidad
- Ventanas: diario, 7d, 30d (baseline 90d para histórico)
- Desglose: por liga, por tipo de pick, por cuota (bucket)
- Actualización: métricas operativas en tiempo real/near-real, model/reporting diario

## 9. Dashboards y visualizaciones (mínimos)
- Dashboard de negocio: ROI, ingresos, volumen, hit rate por pick-type
- Dashboard de modelos: Brier/ECE por fecha, curva ROC, histogramas de probabilidad, calibration plot
- Dashboard operativa: latencias, fallos de jobs, freshness
- Dashboard de calidad de datos: missingness, PSI, últimas 30/90d

Herramientas sugeridas: Metabase/Superset para reporting; Grafana + Prometheus para métricas infra; alertas a Slack/Teams.

## 10. Reglas de alerta iniciales (sugeridas)
- ECE aumenta > 0.03 respecto baseline (alerta warn)
- Brier aumenta > 10% en 7d (alerta)
- Hit rate cae > 15% vs baseline (alerta crítica)
- Freshness > 10 minutos (alerta)
- Uptime < 99% en 24h (alerta)
- PSI > 0.2 en feature crítico (warning)

> Estos umbrales son sugeridos; calibrar tras baseline inicial.

## 11. Responsables y cadencia
- Data Science: KPIs modelo, experimentos (revisión semanal)
- Backend/ML: ETL, serving, métricas operacionales (revisión diaria)
- Product: KPIs negocio y estrategia de monetización (revisión semanal)
- Operaciones: disponibilidad e incidentes (on-call)

## 12. Criterios de aceptación
- Dashboards básicos desplegados con datos históricos (90 días)
- Consultas/Métricas reproducibles (scripts o queries en repo)
- Alertas configuradas y probadas (simulación)
- Dueños asignados y calendario de reportes

## 13. Entregables
- `specs/definir-metrics/spec.md` (este documento)
- Queries / scripts para calcular cada KPI (notebooks o scripts en `backend/`)
- Dashboards en Metabase/Grafana
- Documentación de owners y runbook de alertas

## 14. Próximos pasos (acción inmediata)
1. Validar disponibilidad de datos (colecciones Mongo y campos obligatorios).
2. Implementar queries de baseline 90d para métricas clave: Hit Rate, ROI, Brier, ECE.
3. Desplegar dashboards mínimos y configurar 3 alertas críticas.
4. Iterar thresholds y comenzar experimentos de calibración.

---

Si quieres, puedo:  
- (A) Ejecutar ahora un chequeo de disponibilidad de datos y generar los baselines (90d), o  
- (B) Priorizar la implementación de los dashboards y alertas primero.

¿Cuál prefieres? (responde A o B)