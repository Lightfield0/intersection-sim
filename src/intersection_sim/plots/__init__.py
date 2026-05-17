"""Karsilastirma grafikleri (matplotlib).

Bu paket statik PNG'ler uretir. Plotly veya animasyon yok — sunumda
basit ve okunabilir grafikler hedeflenir. Headless ortamda da calismak
icin matplotlib'in ``Agg`` backend'i kullanilir.
"""

from intersection_sim.plots.compare import (
    plot_avg_wait,
    plot_emergency_wait,
    plot_throughput,
    plot_wait_distribution,
    save_all_plots,
)

__all__ = [
    "plot_avg_wait",
    "plot_emergency_wait",
    "plot_throughput",
    "plot_wait_distribution",
    "save_all_plots",
]
