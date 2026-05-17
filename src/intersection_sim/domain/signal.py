"""Trafik isigi durumlari ve sinyal sure parametreleri.

LightState: bir yondeki isigin uc olasi rengini gosteren basit enum.

SignalConfig: tum kontrolculerin paylastigi sure parametrelerini tutar.
Sabit-zamanli kontrolcu sadece green_duration_s'i kullanir; adaptif
kontrolcu adaptive_min_green_s ve adaptive_max_green_s sinirlariyla
oynar. Tum kontrolculer sari, all-red buffer ve crossing_time_s
degerlerini ayni kullanir — bunlar fiziksel guvenlik parametreleridir.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class LightState(str, Enum):
    """Bir yondeki isigin gosterdigi renk."""

    GREEN = "green"    # Yesil — gecmeye izin var
    YELLOW = "yellow"  # Sari — gecisi tamamla, yenisini baslatma
    RED = "red"        # Kirmizi — durmak zorunlu


class SignalConfig(BaseModel):
    """Tum kontrolculerin paylastigi sure parametreleri (saniye)."""

    model_config = ConfigDict(frozen=True)

    # ---- temel faz sureleri ----------------------------------------------
    green_duration_s: float = Field(
        default=30.0, gt=0.0,
        description="Sabit-zamanli kontrolcude bir yonun yesil suresi",
    )
    yellow_duration_s: float = Field(
        default=3.0, gt=0.0,
        description="Yesilden kirmiziya gecerken sari faz suresi",
    )
    all_red_buffer_s: float = Field(
        default=1.0, ge=0.0,
        description="Bir yon kirmizi olduktan sonra digerine yesil verilene"
        " kadar gecen guvenlik buffer'i — tum yonler kirmizi",
    )
    crossing_time_s: float = Field(
        default=2.0, gt=0.0,
        description="Bir aracin yesilde kavsagi gecmesi icin gereken sure",
    )

    # ---- adaptif kontrolcunun siniri (Faz 2'de kullanilacak) ------------
    adaptive_min_green_s: float = Field(
        default=15.0, gt=0.0,
        description="Adaptif yesilin alt siniri — cok kisa yesiller engellenir",
    )
    adaptive_max_green_s: float = Field(
        default=60.0, gt=0.0,
        description="Adaptif yesilin ust siniri — bir yon ne kadar dolu olursa"
        " olsun bu sureyi asmaz, digerlerine de hak verir",
    )

    @property
    def fixed_cycle_duration_s(self) -> float:
        """Sabit-zamanli kontrolcunun tek tam cevriminin uzunlugu.

        Hesap: 4 yon * (yesil + sari + buffer). Default degerlerle
        4 * (30 + 3 + 1) = 136 saniye.
        """
        return 4.0 * (self.green_duration_s + self.yellow_duration_s + self.all_red_buffer_s)
