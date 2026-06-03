"""İstatistiksel anlamlılık testleri — Mann-Whitney U.

Sunumdaki adaptive vs hibrit predictive karşılaştırmasının gerçek bir
farklılık mı yoksa seed gürültüsü mü olduğunu doğrular. Mann-Whitney U
non-parametrik (normal dağılım varsaymıyor) ve 10 seed gibi küçük
örneklemde uygundur.

Beklenenler:
1. Ortalama bekleme adaptive ≈ predictive (eşdeğer — anlamlı fark yok,
   p > 0.05). Hipotez: trend bonusu ortalamayı kaybettirmedi.
2. p95 adaptive > predictive (predictive daha iyi, p < 0.05 anlamlı).
3. Fairness adaptive < predictive (predictive daha adil, p < 0.05).
4. Sanity: fixed >> adaptive (her metrik için p << 0.001).
"""

import pytest
from scipy.stats import mannwhitneyu

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.controllers.predictive import predictive_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.simulation.runner import run_with_controller

# Aynı seed-setiyle 3 kontrolcüyü koştur — session scope ile cache'le.
N_SEEDS: int = 10
DURATION_HOURS: float = 4.0


@pytest.fixture(scope="session")
def controller_metrics() -> dict[str, dict[str, list[float]]]:
    """N_SEEDS koşum × 3 kontrolcü → her metric için liste.

    Yapı: {controller_name: {metric_name: [values per seed]}}
    """
    out: dict[str, dict[str, list[float]]] = {
        name: {"mean_wait": [], "p95_wait": [], "fairness": []}
        for name in ["fixed", "adaptive", "predictive"]
    }
    for name, ctrl in [
        ("fixed", fixed_controller),
        ("adaptive", adaptive_controller),
        ("predictive", predictive_controller),
    ]:
        for seed in range(N_SEEDS):
            cfg = SimConfig(seed=seed, horizon_seconds=DURATION_HOURS * 3600.0)
            intersection = run_with_controller(cfg, ctrl)
            r = intersection.metrics.build_report(cfg.horizon_seconds)
            assert r.mean_wait_time_s is not None
            assert r.wait_percentiles_s["p95"] is not None
            assert r.fairness_index is not None
            out[name]["mean_wait"].append(r.mean_wait_time_s)
            out[name]["p95_wait"].append(r.wait_percentiles_s["p95"])
            out[name]["fairness"].append(r.fairness_index)
    return out


# ---------- Adaptive vs Predictive — ortalama bekleme EŞDEĞER --------------


def test_adaptive_vs_predictive_mean_wait_not_significant(
    controller_metrics: dict[str, dict[str, list[float]]],
) -> None:
    """Hibrit predictive ortalama bekleme adaptiften ANLAMLI farklı olmamalı.

    Bu, "trend bonusu ortalamayı kaybettirmedi" iddiamızı doğrular.
    Mann-Whitney U two-sided; p > 0.05 → null red edilemez (eşdeğer).
    """
    adapt = controller_metrics["adaptive"]["mean_wait"]
    pred = controller_metrics["predictive"]["mean_wait"]
    _, pval = mannwhitneyu(adapt, pred, alternative="two-sided")
    # 10 seed'de mean fark çok küçük (0.01 sn) → eşdeğer beklenir
    assert pval > 0.05, (
        f"adaptive vs predictive mean farkı anlamlı çıktı (p={pval:.4f}). "
        f"Beklenen: eşdeğer (p>0.05)."
    )


# ---------- Adaptive vs Predictive — p95 PREDICTIVE DAHA İYİ ---------------


def test_adaptive_vs_predictive_p95_predictive_better(
    controller_metrics: dict[str, dict[str, list[float]]],
) -> None:
    """Predictive p95 (kötü uç) adaptiften ANLAMLI daha düşük olmalı.

    Mann-Whitney one-sided 'less': predictive p95 < adaptive p95.
    Hipotez: trend bonusu kötü ucu düşürdü.
    """
    adapt = controller_metrics["adaptive"]["p95_wait"]
    pred = controller_metrics["predictive"]["p95_wait"]
    _, pval = mannwhitneyu(pred, adapt, alternative="less")
    assert pval < 0.05, (
        f"predictive p95 < adaptive p95 anlamlı çıkmadı (p={pval:.4f}). "
        f"adaptive p95 ortalaması: {sum(adapt)/len(adapt):.2f} sn, "
        f"predictive p95 ortalaması: {sum(pred)/len(pred):.2f} sn"
    )


# ---------- Adaptive vs Predictive — fairness PREDICTIVE DAHA İYİ ----------


def test_adaptive_vs_predictive_fairness_predictive_better(
    controller_metrics: dict[str, dict[str, list[float]]],
) -> None:
    """Predictive fairness adaptiften ANLAMLI daha yüksek olmalı.

    Mann-Whitney one-sided 'greater': predictive fairness > adaptive.
    Hipotez: trend bonusu yönler arası dağılımı eşitledi.
    """
    adapt = controller_metrics["adaptive"]["fairness"]
    pred = controller_metrics["predictive"]["fairness"]
    _, pval = mannwhitneyu(pred, adapt, alternative="greater")
    assert pval < 0.05, (
        f"predictive fairness > adaptive fairness anlamlı çıkmadı "
        f"(p={pval:.4f}). adaptive ort: {sum(adapt)/len(adapt):.4f}, "
        f"predictive ort: {sum(pred)/len(pred):.4f}"
    )


# ---------- Sanity check — Fixed FELAKET, adaptive ÇOK iyi -----------------


def test_fixed_vs_adaptive_mean_wait_highly_significant(
    controller_metrics: dict[str, dict[str, list[float]]],
) -> None:
    """Sabit kontrolün adaptive'den çok daha kötü olduğu çok anlamlı (p<0.001).

    Sanity check: temel sunum bulgumuzun istatistiksel olarak güçlü
    olduğunu gösterir.
    """
    fixed = controller_metrics["fixed"]["mean_wait"]
    adapt = controller_metrics["adaptive"]["mean_wait"]
    _, pval = mannwhitneyu(fixed, adapt, alternative="greater")
    assert pval < 0.001, (
        f"fixed >> adaptive yeterince anlamlı çıkmadı (p={pval:.4f}). "
        f"Beklenen: p<0.001 (sunum temel bulgusu güçlü olmalı)."
    )


def test_fixed_vs_adaptive_fairness_lower_in_adaptive(
    controller_metrics: dict[str, dict[str, list[float]]],
) -> None:
    """Fairness paradoksu: fixed > adaptive fairness — ama mean wait
    çok daha kötü. Hocaya göstereceğimiz nüansı doğrular.
    """
    fixed = controller_metrics["fixed"]["fairness"]
    adapt = controller_metrics["adaptive"]["fairness"]
    _, pval = mannwhitneyu(fixed, adapt, alternative="greater")
    # Fixed fairness'i daha yüksek olmalı — paradoks vurgusu
    assert pval < 0.05, (
        f"fixed > adaptive fairness anlamlı çıkmadı (p={pval:.4f}). "
        f"Fairness paradoksu için fixed fairness'in adaptiften yüksek "
        f"olması bekleniyordu."
    )
