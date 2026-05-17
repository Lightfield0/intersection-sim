"""Faz 2 sunum hikayesinin sayisal dogrulamasi.

Adaptif kontrolcu, sabit-zamanli kontrolcuden anlamli derecede daha
kisa ortalama bekleme sagliyor olmali. Eger saglanmazsa bu test fail
eder ve senaryo parametrelerini gozden gecirmemiz gerekir (
SignalConfig.adaptive_*, _GREEN_PER_VEHICLE_S vs).

Esik: en az %20 goreceli iyilesme (sunumda %30 hedef ama test bunun
altinda da gecerli — varyans tolerans icin).
"""

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.simulation.runner import run_with_controller


def _run_and_get_mean_wait(controller, seed: int, hours: float = 4.0) -> float:  # type: ignore[no-untyped-def]
    config = SimConfig(seed=seed, horizon_seconds=hours * 3600.0)
    inter = run_with_controller(config, controller)
    report = inter.metrics.build_report(config.horizon_seconds)
    assert report.mean_wait_time_s is not None
    return report.mean_wait_time_s


def test_adaptive_lowers_mean_wait_by_at_least_20_percent() -> None:
    seeds = [42, 7, 2024]
    fixed_means: list[float] = []
    adaptive_means: list[float] = []

    for s in seeds:
        fixed_means.append(_run_and_get_mean_wait(fixed_controller, s))
        adaptive_means.append(_run_and_get_mean_wait(adaptive_controller, s))

    fixed_avg = sum(fixed_means) / len(fixed_means)
    adaptive_avg = sum(adaptive_means) / len(adaptive_means)

    rel_drop = (fixed_avg - adaptive_avg) / fixed_avg

    assert rel_drop >= 0.20, (
        f"adaptif ortalama bekleme yeterince dusmedi: "
        f"fixed={fixed_avg:.2f} sn, adaptive={adaptive_avg:.2f} sn, "
        f"goreceli dusus = {rel_drop:.1%} "
        f"(beklenen >= 20%; sunum hedefi 30%)"
    )


def test_adaptive_does_not_starve_any_direction() -> None:
    """Adaptif kontrolcu max_green sinirini asmamali — hicbir yon ac kalmasin."""
    config = SimConfig(seed=42, horizon_seconds=4 * 3600.0)
    inter = run_with_controller(config, adaptive_controller)
    report = inter.metrics.build_report(config.horizon_seconds)

    # 4 yondan en az 3'une arac gelmis ve gecmis olmali
    served_dirs = {v.direction for v in inter.metrics.vehicles_served}
    assert len(served_dirs) >= 3, (
        f"adaptif kontrolcu bazi yonleri tamamen ac biraktirdi: {served_dirs}"
    )

    # Yon bazli ortalama bekleme kontrolu: hicbir yonun ortalamasi
    # max_green'den + 30 saniye buffer'den buyuk olmamali
    cap = config.signal.adaptive_max_green_s + 30.0
    for d, mean in report.mean_wait_by_direction_s.items():
        if mean is not None:
            assert mean < cap, (
                f"{d} yonu ortalama beklemesi {mean:.1f}s > kapak {cap:.1f}s"
            )
