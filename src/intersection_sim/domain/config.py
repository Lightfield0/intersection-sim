"""Ust duzey simulasyon konfigurasyonu.

ArrivalProfile: her yon icin saatlik arac/dakika hizini tasir; gun
icindeki yogun saatlerde (07-09 sabah, 17-19 aksam) hizlari arttirir.

SimConfig: tum konfigurasyonu tek bir nesnede toplar — simulasyon
suresi, seed, sinyal parametreleri, geliş hizlari. Senaryolar bu nesneyi
turetir (ornegin "adaptif kontrolcu icin SignalConfig'in ayni, sadece
controller secimi farkli" gibi).
"""


from pydantic import BaseModel, ConfigDict, Field, model_validator

from intersection_sim.domain.direction import Direction
from intersection_sim.domain.signal import SignalConfig

# Default geliş hizlari (arac / dakika).
# Bu degerler proje spesifikasyonundan geliyor.
_DEFAULT_BASE_RATES: dict[Direction, float] = {
    Direction.NORTH: 0.4,
    Direction.SOUTH: 0.4,
    Direction.EAST: 0.3,
    Direction.WEST: 0.3,
}

_DEFAULT_PEAK_RATES: dict[Direction, float] = {
    Direction.NORTH: 0.8,
    Direction.SOUTH: 0.7,
    Direction.EAST: 0.6,
    Direction.WEST: 0.6,
}


class ArrivalProfile(BaseModel):
    """Saatlik degiskenlik tasiyan, yon bazli Poisson hiz tablosu.

    Hizlar arac/dakika cinsinden tanimli; simulasyon icinde saniyeye
    cevrilirken 60'a bolunur (``mean_interarrival_s = 60 / rate``).
    """

    model_config = ConfigDict(frozen=True)

    base_rate_per_min: dict[Direction, float] = Field(
        default_factory=lambda: dict(_DEFAULT_BASE_RATES),
        description="Normal saatlerdeki yon basina arac/dakika hizi",
    )
    peak_rate_per_min: dict[Direction, float] = Field(
        default_factory=lambda: dict(_DEFAULT_PEAK_RATES),
        description="Yogun saatlerdeki yon basina arac/dakika hizi",
    )

    peak_morning: tuple[int, int] = Field(
        default=(7, 9),
        description="Sabah yogun saat araligi (baslangic dahil, bitis haric)",
    )
    peak_evening: tuple[int, int] = Field(
        default=(17, 19),
        description="Aksam yogun saat araligi (baslangic dahil, bitis haric)",
    )

    emergency_probability: float = Field(
        default=0.05, ge=0.0, le=1.0,
        description="Yeni uretilen bir aracin acil arac olma olasiligi",
    )

    @model_validator(mode="after")
    def _check_directions(self) -> "ArrivalProfile":
        """Iki hiz tablosu da tum 4 yonu kapsamali."""
        for table_name, table in (("base", self.base_rate_per_min),
                                  ("peak", self.peak_rate_per_min)):
            missing = set(Direction) - set(table.keys())
            if missing:
                raise ValueError(
                    f"{table_name}_rate_per_min eksik yonler iceriyor: {missing}"
                )
            for d, r in table.items():
                if r <= 0:
                    raise ValueError(f"{table_name}_rate_per_min[{d}] pozitif olmali")
        return self

    def rate_for(self, direction: Direction, sim_time_s: float) -> float:
        """Verilen sim-zamaninda belirli yonun anlik arac/dakika hizi.

        sim_time_s'den saat-of-day cikarilir (mod 24). Eger bu saat
        yogun aralikta ise peak tablo, aksi halde base tablo kullanilir.
        """
        hour_of_day = int((sim_time_s / 3600.0) % 24)
        in_morning = self.peak_morning[0] <= hour_of_day < self.peak_morning[1]
        in_evening = self.peak_evening[0] <= hour_of_day < self.peak_evening[1]
        if in_morning or in_evening:
            return self.peak_rate_per_min[direction]
        return self.base_rate_per_min[direction]


class SimConfig(BaseModel):
    """Bir simulasyon kosumunun tum girdileri."""

    model_config = ConfigDict(frozen=True)

    horizon_seconds: float = Field(
        default=14400.0, gt=0.0,
        description="Simulasyon suresi (sn). Default: 4 saat = 14400 sn",
    )
    seed: int = Field(
        default=42, ge=0,
        description="RNG seed'i. Ayni seed ayni KPI'lari uretir (reproducibility).",
    )
    signal: SignalConfig = Field(default_factory=SignalConfig)
    arrivals: ArrivalProfile = Field(default_factory=ArrivalProfile)
