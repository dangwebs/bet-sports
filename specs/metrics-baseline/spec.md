# Spec: Metrics Baseline (90d)

Resumen
-------
Definir y construir el pipeline que calcula las métricas de referencia sobre 90 días: Brier Score, Calibration (ECE), Hit Rate por mercado, ROI simulado y P&L acumulado. Resultado: un reporte reproducible para medir evolución.

Objetivos
--------
- Implementar job que agregue métricas diarias y calcule 90d rolling.
- Definir dataset: predicciones que fueron etiquetadas (auto/manual), con `model_metadata` asociado.
- Visualización mínima: CSV/JSON export para análisis y dashboard eventual.

Requisitos funcionales
----------------------
1. Brier Score por mercado y global (formulación estándar).
2. ECE (Expected Calibration Error) con 10 bins.
3. ROI y P&L calculados asumiendo stake fijo por predicción (configurable).

Desglose de tareas
------------------
1. Especificar queries para seleccionar predicciones etiquetadas (1h).
2. Implementar librería de métricas y tests (3–4h).
3. Job diario/rolling que persiste resultados en `metrics/` (2–3h).
4. Export CSV y endpoint para descargar informes (2h).

Aceptación
----------
- Pipeline puede generar reporte 90d en staging para un dataset de prueba en menos de 15 minutos.
- Métricas validadas con tests unitarios.
# Spec: Metrics Baseline (Epic 9)

Fecha: 2026-03-31

Resumen
-------
Definir y producir un baseline de métricas para 90 días que permita evaluar desempeño de modelos y del pipeline (Brier Score, ECE, ROI, P&L, cobertura de eventos).

Objetivos
---------
- Especificar métricas, ventanas (90d) y pipelines para su cálculo y almacenamiento.
- Producir reportes reproducibles con filtros por `league`, `model_version` y `market`.

Requisitos (REQ-9.x)
-------------------
- REQ-9.1: Implementar cálculo de Brier Score por partido y agregado por ventana móvil (7/30/90 días).
- REQ-9.2: Calibración (ECE) por bucket y visualización básica.
- REQ-9.3: KPI financiero (ROI, P&L) simulado por mercados y stakes definidos.

Aceptación
----------
- AC-1: Reporte 90d disponible en formato JSON/CSV.
- AC-2: Métricas reproducibles con la misma entrada data y `model_version`.

Tareas
------
1. Definir y documentar fórmulas y buckets (calibration buckets).
2. Implementar job `metrics/compute_baseline.py` y endpoint `/metrics/baseline`.
3. Validar reportes con muestra histórica (90d dry-run).
