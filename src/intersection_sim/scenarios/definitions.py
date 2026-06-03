"""Uc senaryo tanimi — her biri bir kontrolcüye karsilik gelir.

Tüm senaryolar ayni ``SimConfig`` ile kosar; tek fark hangi kontrolcünün
isiklarini yonettigidir. Böylece "ayni trafik, farkli karar verme
stratejisi" karsilastirmasi temiz oturur.

Her senaryo bir factory fonksiyonu ile temsil edilir — ``SimConfig``'i
(seed ve sure parametreleriyle) üretir ve hangi kontrolcuyu kullanacagini
soyler. Triage projesinde scenarios dict olarak tutuluyordu; burada
hafif bir dataclass kullaniyoruz, daha okunur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.controllers.predictive import predictive_controller
from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig

# Hangi paletten renklendirme yapilacagi — plotlama tarafinda da kullanilir.
COLOR_FIXED = "#DC2626"       # kirmizi — pasif baseline
COLOR_ADAPTIVE = "#EAB308"    # altin sari — adaptif
COLOR_PREEMPTIVE = "#16A34A"  # yesil — preemptive (en iyi acil)
COLOR_PREDICTIVE = "#7C3AED"  # mor — predictive (trend tahminli)


@dataclass(frozen=True)
class ScenarioDef:
    """Bir senaryonun statik tanimi.

    - ``name`` raporlarda ve dosya isimlerinde kullanilir (kısa ingilizce).
    - ``display_name_tr`` sunum grafiklerinde gosterilir (Türkçe).
    - ``controller`` bu senaryonun kullandigi SimPy kontrolcü fonksiyonu.
    - ``color`` matplotlib rengi.
    - ``description_tr`` 1 cumlelik açıklama (findings.md için).
    """

    name: str
    display_name_tr: str
    controller: Callable[..., Any]
    color: str
    description_tr: str

    def build_config(self, seed: int, duration_hours: float) -> SimConfig:
        """Bu senaryonun varsayilan SimConfig'ini üretir."""
        return SimConfig(
            seed=seed,
            horizon_seconds=duration_hours * 3600.0,
        )


def fixed_scenario() -> ScenarioDef:
    """Sabit-zamanli kontrolcü senaryosu — pasif baseline."""
    return ScenarioDef(
        name="fixed",
        display_name_tr="Sabit Zamanlı",
        controller=fixed_controller,
        color=COLOR_FIXED,
        description_tr=(
            "Her yone sirayla 30 sn yesil. Trafik yogunluguna duyarsız, "
            "boş yone bile yesil verir."
        ),
    )


def adaptive_scenario() -> ScenarioDef:
    """Adaptif kontrolcü senaryosu — kuyruga göre dinamik yesil."""
    return ScenarioDef(
        name="adaptive",
        display_name_tr="Adaptif",
        controller=adaptive_controller,
        color=COLOR_ADAPTIVE,
        description_tr=(
            "En uzun kuyruga sahip yone yesil; sure = arac sayisi x 3 sn "
            "(min 15, max 60). Boş yonu atlar."
        ),
    )


def preemptive_scenario() -> ScenarioDef:
    """Acil-öncelikli kontrolcü senaryosu — adaptif + acil arac preemption."""
    return ScenarioDef(
        name="preemptive",
        display_name_tr="Acil Öncelikli",
        controller=preemptive_controller,
        color=COLOR_PREEMPTIVE,
        description_tr=(
            "Adaptif mantık + acil arac geldiginde mevcut yesil 5 sn'de "
            "kapanir, acil yone 15 sn sabit yesil verilir."
        ),
    )


def predictive_scenario() -> ScenarioDef:
    """Tahmine dayali kontrolcü — adaptifin trend-aware varyanti."""
    return ScenarioDef(
        name="predictive",
        display_name_tr="Tahmine Dayalı",
        controller=predictive_controller,
        color=COLOR_PREDICTIVE,
        description_tr=(
            "Son 60 sn snapshot'larindan trend hesaplar; 30 sn sonrasi icin "
            "en kalabalik tahmini yone yesil verir. Adaptifin 'anlik' yerine "
            "'yakin gelecek' versiyonu."
        ),
    )


# Sunum siralamasi — fixed (kötü) → adaptive → predictive → preemptive (acil).
ALL_SCENARIOS: list[ScenarioDef] = [
    fixed_scenario(),
    adaptive_scenario(),
    predictive_scenario(),
    preemptive_scenario(),
]
