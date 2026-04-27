"""Lightweight metrics wrapper that tolerates missing prometheus_client.

Use `metrics.get_counter(name, documentation, labelnames=())` to obtain a
counter-like object with `inc()` method. When `prometheus_client` is not
installed the wrapper provides noop objects so instrumentation is safe.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROM_AVAILABLE = True
except Exception:
    PROM_AVAILABLE = False


class _NoopMetric:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def inc(self, *args: Any, **kwargs: Any) -> None:
        return None

    def observe(self, *args: Any, **kwargs: Any) -> None:
        return None

    def set(self, *args: Any, **kwargs: Any) -> None:
        return None


_METRICS: Dict[str, Any] = {}


def get_counter(name: str, documentation: str, labelnames: Tuple[str, ...] = ()) -> Any:
    if PROM_AVAILABLE:
        try:
            if labelnames:
                c = Counter(name, documentation, labelnames)
            else:
                c = Counter(name, documentation)
            _METRICS[name] = c
            return c
        except Exception as exc:
            logger.debug("prometheus counter creation failed: %s", exc)
    # fallback noop
    c = _NoopMetric()
    _METRICS[name] = c
    return c


def get_histogram(name: str, documentation: str) -> Any:
    if PROM_AVAILABLE:
        try:
            h = Histogram(name, documentation)
            _METRICS[name] = h
            return h
        except Exception:
            pass
    return _NoopMetric()


def get_gauge(name: str, documentation: str) -> Any:
    if PROM_AVAILABLE:
        try:
            g = Gauge(name, documentation)
            _METRICS[name] = g
            return g
        except Exception:
            pass
    return _NoopMetric()
