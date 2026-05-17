"""Adaptif kontrolcunun yon secimi ve yesil suresi davranisi.

Iki temel test:
  1. En uzun kuyruga sahip yonu seciyor (longest-queue first).
  2. Yesil suresi min/max sinirlari icinde kaliyor.

Polling-bazli arac uretici yerine, testlerde kuyruklara dogrudan
arac enjekte edip kontrolcuyu izole olarak kosturuyoruz.
"""

from typing import TYPE_CHECKING

import simpy

from intersection_sim.controllers.adaptive import (
    _GREEN_PER_VEHICLE_S,
    _green_duration_for,
    _pick_direction,
    adaptive_controller,
)
from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import Direction
from intersection_sim.domain.signal import LightState, SignalConfig
from intersection_sim.domain.vehicle import Vehicle
from intersection_sim.simulation.intersection import Intersection

if TYPE_CHECKING:
    from collections.abc import Generator


def _enqueue_n(inter: Intersection, direction: Direction, n: int) -> None:
    """Belirli yon kuyruguna n adet test araci ekler."""
    for i in range(n):
        v = Vehicle(vehicle_id=1000 + i, direction=direction, arrival_time=0.0)
        # Test sirasinda env.run icinde olmadigimiz icin Store.put yield
        # gerekmez — items listesine dogrudan ekliyoruz.
        inter.queues[direction].items.append(v)


# ---- _pick_direction birim testi ------------------------------------------


def test_pick_direction_returns_longest_queue() -> None:
    """En cok arac olan yon secilmeli."""
    config = SimConfig(seed=0)
    env = simpy.Environment()
    inter = Intersection(env, config)

    _enqueue_n(inter, Direction.NORTH, 2)
    _enqueue_n(inter, Direction.EAST, 10)  # en uzun
    _enqueue_n(inter, Direction.SOUTH, 5)
    _enqueue_n(inter, Direction.WEST, 1)

    assert _pick_direction(inter) is Direction.EAST


def test_pick_direction_breaks_ties_in_canonical_order() -> None:
    """Esitlikte ALL_DIRECTIONS sirasina gore (N -> E -> S -> W) ilki secilmeli."""
    config = SimConfig(seed=0)
    env = simpy.Environment()
    inter = Intersection(env, config)

    _enqueue_n(inter, Direction.NORTH, 3)
    _enqueue_n(inter, Direction.EAST, 3)
    _enqueue_n(inter, Direction.SOUTH, 0)
    _enqueue_n(inter, Direction.WEST, 0)

    # N ve E esit; N once gelmeli.
    assert _pick_direction(inter) is Direction.NORTH


# ---- _green_duration_for birim testi --------------------------------------


def test_green_duration_clamped_to_min() -> None:
    """Bos kuyruk olsa bile en az min_green saniye yesil verilmeli."""
    cfg = SignalConfig(adaptive_min_green_s=15.0, adaptive_max_green_s=60.0)
    assert _green_duration_for(0, cfg) == 15.0
    # 4 arac * 3 = 12 sn — yine min'in altinda
    assert _green_duration_for(4, cfg) == 15.0


def test_green_duration_clamped_to_max() -> None:
    """Cok dolu kuyruk olsa bile en cok max_green saniye yesil verilmeli."""
    cfg = SignalConfig(adaptive_min_green_s=15.0, adaptive_max_green_s=60.0)
    # 50 arac * 3 = 150 sn ama tavan 60.
    assert _green_duration_for(50, cfg) == 60.0


def test_green_duration_scales_linearly_within_bounds() -> None:
    """Sinirlar arasinda queue * GREEN_PER_VEHICLE_S kullanilmali."""
    cfg = SignalConfig(adaptive_min_green_s=15.0, adaptive_max_green_s=60.0)
    # 10 arac * 3 sn = 30 sn — min ile max arasinda
    assert _green_duration_for(10, cfg) == 10 * _GREEN_PER_VEHICLE_S


# ---- entegrasyon: kontrolcu uzun kuyruga oncelik veriyor mu ---------------


def test_adaptive_picks_loaded_direction_first() -> None:
    """N kuyrugu dolu ise kontrolcu N'i ilk yesil olarak secmeli.

    Senaryo: hic arac uretici yok, sadece kontrolcu calisiyor; ama N'de
    once 12 arac, E/S/W'de hic arac yok. Kontrolcu hangi yonun
    once yesil oldugunu izleyen bir gozlemci ile dogruluyoruz.
    """
    config = SimConfig(seed=0, horizon_seconds=200.0, signal=SignalConfig())
    env = simpy.Environment()
    inter = Intersection(env, config)
    _enqueue_n(inter, Direction.NORTH, 12)

    first_green: dict[str, Direction] = {}

    def _watch() -> "Generator[simpy.events.Event, None, None]":
        while True:
            for d in Direction:
                if inter.signals[d] is LightState.GREEN and "dir" not in first_green:
                    first_green["dir"] = d
                    return
            yield env.timeout(0.5)

    env.process(adaptive_controller(env, inter))
    env.process(_watch())
    env.run(until=10.0)

    assert first_green.get("dir") is Direction.NORTH
