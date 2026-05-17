"""Acil arac preemption mekanik testi.

Senaryo: Kuzey yesil iken doguya bir acil arac geliyor. Kontrolcu kisa
sure icinde mevcut yesili kapatip doguya yesil vermeli; ``preemption_count``
en az 1 olmali.

Polling-bazli detection icin biraz tolerans gerekli (yesil kapanmasi
5 sn buffer + sari 3 sn + buffer 1 sn = ~9 sn).
"""

from typing import TYPE_CHECKING

import simpy

from intersection_sim.controllers.preemptive import preemptive_controller
from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import Direction
from intersection_sim.domain.signal import LightState, SignalConfig
from intersection_sim.domain.vehicle import Vehicle, VehicleType
from intersection_sim.simulation.intersection import Intersection

if TYPE_CHECKING:
    from collections.abc import Generator


def _enqueue(inter: Intersection, direction: Direction, vehicle: Vehicle) -> None:
    """Test araci kuyruga ekle (env.run icinde olmadigimiz icin items.append)."""
    inter.queues[direction].items.append(vehicle)


def test_preemption_swaps_green_to_emergency_direction() -> None:
    """N yesil olmaya basladiktan sonra E'ye acil arac gelirse, kontrolcu
    kisa sure icinde E'yi yesil yapmali."""
    config = SimConfig(
        seed=0, horizon_seconds=200.0,
        signal=SignalConfig(adaptive_max_green_s=60.0),
    )
    env = simpy.Environment()
    inter = Intersection(env, config)

    # Baslangic: N kuyrugunda 10 normal arac (yesil onunda olsun)
    for i in range(10):
        _enqueue(inter, Direction.NORTH,
                 Vehicle(vehicle_id=i, direction=Direction.NORTH, arrival_time=0.0))

    # Ilerleyen zamanda E'ye bir acil arac enjekte et.
    def _inject_emergency() -> "Generator[simpy.events.Event, None, None]":
        # 8 sn bekle — N yesil oturmus oluyor
        yield env.timeout(8.0)
        _enqueue(inter, Direction.EAST, Vehicle(
            vehicle_id=999, direction=Direction.EAST,
            vehicle_type=VehicleType.EMERGENCY, arrival_time=env.now,
        ))

    # E yesil olmaya basladigi ilk zamani yakala
    east_green_at: dict[str, float] = {}

    def _watch_east_green() -> "Generator[simpy.events.Event, None, None]":
        while True:
            if inter.signals[Direction.EAST] is LightState.GREEN and "t" not in east_green_at:
                east_green_at["t"] = env.now
                return
            yield env.timeout(0.5)

    env.process(preemptive_controller(env, inter))
    env.process(_inject_emergency())
    env.process(_watch_east_green())
    env.run(until=60.0)

    assert "t" in east_green_at, "E yonu hic yesil olmadi"
    # E acil arac 8 sn'de geldi. Preempt 5 sn + sari 3 sn + buffer 1 sn = 9 sn
    # Yani E yesili en gec ~17 sn'de baslamali.
    # Yine de polling toleransi icin 25 sn'ye kadar acelle kabul edilir.
    assert east_green_at["t"] < 25.0, (
        f"E yesili cok gec geldi: t={east_green_at['t']:.1f}s "
        f"(acil arac 8 sn'de geldi)"
    )

    # En az bir preemption tetiklenmis olmali
    assert inter.metrics.preemption_count >= 1, (
        f"preemption_count={inter.metrics.preemption_count} — beklenen >= 1"
    )


def test_preemption_does_not_trigger_when_emergency_in_active_green_direction() -> None:
    """Eger acil arac mevcut yesil yondeyse preemption tetiklenmemeli —
    o arac zaten gececek."""
    config = SimConfig(seed=0, horizon_seconds=60.0, signal=SignalConfig())
    env = simpy.Environment()
    inter = Intersection(env, config)

    # N kuyrugunda 2 normal arac, bir de acil arac
    for i in range(2):
        _enqueue(inter, Direction.NORTH,
                 Vehicle(vehicle_id=i, direction=Direction.NORTH, arrival_time=0.0))
    _enqueue(inter, Direction.NORTH, Vehicle(
        vehicle_id=99, direction=Direction.NORTH,
        vehicle_type=VehicleType.EMERGENCY, arrival_time=0.0,
    ))

    env.process(preemptive_controller(env, inter))
    env.run(until=20.0)

    # Acil arac N'de, yesil yine N'e gitmis olmali → preempt tetiklenmemeli
    assert inter.metrics.preemption_count == 0, (
        f"preemption gereksiz yere tetiklendi: count={inter.metrics.preemption_count}"
    )
