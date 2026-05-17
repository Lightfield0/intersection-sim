"""Acil arac preemption'li trafik isigi kontrolcusu.

Bu kontrolcu adaptif kontrolcunun uzerine bir kural daha ekler:

  - **Normal durum:** Adaptif kontrolcu ile aynı — en uzun kuyruga
    yesil, queue*3 sn ile orantili sure.

  - **Acil durum:** Kuyrugunda acil arac bekleyen bir yon varsa ve o
    yon su an yesil DEGILSE, mevcut yesil hizla kapatilir. 5 sn'lik
    kapanma penceresi (sari + tepki suresi icin guvenlik) sonra acil
    yon icin sabit 15 sn yesil pencere acilir. Sonra normal adaptif
    moda donulur.

Bu wrapper pattern adaptive.py'daki ``_pick_direction`` ve
``_green_duration_for`` yardimcilarini yeniden kullanir — adaptif
kontrolcuyu yeniden yazmiyoruz, sadece etrafina "acil arac varsa
preempt et" kontrolu ekliyoruz.

Yesil sirasinda baska yonde acil arac belirirse, polling sirasinda
algilanir ve mevcut yesil ``_PREEMPT_CLOSE_S = 5`` saniyeye sikistirilir.
Bu MetricsCollector'da ``preemption_count`` olarak sayilir.
"""

from typing import TYPE_CHECKING, Optional, cast

from intersection_sim.controllers.adaptive import _green_duration_for, _pick_direction
from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState
from intersection_sim.domain.vehicle import Vehicle

if TYPE_CHECKING:
    from collections.abc import Generator

    import simpy

    from intersection_sim.simulation.intersection import Intersection


# Acil arac geldiginde mevcut yesilin kapatilma suresi.
# Buradaki 5 sn sari + insanin tepki suresi icin guvenlik buffer'i —
# gercek hayatta isigi anlik kapatamayiz.
_PREEMPT_CLOSE_S: float = 5.0

# Acil aracin yonune verilecek sabit yesil suresi.
# Adaptif sureye bagli degil — acil arac mutlaka gecsin diye sabit.
_EMERGENCY_GREEN_S: float = 15.0

# Polling araligi (sn) — yesil sirasinda acil arac kontrolu burada yapilir.
_PROBE_S: float = 0.5


def _direction_with_waiting_emergency(
    intersection: "Intersection",
    skip: Optional[Direction] = None,
) -> Optional[Direction]:
    """Kuyrugunda en az bir acil arac bekleyen ilk yonu dondurur.

    ``skip`` verilirse o yonu (genellikle su anki yesil) atlar — boylece
    "baska yonde acil var mi?" sorusu sorulabilir.
    """
    for d in ALL_DIRECTIONS:
        if d is skip:
            continue
        for v in intersection.queues[d].items:
            if v.is_emergency:
                return d
    return None


def preemptive_controller(
    env: "simpy.Environment",
    intersection: "Intersection",
) -> "Generator[simpy.events.Event, None, None]":
    """Adaptif + acil arac preemption'li kontrolcu."""
    cfg = intersection.config.signal

    while True:
        # 1. ACIL DURUM ONCELIK: kuyrukta acil arac varsa o yone yesil.
        emergency_dir = _direction_with_waiting_emergency(intersection)
        if emergency_dir is not None:
            yield from _emergency_green_window(env, intersection, emergency_dir)
            continue

        # 2. NORMAL ADAPTIF: en uzun kuyruga yesil, queue*3 sn.
        target = _pick_direction(intersection)
        green_duration = _green_duration_for(
            intersection.queue_length(target), cfg,
        )

        intersection.set_signal(target, LightState.GREEN)
        intersection.metrics.record_green_phase()
        green_end = env.now + green_duration

        yield from _cross_with_preempt_watch(env, intersection, target, green_end)

        # 3. SARI + KIRMIZI FAZLARI (her kontrolcude ayni)
        intersection.set_signal(target, LightState.YELLOW)
        yield env.timeout(cfg.yellow_duration_s)
        intersection.set_signal(target, LightState.RED)
        yield env.timeout(cfg.all_red_buffer_s)


def _emergency_green_window(
    env: "simpy.Environment",
    intersection: "Intersection",
    direction: Direction,
) -> "Generator[simpy.events.Event, None, None]":
    """Acil aracin yonune sabit 15 sn yesil ver.

    Bu pencere icinde preempt kontrolu yapilmaz — acil yonu kestirip
    baska bir acil yone gecmeye calismayiz. (Pratikte ardisik acil arac
    cok seyrek.)
    """
    cfg = intersection.config.signal
    intersection.set_signal(direction, LightState.GREEN)
    intersection.metrics.record_green_phase()
    green_end = env.now + _EMERGENCY_GREEN_S

    # Bu pencere icinde standart polling-based crossing kullaniyoruz.
    # cross_during_green helper'i yeterli — sadece preempt kontrolu yok.
    while True:
        remaining = green_end - env.now
        if remaining < cfg.crossing_time_s:
            if remaining > 0:
                yield env.timeout(remaining)
            break
        if intersection.queue_length(direction) == 0:
            yield env.timeout(min(_PROBE_S, remaining))
            continue
        vehicle = cast(Vehicle, (yield intersection.queues[direction].get()))
        vehicle.cross_start_time = env.now
        yield env.timeout(cfg.crossing_time_s)
        vehicle.cross_end_time = env.now
        intersection.metrics.record_vehicle_served(vehicle)

    # Sari + kirmizi
    intersection.set_signal(direction, LightState.YELLOW)
    yield env.timeout(cfg.yellow_duration_s)
    intersection.set_signal(direction, LightState.RED)
    yield env.timeout(cfg.all_red_buffer_s)


def _cross_with_preempt_watch(
    env: "simpy.Environment",
    intersection: "Intersection",
    direction: Direction,
    green_end: float,
) -> "Generator[simpy.events.Event, None, None]":
    """Yesil sirasinda hem arac gecirir hem baska yonde acil arac kontrol eder.

    Eger baska bir yonde acil arac bekliyor ve mevcut yesilden 5 sn'den
    fazla kaldiysa, yesili 5 sn'ye sikistir — bu MetricsCollector'da
    preemption olarak kaydedilir.
    """
    cfg = intersection.config.signal
    preempted = False  # ayni yesilde birden cok kez sayma

    while True:
        remaining = green_end - env.now

        # PREEMPT KONTROLU: baska yonde acil arac bekliyor mu?
        if not preempted:
            other_emergency = _direction_with_waiting_emergency(
                intersection, skip=direction,
            )
            if other_emergency is not None and remaining > _PREEMPT_CLOSE_S:
                # Yesili kis — kalan sure 5 sn'ye sabitle.
                green_end = env.now + _PREEMPT_CLOSE_S
                intersection.metrics.record_preemption()
                preempted = True
                remaining = _PREEMPT_CLOSE_S

        if remaining < cfg.crossing_time_s:
            if remaining > 0:
                yield env.timeout(remaining)
            return

        if intersection.queue_length(direction) == 0:
            yield env.timeout(min(_PROBE_S, remaining))
            continue

        # Bir arac al ve gecir
        vehicle = cast(Vehicle, (yield intersection.queues[direction].get()))
        vehicle.cross_start_time = env.now
        yield env.timeout(cfg.crossing_time_s)
        vehicle.cross_end_time = env.now
        intersection.metrics.record_vehicle_served(vehicle)
