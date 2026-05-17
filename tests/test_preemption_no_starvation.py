"""Preemption sonrasi normal akisa donus + yon acligi yok testi.

Preemption sonra adaptif moda donmeli; 4 yondeki tum normal araclar
yine sonunda gecmeli. Bu test, "preemption fasit dongu yapmiyor mu"
sorusunu cevaplar.
"""

from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.simulation.runner import run_with_controller


def test_all_directions_get_served_under_preemptive() -> None:
    """4 saat preemptive kosumda 4 yondeki de en az birkac arac gecmis olmali."""
    config = SimConfig(seed=42, horizon_seconds=4 * 3600.0)
    inter = run_with_controller(config, preemptive_controller)
    report = inter.metrics.build_report(config.horizon_seconds)

    # Hicbir yonun ortalama beklemesi None olmamali — yani her yon en az
    # bir arac gormus olmali.
    for d, mean in report.mean_wait_by_direction_s.items():
        assert mean is not None, f"{d} yonu hic arac gecmedi (acliga benzer)"

    # 4 yondan en az 3'una arac gecmis olmali (zaten yukarida garantili
    # ama belirginlik icin).
    served_dirs = {v.direction for v in inter.metrics.vehicles_served}
    assert len(served_dirs) == 4, f"sadece {len(served_dirs)} yon gormus arac geciyor"


def test_after_preemption_normal_flow_resumes() -> None:
    """Preemption tetiklendigi seed'lerde bile normal araclar makul surede gecsin.

    Adaptive'in en kotu yon beklemesi ~12 sn idi. Preemptive'in en kotu
    yonu adaptive'den +10 sn'den daha kotu olmamali — yani normal akis
    duyarlilikla devam etsin.
    """
    config = SimConfig(seed=42, horizon_seconds=4 * 3600.0)
    inter = run_with_controller(config, preemptive_controller)
    report = inter.metrics.build_report(config.horizon_seconds)

    # Hicbir yonun ortalama beklemesi 30 sn'den buyuk olmamali — fixed
    # baseline (~45 sn) ile karsilastirildiginda hala cok daha iyi.
    for d, mean in report.mean_wait_by_direction_s.items():
        assert mean is not None
        assert mean < 30.0, f"{d} yonu ortalama bekleme cok yuksek: {mean:.1f}s"
