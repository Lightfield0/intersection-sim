"""KPI toplama ve raporlama modulu.

Bu paket simulasyondan tamamen ayri durur — SimPy yok, sadece pydantic
veri sinifi ve pandas. Boylece testler MetricsCollector'a sentetik arac
verisi vererek hesaplamalari dogrulayabilir.
"""

from intersection_sim.metrics.metrics_collector import (
    MetricsCollector,
    MetricsReport,
    MetricsSnapshot,
)

__all__ = ["MetricsCollector", "MetricsReport", "MetricsSnapshot"]
