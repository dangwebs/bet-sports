# Baseline 90d — Disponibilidad de datos y métricas

- Fecha: 31-03-2026
- Generado por: Orquestador (resumen automático)

## 1) Resumen de disponibilidad de datos
- Colección `match_predictions`: 104 documentos (predicciones actuales).  
  - Estados principales en ventana 90d: `NS`: 54, `TIMED`: 50 (ninguno `FT`).  
  - Conclusión: `match_predictions` contiene predicciones para partidos programados (no resultados finales), por lo que NO se puede usar directamente para calcular Brier/ECE/hit-rate por partido sin etiquetado posterior.

- Colección `training_results` (key=`latest_daily`): serie histórica y métricas agregadas.
  - `matches_processed`: 4424
  - `correct_predictions`: 2113
  - `accuracy`: 0.4776
  - `total_bets`: 4421
  - `roi` (agregado): -100.0
  - `profit_units`: -4421.0
  - `roi_evolution` points: 355 (serie histórica)
  - `roi_evolution` en los últimos 90d: 71 puntos
  - `avg_roi_90d` (promedio sobre `roi_evolution` últimos 90d): -50.34633802816903
  - `profit_change_90d`: -471.0 units

## 2) Métricas/tendencias detectadas (baseline)
- Accuracy global (histórica): 47.76%.
- ROI histórico agregado: negativo (indicador de pérdidas netas en backtests/registry).
- Evolución reciente (últimos 90d): ROI medio ~ -50.35 (unidad % / formato de la serie), pérdida acumulada ~ -471 unidades en la ventana.
- `pick_efficiency` (resumen por tipo de pick): hay mercados con alta eficiencia histórica (ejemplos):
  - `goals_over_0_5`: 93.87%  
  - `home_corners_over`: 85.22%  
  - `away_corners_over`: 84.90%  
  - `goals_under`: 84.18%  
  - `team_goals_over`: 77.88%  
  (lista completa en `training_results.data.pick_efficiency`)

## 3) Limitaciones identificadas
- `match_predictions` no contiene resultados finales; falta un pipeline que etiquete automáticamente predicciones cuando acaba el partido (labeling).  
- `match_predictions.data.prediction` contiene probabilidades (`home_win_probability`, `over_25_probability`, `predicted_*`) y `created_at` — esto permite trazabilidad pero se requiere:  
  - almacenar `odds` en el momento de la predicción (`real_time_odds` / `prediction.opening_odds`) para calcular EV/ROI per-pick;  
  - registrar outcome final (y) y tiempo de resolución para cada predicción para cálculos de Brier/ECE.
- `training_results` ofrece métricas agregadas útiles (ROI series, accuracy, pick_efficiency) pero no desagregación por probabilidad-buckets ni Brier por market (market_stats vacío).

## 4) Recomendaciones inmediatas (prioridad alta)
1. Implementar proceso de etiquetado automático: cuando `match.status` pase a `FT`/finalizar, anexar `outcome` a la predicción original y guardar en histórico (colección `match_predictions_labeled` o actualizar documento). Esto es requisito para Brier/ECE y calibración.
2. Garantizar captura de `odds` en el instante de la predicción y almacenarlas en `data.prediction.opening_odds` o `data.real_time_odds` (para EV/ROI verdadero).
3. Generar scripts reproducibles (notebook/python) que calculen: Brier, ECE (10 bins), hit-rate por threshold, ROI per-pick y ROI por market. Repetible y versionado en `backend/scripts/metrics_baseline.py`.
4. Priorizar mercados con alta `pick_efficiency` para producto mínimo viable (reduce ruido): empezar con `goals_over_0_5`, `home_corners_over`, `away_corners_over`, `goals_under`.
5. Configurar alertas iniciales en Grafana/Metabase para: caída de accuracy >10 p.p., ECE aumento >0.03, ROI diario < umbral (configurable).

## 5) Recomendaciones técnicas (mediano plazo)
- Añadir métricas por-probabilidad (calibration plots): agrupar por bins (0-10%,10-20%,...), almacenar ECE diario y Brier por market.
- Calibración de probabilidades (Platt / isotonic) usando datos etiquetados; validar por walk-forward.
- Implementar backtesting robusto y walk-forward para validar staking y thresholds (evitar lookahead bias).
- Reforzar ETL: garantías de integridad/duplicados, PSI para detectar drift de features.

## 6) Entregables propuestos (próxima iteración)
- Script reproducible: `backend/scripts/metrics_baseline.py` (genera CSV/JSON de KPIs y plots).  
- Notebook con calibration plots y Brier/ECE por market.  
- Reporte `specs/definir-metrics/baseline-90d.md` (este archivo).  
- Dashboards mínimos: (a) `Model Health` (Brier, ECE, accuracy), (b) `Business` (ROI, profit, volume), (c) `Data Quality` (missingness, freshness).

---

Si quieres, puedo continuar con una de las siguientes acciones:  
- **B**: crear los dashboards mínimos y configurar 3 alertas críticas (Grafana/Metabase).  
- **C**: generar el script reproducible `backend/scripts/metrics_baseline.py` que calcule y guarde los KPIs 90d (y ejecutar localmente para guardar resultados).  

Responde **B** o **C** para que proceda.  

(He marcado la comprobación de disponibilidad de datos como completada en la TODO list.)
