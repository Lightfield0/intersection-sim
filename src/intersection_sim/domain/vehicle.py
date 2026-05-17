"""Arac domain modeli.

Bir arac ilk uretildigi anda yaratilir. arrival_time o anki sim-saatidir.
Daha sonra kavsaga geldiginde kuyruga eklenir; yesil isikta sirasi gelince
gecis baslar (cross_start_time) ve crossing_time_s sonra biter
(cross_end_time).

wait_time bu iki zamandan turetilir: kavsaga varistan gecise baslamaya
kadar gecen sure. KPI hesaplarken bu deger kullanilir.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from intersection_sim.domain.direction import Direction


class VehicleType(str, Enum):
    """Bir aracin sokakta hangi rolu oynadigini soyler.

    Acil araclar (ambulans, itfaiye, polis) Faz 3'te eklenecek olan
    preemptive kontrolcu tarafindan ozel muamele gorur — kavsaktaki
    yesil isik onlarin yonune dogru anlik olarak donulur.
    """

    NORMAL = "normal"        # Sira disi bir ozelligi olmayan binek arac
    EMERGENCY = "emergency"  # Ambulans / itfaiye / polis aracligi


class Vehicle(BaseModel):
    """Kavsaktan gecen bir aracin tum olay damgalarini tutar.

    Tum zaman alanlari simulasyon saniyesi cinsindendir
    (``simpy.Environment.now`` degerleri). Henuz yasanmamis bir olayin
    zaman damgasi ``None`` kalir — ornegin yesil bekleyen bir arac icin
    cross_start_time hala ``None``'dir.
    """

    model_config = ConfigDict(frozen=False)

    vehicle_id: int = Field(ge=0, description="Sirasiyla artan benzersiz ID")
    direction: Direction = Field(description="Aracin geldigi yon")
    vehicle_type: VehicleType = Field(
        default=VehicleType.NORMAL,
        description="Normal mi yoksa acil arac mi",
    )

    arrival_time: float = Field(
        ge=0.0,
        description="Kavsaga varis zamani (sn)",
    )
    cross_start_time: Optional[float] = Field(
        default=None,
        description="Gecise basladigi zaman; yesil isik geldiginde dolar",
    )
    cross_end_time: Optional[float] = Field(
        default=None,
        description="Karsiya gectigi an; cross_start + crossing_time_s",
    )

    # ---- turevsel ozellikler ----------------------------------------------

    @property
    def is_emergency(self) -> bool:
        """Bu arac acil arac mi?"""
        return self.vehicle_type is VehicleType.EMERGENCY

    @property
    def wait_time(self) -> Optional[float]:
        """Variştan gecise baslayana kadar gecen sure (sn).

        Hala bekleyen veya gecememis araclar icin ``None`` doner.
        """
        if self.cross_start_time is None:
            return None
        return self.cross_start_time - self.arrival_time

    @property
    def total_time_in_system(self) -> Optional[float]:
        """Variştan gecisin bitisine kadar gecen toplam sure (sn)."""
        if self.cross_end_time is None:
            return None
        return self.cross_end_time - self.arrival_time
