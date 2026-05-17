"""Yesil isikta arac gecirme dongusu — paylasilan yardimci.

Hem sabit-zamanli hem adaptif kontrolcu bu fonksiyonu cagirir. Boylece
"yesil ne kadar sursun?" karari kontrolculere kalir; "yesil suresi
boyunca kuyruktan araclari sirayla gecir" mantigi tek yerde durur.

Polling pattern: kuyruk bossa kisa bir bekleme (probe_s) ile yeniden
bak. SimPy'nin Store.get + interrupt kombinasyonundan daha az hataya
acik — Nihal'in anlamasi kolay olsun diye.
"""

from typing import TYPE_CHECKING, cast

from intersection_sim.domain.direction import Direction
from intersection_sim.domain.vehicle import Vehicle

if TYPE_CHECKING:
    from collections.abc import Generator

    import simpy

    from intersection_sim.simulation.intersection import Intersection


# Bos kuyrukta yeniden bakma araligi (sn). Cok kucuk: arac gelir gelmez
# yakalanir. Cok buyuk: yesil suresinin sonunda ic araclar kacirilabilir.
_PROBE_S: float = 0.5


def cross_during_green(
    env: "simpy.Environment",
    intersection: "Intersection",
    direction: Direction,
    green_end: float,
) -> "Generator[simpy.events.Event, None, None]":
    """``green_end`` zamanina kadar ``direction`` yonunden arac gecirir.

    Calisma:
        - Yesil bitmeden once ``crossing_time_s`` saniyeden az kalmissa
          yeni gecisi baslatmiyoruz (arac sariya tasmamali).
        - Kuyruk bos ise kisa bir polling araligiyla yeniden bakiyoruz.
        - Bir arac alindiginda ``cross_start_time`` ve ``cross_end_time``
          damgalanir, MetricsCollector'a kaydedilir.
    """
    cfg = intersection.config.signal

    while True:
        remaining = green_end - env.now
        # Yeni bir gecisi tamamlamaya yetecek sure var mi?
        if remaining < cfg.crossing_time_s:
            if remaining > 0:
                yield env.timeout(remaining)
            return

        # Kuyruk bossa kisaca bekle ve tekrar bak
        if intersection.queue_length(direction) == 0:
            sleep = min(_PROBE_S, remaining)
            yield env.timeout(sleep)
            continue

        # Bir arac al, geciris bitimini damgala, metrige yaz
        vehicle = cast(Vehicle, (yield intersection.queues[direction].get()))
        vehicle.cross_start_time = env.now
        yield env.timeout(cfg.crossing_time_s)
        vehicle.cross_end_time = env.now
        intersection.metrics.record_vehicle_served(vehicle)
