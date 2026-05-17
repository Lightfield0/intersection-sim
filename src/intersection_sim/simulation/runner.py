"""Simulasyon orkestratoru — SimPy ortamini kurar, sürec­leri başlatır, koşturur.

Kullanim sekli:

    from intersection_sim.controllers.fixed import fixed_controller
    from intersection_sim.domain.config import SimConfig
    from intersection_sim.simulation.runner import run_with_controller

    intersection = run_with_controller(SimConfig(), fixed_controller)

Adaptif veya preemptive kontrolculer eklenince sadece ikinci argümani
degistirip ayni runner kullanilir.

Faz 2'de eklendi: periyodik snapshot loop. Her ``SNAPSHOT_INTERVAL_S``
saniyede bir kavsagin durumunu (kuyruk uzunluklari + aktif yesil) yakalar
ve MetricsCollector'a kaydeder. Bu zaman serileri sunum grafiklerinde
ve KPI hesaplamalarinda kullanilir.
"""

from collections.abc import Generator
from typing import Any, Callable

import numpy as np
import simpy

from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import ALL_DIRECTIONS
from intersection_sim.metrics.metrics_collector import (
    SNAPSHOT_INTERVAL_S,
    MetricsSnapshot,
)
from intersection_sim.simulation.arrivals import start_vehicle_generators
from intersection_sim.simulation.intersection import Intersection

ControllerFn = Callable[
    [simpy.Environment, Intersection],
    Generator[simpy.events.Event, Any, None],
]


def _snapshot_loop(
    env: simpy.Environment,
    intersection: Intersection,
    interval_s: float,
) -> Generator[simpy.events.Event, None, None]:
    """Periyodik olarak kavsagin durumunu MetricsCollector'a yazar."""
    while True:
        snap = MetricsSnapshot(
            sim_time_s=float(env.now),
            queue_lengths={d: intersection.queue_length(d) for d in ALL_DIRECTIONS},
            active_green=intersection.active_green(),
        )
        intersection.metrics.record_snapshot(snap)
        yield env.timeout(interval_s)


def run_with_controller(
    config: SimConfig,
    controller: ControllerFn,
    *,
    snapshot_interval_s: float = SNAPSHOT_INTERVAL_S,
) -> Intersection:
    """Verilen konfig ve kontrolcu ile bir simulasyon kosumu calistirir.

    Adimlar:
        1. SimPy environment olustur, seedli numpy RNG yarat.
        2. Intersection kur (4 kuyruk + 4 sinyal RED ile + Metrics).
        3. Kontrolcu surecini baslat.
        4. Periyodik snapshot surecini baslat.
        5. Her yon icin Poisson arac uretici suresi baslat.
        6. env.run(until=horizon) ile koştur.
        7. Doldurulmus Intersection nesnesini geri don.
    """
    env = simpy.Environment()
    rng = np.random.default_rng(config.seed)

    intersection = Intersection(env, config)

    env.process(controller(env, intersection))
    env.process(_snapshot_loop(env, intersection, snapshot_interval_s))
    start_vehicle_generators(env, intersection, rng)

    env.run(until=config.horizon_seconds)
    return intersection
