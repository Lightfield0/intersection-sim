"""Throughput hipotezi: 3 kontrolcunun arac/saat'i birbirine yakin olmali.

Mantik: gelis hizi Poisson disindan belirleniyor (saatlik lambda).
Kontrolcu bekleme suresini optimize eder ama uzun vadede gelen tum
araclari geciris yapar — yani throughput'lar birbirine cok yakin.
"""

from intersection_sim.scenarios.runner import compare_controllers


def test_throughputs_within_5_percent() -> None:
    """3 kontrolcunun throughput'u en cok birbirinden %5 farkli olsun."""
    results = compare_controllers(seeds=[0, 1, 2], duration_hours=4.0)
    throughputs = [r.throughput_per_hour_mean for r in results]
    assert min(throughputs) > 0

    spread = (max(throughputs) - min(throughputs)) / max(throughputs)
    assert spread < 0.05, (
        f"throughput'lar cok farkli: {throughputs}, fark = {spread:.1%}"
    )
