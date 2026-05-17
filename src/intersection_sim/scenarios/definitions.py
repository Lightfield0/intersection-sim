"""Uc senaryo tanimi — her biri bir kontrolcuye karsilik gelir.

Tum senaryolar ayni ``SimConfig`` ile kosar; tek fark hangi kontrolcunun
isiklarini yonettigidir. Boylece "ayni trafik, farkli karar verme
stratejisi" karsilastirmasi temiz oturur.

Her senaryo bir factory fonksiyonu ile temsil edilir — ``SimConfig``'i
(seed ve sure parametreleriyle) uretir ve hangi kontrolcuyu kullanacagini
soyler. Triage projesinde scenarios dict olarak tutuluyordu; burada
hafif bir dataclass kullaniyoruz, daha okunur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from intersection_sim.controllers.adaptive import adaptive_controller
from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig

# Hangi paletten renklendirme yapilacagi — plotlama tarafinda da kullanilir.
COLOR_FIXED = "#DC2626"       # kirmizi — pasif baseline
COLOR_ADAPTIVE = "#EAB308"    # altin sari — adaptif
COLOR_PREEMPTIVE = "#16A34A"  # yesil — preemptive (en iyi acil)


@dataclass(frozen=True)
class ScenarioDef:
    """Bir senaryonun statik tanimi.

    - ``name`` raporlarda ve dosya isimlerinde kullanilir (kisa ingilizce).
    - ``display_name_tr`` sunum grafiklerinde gosterilir (Turkce).
    - ``controller`` bu senaryonun kullandigi SimPy kontrolcu fonksiyonu.
    - ``color`` matplotlib rengi.
    - ``description_tr`` 1 cumlelik aciklama (findings.md icin).
    """

    name: str
    display_name_tr: str
    controller: Callable[..., Any]
    color: str
    description_tr: str

    def build_config(self, seed: int, duration_hours: float) -> SimConfig:
        """Bu senaryonun varsayilan SimConfig'ini uretir."""
        return SimConfig(
            seed=seed,
            horizon_seconds=duration_hours * 3600.0,
        )


def fixed_scenario() -> ScenarioDef:
    """Sabit-zamanli kontrolcu senaryosu — pasif baseline."""
    return ScenarioDef(
        name="fixed",
        display_name_tr="Sabit Zamanli",
        controller=fixed_controller,
        color=COLOR_FIXED,
        description_tr=(
            "Her yone sirayla 30 sn yesil. Trafik yogunluguna duyarsiz, "
            "bos yone bile yesil verir."
        ),
    )


def adaptive_scenario() -> ScenarioDef:
    """Adaptif kontrolcu senaryosu — kuyruga gore dinamik yesil."""
    return ScenarioDef(
        name="adaptive",
        display_name_tr="Adaptif",
        controller=adaptive_controller,
        color=COLOR_ADAPTIVE,
        description_tr=(
            "En uzun kuyruga sahip yone yesil; sure = arac sayisi x 3 sn "
            "(min 15, max 60). Bos yonu atlar."
        ),
    )


def preemptive_scenario() -> ScenarioDef:
    """Acil-oncelikli kontrolcu senaryosu — adaptif + acil arac preemption."""
    return ScenarioDef(
        name="preemptive",
        display_name_tr="Acil Oncelikli",
        controller=preemptive_controller,
        color=COLOR_PREEMPTIVE,
        description_tr=(
            "Adaptif mantik + acil arac geldiginde mevcut yesil 5 sn'de "
            "kapanir, acil yone 15 sn sabit yesil verilir."
        ),
    )


# Sunum siralamasi — fixed (kotu) → adaptive (iyi) → preemptive (en iyi acil).
ALL_SCENARIOS: list[ScenarioDef] = [
    fixed_scenario(),
    adaptive_scenario(),
    preemptive_scenario(),
]
