"""Senaryo runner deterministik mi? Ayni seed ayni KPI'lari uretmeli."""

from intersection_sim.scenarios.definitions import adaptive_scenario, fixed_scenario
from intersection_sim.scenarios.runner import run_scenario


def test_same_seeds_produce_same_kpis_fixed() -> None:
    """Iki kez ayni seed'le calistir, sayilar birebir esit olmali."""
    seeds = [11, 22]
    r1 = run_scenario(fixed_scenario(), seeds, duration_hours=2.0)
    r2 = run_scenario(fixed_scenario(), seeds, duration_hours=2.0)

    for run1, run2 in zip(r1.runs, r2.runs):
        assert run1.seed == run2.seed
        assert run1.report.vehicles_served == run2.report.vehicles_served
        assert run1.report.mean_wait_time_s == run2.report.mean_wait_time_s
        assert run1.report.signal_change_count == run2.report.signal_change_count


def test_same_seeds_produce_same_kpis_adaptive() -> None:
    """Adaptif kontrolcu da deterministik olmali — RNG seed dis baglayicidir."""
    seeds = [42, 7]
    r1 = run_scenario(adaptive_scenario(), seeds, duration_hours=1.0)
    r2 = run_scenario(adaptive_scenario(), seeds, duration_hours=1.0)

    for run1, run2 in zip(r1.runs, r2.runs):
        assert run1.report.vehicles_served == run2.report.vehicles_served
        assert run1.report.mean_wait_time_s == run2.report.mean_wait_time_s


def test_compare_controllers_preserves_scenario_order() -> None:
    """compare_controllers ALL_SCENARIOS sirasini korumali.

    Sıra: fixed -> adaptive -> predictive -> preemptive
    """
    from intersection_sim.scenarios.runner import compare_controllers

    results = compare_controllers([0, 1], duration_hours=1.0)
    names = [r.scenario.name for r in results]
    assert names == ["fixed", "adaptive", "predictive", "preemptive"]
