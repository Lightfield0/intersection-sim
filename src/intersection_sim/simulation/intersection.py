"""Kavsagin merkez nesnesi: 4 yonun kuyruklari + sinyal durumlari.



Bu sinif simulasyondaki "ortak hafiza" gibi davranir:
  - Kontrolculer ``set_signal()`` ile yon isiklarini degistirir.
  - Arac uretici ``enqueue()`` ile gelen araci ilgili yon kuyruguna koyar.
  - Geçiş mantigi (``crossing.cross_during_green``) yesil yondeki
    kuyruktan araç ceker, gecirir, MetricsCollector'a kaydeder.

Tum metotlar saf python (SimPy event'i degil); ``enqueue`` SimPy Store
event'i dondurdugu icin caller'in onu yield etmesi gerekir.

Faz 2'de MetricsCollector eklendi: tum sinyal degisimleri ve gecmis
araclar artik bu collector'a yazilir. Eski ``signal_change_count`` ve
``crossed_vehicles`` ozellikleri Faz 1 testleri kirilmasin diye
collector'a proxy olarak korunur.
"""

from __future__ import annotations

import simpy

from intersection_sim.domain.config import SimConfig
from intersection_sim.domain.direction import ALL_DIRECTIONS, Direction
from intersection_sim.domain.signal import LightState
from intersection_sim.domain.vehicle import Vehicle
from intersection_sim.metrics.metrics_collector import MetricsCollector


class Intersection:
    """Dort yonlu kavsak — her yon icin ayri kuyruk ve sinyal durumu."""

    def __init__(self, env: simpy.Environment, config: SimConfig) -> None:
        self.env = env
        self.config = config

        # Her yone bir kuyruk. SimPy Store: FIFO, kapasitesi sinirsiz.
        # (Gercek dunyada yol uzar ama biz tasmayi modellemiyoruz.)
        self.queues: dict[Direction, simpy.Store] = {
            d: simpy.Store(env) for d in ALL_DIRECTIONS
        }

        # Baslangicta tum yonler kirmizi. Ilk kontrolcu tick'inde bir
        # yone yesil verilecek.
        self.signals: dict[Direction, LightState] = {
            d: LightState.RED for d in ALL_DIRECTIONS
        }

        # KPI toplayicisi — sinyal degisimleri ve arac olaylari buraya yazilir.
        self.metrics: MetricsCollector = MetricsCollector()

    # ---- sinyal kontrolu --------------------------------------------------

    def set_signal(self, direction: Direction, state: LightState) -> None:
        """Belirli yonun isigini istenen renge cevirir.

        Renk gerçekten degisirse MetricsCollector'a sinyal degisimi
        kaydedilir; ayni rengi bir kez daha "ayarlamak" sayaca dokunmaz.
        """
        if self.signals[direction] != state:
            self.metrics.record_signal_change()
        self.signals[direction] = state

    def active_green(self) -> Direction | None:
        """O an yesil olan yonu dondurur (yoksa None)."""
        for d in ALL_DIRECTIONS:
            if self.signals[d] is LightState.GREEN:
                return d
        return None

    # ---- kuyruk islemleri -------------------------------------------------

    def queue_length(self, direction: Direction) -> int:
        """Belirli yonun bekleyen arac sayisi."""
        return len(self.queues[direction].items)

    def enqueue(self, vehicle: Vehicle) -> simpy.events.Event:
        """Araci kendi yonune ekler. SimPy event dondurur — yield edin."""
        return self.queues[vehicle.direction].put(vehicle)

    # ---- ek faydalar ------------------------------------------------------

    @property
    def total_queue_length(self) -> int:
        """Tum yonlerdeki bekleyen araclarin toplami."""
        return sum(self.queue_length(d) for d in ALL_DIRECTIONS)

    # ---- geriye-uyumluluk proxy'leri (Faz 1 testleri icin) ---------------

    @property
    def crossed_vehicles(self) -> list[Vehicle]:
        """Faz 1 API'si — MetricsCollector listesine proxy."""
        return self.metrics.vehicles_served

    @property
    def crossed_count(self) -> int:
        """Kavsagi gecmis arac sayisi (KPI kisayolu)."""
        return len(self.metrics.vehicles_served)

    @property
    def signal_change_count(self) -> int:
        """Faz 1 API'si — MetricsCollector sayacina proxy."""
        return self.metrics.signal_change_count
