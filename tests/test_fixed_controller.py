"""Sabit-zamanli kontrolcunun temel davranis testleri.

- Sirayla N -> E -> S -> W yonune yesil veriyor mu?
- Bir tam cevrim 136 saniye suruyor mu?
- Sinyal degisimleri beklendigi kadar oluyor mu?
"""

from typing import TYPE_CHECKING

import simpy

from intersection_sim.controllers.fixed import fixed_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState, SignalConfig
from intersection_sim.simulation.intersection import Intersection

if TYPE_CHECKING:
    from collections.abc import Generator


def _build_intersection(seed: int = 0) -> Intersection:
    """Bir kontrolcuyu izole kosturmak icin test fixture'i."""
    config = SimConfig(seed=seed, horizon_seconds=200.0, signal=SignalConfig())
    env = simpy.Environment()
    return Intersection(env, config)


def test_fixed_controller_visits_directions_in_clockwise_order() -> None:
    """Yesil isigi sirayla N, E, S, W yonlerine vermeli."""
    inter = _build_intersection()
    env = inter.env

    green_log: list[tuple[float, Direction]] = []

    def _watch() -> "Generator[simpy.events.Event, None, None]":
        """Her tick'te yesil olan yonu kaydeden gozlemci surec."""
        last_green: Direction | None = None
        while True:
            current_green = next(
                (d for d in ALL_DIRECTIONS if inter.signals[d] is LightState.GREEN),
                None,
            )
            if current_green is not None and current_green is not last_green:
                green_log.append((env.now, current_green))
                last_green = current_green
            yield env.timeout(0.5)

    env.process(fixed_controller(env, inter))
    env.process(_watch())
    env.run(until=160.0)

    # Ilk 4 yesil periyodu sira ile gormeliyiz.
    seen = [d for _, d in green_log[:4]]
    assert seen == ALL_DIRECTIONS, f"sira hatali: {seen}"


def test_one_full_cycle_takes_136_seconds() -> None:
    """N'in ikinci kez yesil olmasi tam bir cevrim sonra (136 sn) olmali."""
    inter = _build_intersection()
    env = inter.env

    north_green_starts: list[float] = []

    def _watch_north() -> "Generator[simpy.events.Event, None, None]":
        last = LightState.RED
        while True:
            current = inter.signals[Direction.NORTH]
            if current is LightState.GREEN and last is not LightState.GREEN:
                north_green_starts.append(env.now)
            last = current
            yield env.timeout(0.1)

    env.process(fixed_controller(env, inter))
    env.process(_watch_north())
    env.run(until=300.0)

    # En az iki yesil baslangici gormeliyiz; iki yesil arasi tam 136 sn.
    assert len(north_green_starts) >= 2, north_green_starts
    cycle = north_green_starts[1] - north_green_starts[0]
    # Polling 0.1 sn'lik araliklarla; tolerans buna gore.
    assert abs(cycle - 136.0) < 0.2, f"cevrim suresi 136 sn olmali, oldu: {cycle}"


def test_signal_change_count_accumulates() -> None:
    """Her renk degisimi sayaca bir eklemeli (RED -> GREEN -> YELLOW -> RED ...)."""
    inter = _build_intersection()
    env = inter.env

    env.process(fixed_controller(env, inter))
    env.run(until=136.0)  # bir tam cevrim

    # Her yon icin 3 degisim: RED->GREEN, GREEN->YELLOW, YELLOW->RED
    # 4 yon * 3 = 12. Baslangic durumu RED oldugu icin ilk yon RED -> GREEN
    # geçişi de sayar.
    assert inter.signal_change_count >= 12, inter.signal_change_count
