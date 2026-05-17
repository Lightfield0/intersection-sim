"""Yon bazli, saate gore degisken Poisson arac uretici.

Her yon icin AYRI bir SimPy sureci calisir. Bu surec sonsuz dongude:
    1. O an sim-saatine bakar, ilgili yonun arac/dakika hizini cikarir.
    2. Hizdan ortalamayla ustel inter-arrival ornekler.
    3. O kadar bekler.
    4. Yeni bir Vehicle olusturur (acil mi normal mi rastgele) ve
       kavsak kuyruguna koyar.

Acil arac olasiligi config.arrivals.emergency_probability (default %5).

Tum yonler ayni RNG'yi paylasir — boylece tek seed butun urettiklerini
deterministik kilar.
"""

from typing import TYPE_CHECKING

import numpy as np

from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.vehicle import Vehicle, VehicleType

if TYPE_CHECKING:
    from collections.abc import Generator

    import simpy

    from intersection_sim.simulation.intersection import Intersection


def start_vehicle_generators(
    env: "simpy.Environment",
    intersection: "Intersection",
    rng: np.random.Generator,
) -> None:
    """Her yon icin bir Poisson sureci baslatir. Bu fonksiyon kendisi
    surec degil — sadece 4 surec yaratir ve geri doner.
    """
    # next_id: tum yonler arasinda paylasilan sayac.
    # Listeye sarip nonlocal yerine mutable referans veriyoruz —
    # closure tarafindan paylasilan int'i incrementlemek icin tipik kalip.
    next_id = [0]

    for direction in ALL_DIRECTIONS:
        env.process(_arrival_loop(env, intersection, rng, direction, next_id))


def _arrival_loop(
    env: "simpy.Environment",
    intersection: "Intersection",
    rng: np.random.Generator,
    direction: Direction,
    next_id: list[int],  # tek-elemanli mutable sayac
) -> "Generator[simpy.events.Event, None, None]":
    """Tek bir yonun arac uretim dongusu.

    Cikis kosulu: horizon (`config.horizon_seconds`) gectikten sonra
    yeni arac uretmiyoruz. Dongu return ile sonlanir.
    """
    config = intersection.config

    while True:
        # ---- bir sonraki gelisin zamani ---------------------------------
        rate_per_min = config.arrivals.rate_for(direction, env.now)
        # Hiz arac/dakika; bunu saniye-cinsi ortalama-bekleme'ye cevirmek
        # icin once arac/saniyeye, sonra 1/hiz al.
        mean_gap_s = 60.0 / rate_per_min
        gap = float(rng.exponential(mean_gap_s))
        yield env.timeout(gap)

        # Simulasyon suresi bittiyse cikabiliriz.
        if env.now >= config.horizon_seconds:
            return

        # ---- yeni araci olustur -----------------------------------------
        # Acil arac mi? Bernoulli ornek.
        is_emergency = bool(rng.random() < config.arrivals.emergency_probability)
        vtype = VehicleType.EMERGENCY if is_emergency else VehicleType.NORMAL

        vehicle = Vehicle(
            vehicle_id=next_id[0],
            direction=direction,
            vehicle_type=vtype,
            arrival_time=float(env.now),
        )
        next_id[0] += 1

        # Kuyruga ekle. Store.put() event'tir; yield ile bekliyoruz
        # (sinirsiz kapasiteli store oldugu icin aninda tamamlanir).
        yield intersection.enqueue(vehicle)
