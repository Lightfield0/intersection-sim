"""Kavsaktaki dort yon — kuzey, guney, dogu, bati.

Direction'i str-tabanli Enum olarak tanimladik. Sebep: CSV ciktilarinda ve
log mesajlarinda "Direction.NORTH" yerine dogrudan "N" goruluyor. Bu hem
dosya boyutunu hem de okunabilirligi iyilestiriyor.

ALL_DIRECTIONS sabit liste — sabit-zamanli kontrolcunun rotasyon sirasi
buradan okunuyor: kuzey -> dogu -> guney -> bati. Bu sira saat yonunde
gidiyor (haritada bakildiginda).
"""

from enum import Enum


class Direction(str, Enum):
    """Bir aracin kavsaga hangi yonden geldigini soyler."""

    NORTH = "N"  # Kuzey
    SOUTH = "S"  # Guney
    EAST = "E"   # Dogu
    WEST = "W"   # Bati

    @property
    def display_name_tr(self) -> str:
        """Grafiklerde ve UI'da gosterilen Turkce ad."""
        names = {
            Direction.NORTH: "Kuzey",
            Direction.SOUTH: "Güney",
            Direction.EAST: "Doğu",
            Direction.WEST: "Batı",
        }
        return names[self]


# Sabit-zamanli kontrolcunun yesil isigi gezdirme sirasi.
# Saat yonunde: N -> E -> S -> W -> N -> ...
ALL_DIRECTIONS: list[Direction] = [
    Direction.NORTH,
    Direction.EAST,
    Direction.SOUTH,
    Direction.WEST,
]
