"""Sabit-zamanli (fixed-time) trafik isigi kontrolcusu.

En basit baseline: yesil isigi sirayla N -> E -> S -> W -> N ... yonlerine
verir. Her yon icin yesil suresi sabit (default 30 sn). Trafik
yogunluguna duyarsizdir — kuyruk uzun olsa da kisa olsa da ayni sureyi
verir.

Bir yon icin tam faz dongusu:
    1. YESIL (green_duration_s sn)     -> arac geçişi yapilir
    2. SARI (yellow_duration_s sn)     -> yeni arac alinmaz
    3. KIRMIZI BUFFER (all_red_buffer_s) -> tum yonler kirmizi, guvenlik

Yesil sirasinda arac gecirme mantigi ``simulation.crossing`` modulunde
paylasilan helper'a tasindi — adaptif kontrolcu de ayni helper'i kullaniyor.
"""

from typing import TYPE_CHECKING

from intersection_sim.domain.direction import ALL_DIRECTIONS
from intersection_sim.domain.signal import LightState
from intersection_sim.simulation.crossing import cross_during_green

if TYPE_CHECKING:
    from collections.abc import Generator

    import simpy

    from intersection_sim.simulation.intersection import Intersection


def fixed_controller(
    env: "simpy.Environment",
    intersection: "Intersection",
) -> "Generator[simpy.events.Event, None, None]":
    """Sirayla yesil veren ana SimPy kontrolcu surecidir.

    Calisma: sonsuz dongu icinde 4 yonu sirayla dolasir ve her yon icin
    GREEN -> YELLOW -> RED faz dongusunu uygular.
    """
    cfg = intersection.config.signal
    while True:
        for direction in ALL_DIRECTIONS:
            # ----- YESIL FAZI -------------------------------------------
            intersection.set_signal(direction, LightState.GREEN)
            intersection.metrics.record_green_phase()
            green_end = env.now + cfg.green_duration_s
            yield from cross_during_green(env, intersection, direction, green_end)

            # ----- SARI FAZI --------------------------------------------
            intersection.set_signal(direction, LightState.YELLOW)
            yield env.timeout(cfg.yellow_duration_s)

            # ----- TUM-KIRMIZI BUFFER -----------------------------------
            intersection.set_signal(direction, LightState.RED)
            yield env.timeout(cfg.all_red_buffer_s)
