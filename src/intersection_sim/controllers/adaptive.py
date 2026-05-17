"""Adaptif (kuyruk-uzunluguna duyarli) trafik isigi kontrolcusu.

Sabit-zamanli kontrolcunun zayifligi: bos yone bile 30 sn yesil veriyor,
dolu yon kuyrukta bekliyor. Adaptif kontrolcu iki yerden duyarli:

1. **Yon secimi:** Sira sabit degil. Her yesil periyodu baslamadan once
   4 yonun kuyruk uzunluklarina bakilir, en uzun olan secilir.

2. **Yesil suresi:** Sabit 30 sn yerine, kuyruk uzunluguna gore
   hesaplanir:

       green = clamp(queue * GREEN_PER_VEHICLE_S, min_green, max_green)

   Buradaki ``GREEN_PER_VEHICLE_S`` her aracin kavsagi gecmesi icin
   ayrilan ortalama yesil suresi (default 3 sn — gercek bir arac
   crossing_time_s=2sn'de gecer ama tepki/baslama suresi de var).

Min ve max sinirlari (SignalConfig'te tanimli) bir yonun ne cok kisa
ne de tekelci uzun yesil almasini engeller. Default: min=15sn, max=60sn.

Diger yonlerin "aclik yasayisi" probleminin onune gecmek icin: yesil
suresi max=60 ile sinirli; cok dolu bir yon bile en fazla 60 sn alir,
sonra siradakine baslanir.
"""

from typing import TYPE_CHECKING

from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState
from intersection_sim.simulation.crossing import cross_during_green

if TYPE_CHECKING:
    from collections.abc import Generator

    import simpy

    from intersection_sim.simulation.intersection import Intersection


# Bir aracin yesilden gecmesi icin ayrilan ortalama tahmini sure (sn).
# crossing_time_s sabit 2 sn ama burada 3 kullaniyoruz cunku tepki +
# baslama gecikmesi var (kuyrugun ortasindan kalkis daha yavas).
_GREEN_PER_VEHICLE_S: float = 3.0


def _pick_direction(intersection: "Intersection") -> Direction:
    """En uzun kuyruga sahip yonu secer.

    Eslik durumunda (ayni kuyruk uzunlugu birden cok yonde) ``max``
    fonksiyonu sirayi N -> E -> S -> W olarak kullanir (ALL_DIRECTIONS
    sirasi). Bu eslik durumunda kuzeyi tercih etmek anlamina gelir —
    deterministik bir secim.
    """
    return max(ALL_DIRECTIONS, key=lambda d: intersection.queue_length(d))


def _green_duration_for(queue_length: int, cfg) -> float:  # type: ignore[no-untyped-def]
    """Kuyruk uzunluguna gore yesil sure tahmini.

    Bos kuyruk olsa bile min_green kadar yesil verilir — aksi halde
    arac yokken bile cevrim cok hizli doner ve overhead artar.
    """
    raw = queue_length * _GREEN_PER_VEHICLE_S
    return float(min(cfg.adaptive_max_green_s,
                     max(cfg.adaptive_min_green_s, raw)))


def adaptive_controller(
    env: "simpy.Environment",
    intersection: "Intersection",
) -> "Generator[simpy.events.Event, None, None]":
    """En uzun kuyruga oncelik veren dinamik kontrolcu.

    Her yesil periyodunda:
        1. Tum yonleri tara, en uzun kuyruga sahip olani sec.
        2. Yesil suresini o anki kuyruk uzunluguna gore hesapla
           (min_green / max_green sinirlari ile).
        3. YESIL -> SARI -> KIRMIZI faz dongusunu uygula.
    """
    cfg = intersection.config.signal

    while True:
        # 1. Yon secimi
        target = _pick_direction(intersection)
        queue = intersection.queue_length(target)

        # 2. Yesil suresi
        green_duration = _green_duration_for(queue, cfg)

        # 3. YESIL FAZI
        intersection.set_signal(target, LightState.GREEN)
        intersection.metrics.record_green_phase()
        green_end = env.now + green_duration
        yield from cross_during_green(env, intersection, target, green_end)

        # 4. SARI FAZI
        intersection.set_signal(target, LightState.YELLOW)
        yield env.timeout(cfg.yellow_duration_s)

        # 5. TUM-KIRMIZI BUFFER
        intersection.set_signal(target, LightState.RED)
        yield env.timeout(cfg.all_red_buffer_s)
