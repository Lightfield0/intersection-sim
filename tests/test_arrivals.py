"""Poisson arac uretici testleri.

Iki sey kontrol ediyoruz:
1) Yogun saat normal saatten daha cok arac uretiyor mu? (orneklem
   uzun olmalı ki rastgele oynama yutulsun.)
2) Acil arac orani yaklasik %5 mi?
"""

from typing import TYPE_CHECKING

import numpy as np
import pytest
import simpy

from intersection_sim.domain.config import ArrivalProfile, SimConfig
from intersection_sim.domain.direction import Direction
from intersection_sim.domain.signal import SignalConfig
from intersection_sim.domain.vehicle import VehicleType
from intersection_sim.simulation.arrivals import start_vehicle_generators
from intersection_sim.simulation.intersection import Intersection

if TYPE_CHECKING:
    pass


def _collect_vehicles(seed: int, horizon_s: float) -> list:
    """Bir kosumda kuyruklara ekledigimiz tum araclari toplar.

    Burada sadece arrivals'i kosutuyoruz — kontrolcu yok. Yani
    kuyruklar bosalmaz, hepsi listeye yerlesir.
    """
    config = SimConfig(
        seed=seed, horizon_seconds=horizon_s,
        signal=SignalConfig(), arrivals=ArrivalProfile(),
    )
    env = simpy.Environment()
    rng = np.random.default_rng(seed)
    inter = Intersection(env, config)

    start_vehicle_generators(env, inter, rng)
    env.run(until=horizon_s)

    # Tum yon kuyruklarini tek listede topla.
    all_v = []
    for d in Direction:
        all_v.extend(inter.queues[d].items)
    return all_v


def test_peak_hour_produces_more_arrivals_than_normal_hour() -> None:
    """Sabah yogun saat (07-09) sakin saatlere gore daha cok arac uretmeli.

    Kosumu 10 saat boyunca yapiyoruz (0 ile 36000 sn arasi) — boylece
    07:00-09:00 yogun penceresi tam icinde. Her aracin arrival_time'i
    saate cevrilip uygun kovaya yazilir.
    """
    horizon = 10 * 3600.0  # 0..10 saat — peak penceresini icerir

    total_peak_arrivals = 0
    total_normal_arrivals = 0

    for seed in (1, 2, 3):
        vehicles = _collect_vehicles(seed=seed, horizon_s=horizon)
        for v in vehicles:
            hour = int((v.arrival_time / 3600.0) % 24)
            if 7 <= hour < 9:
                total_peak_arrivals += 1
            else:
                total_normal_arrivals += 1

    # 3 seed * 2 saat yogun = 6 saat-orneklemi
    # 3 seed * 8 saat sakin = 24 saat-orneklemi
    peak_per_hour = total_peak_arrivals / (3 * 2.0)
    normal_per_hour = total_normal_arrivals / (3 * 8.0)

    assert peak_per_hour > normal_per_hour, (
        f"yogun saat sakin saatten daha az arac uretti: "
        f"peak={peak_per_hour:.1f}/h, normal={normal_per_hour:.1f}/h"
    )


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_emergency_share_is_around_five_percent(seed: int) -> None:
    """Tek seed'de bile %5'e yakin (±%4 tolerans) acil arac orani gormeliyiz."""
    horizon = 8 * 3600.0  # 8 saatlik kosum — yeterli orneklem
    vehicles = _collect_vehicles(seed=seed, horizon_s=horizon)
    assert len(vehicles) > 100, f"orneklem cok kucuk: {len(vehicles)}"

    emergencies = sum(1 for v in vehicles if v.vehicle_type is VehicleType.EMERGENCY)
    share = emergencies / len(vehicles)

    # Beklenen %5, %1 - %9 araligi makul.
    assert 0.01 < share < 0.09, f"acil arac orani sira disi: {share:.2%}"


def test_each_direction_gets_some_arrivals() -> None:
    """4 yonun her birine en az birkac arac gelmis olmali."""
    vehicles = _collect_vehicles(seed=42, horizon_s=4 * 3600.0)
    counts = {d: 0 for d in Direction}
    for v in vehicles:
        counts[v.direction] += 1
    for d, n in counts.items():
        assert n > 5, f"{d.display_name_tr} yonune sadece {n} arac geldi"
