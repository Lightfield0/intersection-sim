"""Scenario-runner uzerinden Faz 3 hipotezi — acil arac beklemesi.

Bu test scenarios.runner API'sini kullanarak yapilan karsilastirmanin
da test_emergency_wait_drops.py'deki yaklasimla ayni sonuca vardigini
dogrular. Aradaki fark: scenarios.runner durustluk icin ayri bir yol.
"""

from intersection_sim.scenarios.definitions import adaptive_scenario, preemptive_scenario
from intersection_sim.scenarios.runner import run_scenario


def test_preemptive_emergency_wait_lower_than_adaptive() -> None:
    """5 seed × 4 saat: preemptive acil bekleme adaptive'den belirgin dusuk."""
    seeds = [42, 7, 2024, 13, 1995]
    hours = 4.0

    a_res = run_scenario(adaptive_scenario(), seeds, hours)
    p_res = run_scenario(preemptive_scenario(), seeds, hours)

    a_em = a_res.emergency_wait_s_mean
    p_em = p_res.emergency_wait_s_mean
    assert a_em > 0 and p_em > 0

    drop_pct = (a_em - p_em) / a_em
    assert drop_pct >= 0.20, (
        f"preemptive acil arac beklemesini scenario runner uzerinden de "
        f"yeterince dusurmuyor: adaptive={a_em:.2f}, preemptive={p_em:.2f}, "
        f"dusus = {drop_pct:.1%}"
    )


def test_preemptive_normal_wait_not_severely_worse() -> None:
    """Preemptive normal arac beklemesi adaptive'in en cok %25 ustunde olsun."""
    seeds = [42, 7, 2024, 13, 1995]
    hours = 4.0

    a_res = run_scenario(adaptive_scenario(), seeds, hours)
    p_res = run_scenario(preemptive_scenario(), seeds, hours)

    a_n = a_res.normal_wait_s_mean
    p_n = p_res.normal_wait_s_mean
    pct = (p_n - a_n) / a_n if a_n > 0 else 0.0
    assert pct <= 0.25, (
        f"preemptive normal arac beklemesi cok arttirildi: "
        f"adaptive={a_n:.2f}, preemptive={p_n:.2f}, artis = {pct:.1%}"
    )
