"""Faz 3 sunum hikayesinin sayisal dogrulamasi.

Preemptive kontrolcunun adaptif kontrolcuye gore:
  1. Acil arac ortalama beklemesini belirgin sekilde dusurmesi (>=%25
     goreceli iyilesme, 5 seed ortalamasi uzerinden — hedef sunum
     icin %30 ama varyans icin esik %25'e cekildi).
  2. Normal arac ortalama beklemesini cok kotulestirmemesi (<=%20 artis).

NOT: Adaptif kontrolcu zaten kuyrukları hizla isledigi icin acil arac
cogu zaman normal yesil cevriminde gecer; preemption nadir tetiklenir.
Bu yuzden seed varyansi yuksek olabilir; coklu seed ortalamasi alarak
hipotezi degerlendiriyoruz.
"""

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.simulation.runner import run_with_controller

_SEEDS = [42, 7, 2024, 13, 1995]
_HOURS = 4.0


def _run_get_waits(controller, seed: int):  # type: ignore[no-untyped-def]
    """Bir kosumun (normal_wait, emergency_wait) ciftini dondurur."""
    config = SimConfig(seed=seed, horizon_seconds=_HOURS * 3600.0)
    inter = run_with_controller(config, controller)
    report = inter.metrics.build_report(config.horizon_seconds)
    return (
        report.mean_wait_by_type_s["normal"],
        report.mean_wait_by_type_s["emergency"],
    )


def test_preemptive_lowers_emergency_wait_significantly() -> None:
    adaptive_emergency: list[float] = []
    preemptive_emergency: list[float] = []

    for s in _SEEDS:
        _, a_em = _run_get_waits(adaptive_controller, s)
        _, p_em = _run_get_waits(preemptive_controller, s)
        # Acil arac geldi mi? Hicbir kosumda 0 olmadigini varsayalim.
        assert a_em is not None and p_em is not None, f"seed={s}: hic acil arac yok"
        adaptive_emergency.append(a_em)
        preemptive_emergency.append(p_em)

    a_avg = sum(adaptive_emergency) / len(adaptive_emergency)
    p_avg = sum(preemptive_emergency) / len(preemptive_emergency)
    drop = (a_avg - p_avg) / a_avg

    assert drop >= 0.25, (
        f"preemptive acil arac beklemesini yeterince dusurmedi: "
        f"adaptive={a_avg:.2f}s, preemptive={p_avg:.2f}s, "
        f"goreceli dusus = {drop:.1%} (beklenen >= 25%, sunum hedefi 30%)"
    )


def test_preemptive_does_not_severely_hurt_normal_vehicle_wait() -> None:
    """Preemption normal araclari fazla bekletmesin — adaptive'e yakin kalmali."""
    adaptive_normal: list[float] = []
    preemptive_normal: list[float] = []

    for s in _SEEDS:
        a_n, _ = _run_get_waits(adaptive_controller, s)
        p_n, _ = _run_get_waits(preemptive_controller, s)
        assert a_n is not None and p_n is not None
        adaptive_normal.append(a_n)
        preemptive_normal.append(p_n)

    a_avg = sum(adaptive_normal) / len(adaptive_normal)
    p_avg = sum(preemptive_normal) / len(preemptive_normal)
    # Preemptive normal arac beklemesi adaptive'in en fazla %20 ustunde olsun
    pct_change = (p_avg - a_avg) / a_avg
    assert pct_change <= 0.20, (
        f"preemptive normal arac beklemesini cok arttirdi: "
        f"adaptive={a_avg:.2f}s, preemptive={p_avg:.2f}s, "
        f"artis = {pct_change:.1%} (kabul limiti +20%)"
    )
