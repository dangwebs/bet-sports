# Catálogo de métricas (Prometheus)

Este documento lista las métricas mínimas a instrumentar en el sistema.

- **labeler_labeled_total**: counter — Total de predicciones etiquetadas por el labeler. Sin labels.
- **labeler_failure_total**: counter — Fallos por ejecución del labeler.
- **labeler_latency_seconds**: histogram — Latencia del job de labeler.
- **match_predictions_backlog**: gauge — Cantidad de predicciones pendientes (no etiquetadas).
- **api_request_duration_seconds**: histogram — Latencia por endpoint (label con `endpoint` label).
- **api_errors_total**: counter — Errores 5xx por endpoint.

Convenciones

- Nombres en snake_case y sufijo tipo (`_total`, `_seconds`).
- Evitar labels con alta cardinalidad (no usar `prediction_id` como label).
- Agregar `instance` y `job` por configuración de Prometheus si aplica.

Ejemplo (usar `src/utils/metrics.py` wrapper):

```py
from src.utils.metrics import get_counter, get_histogram

LABELER_COUNTER = get_counter("labeler_labeled_total", "Total labeled predictions")

def my_labeler(...):
    LABELER_COUNTER.inc()

```
