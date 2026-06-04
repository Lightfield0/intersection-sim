"""docs/presentation.pdf — 8 slayt, yeşil/turuncu palet, konuşma notları YOK.

Triage projesindeki lacivert/altin paletten farkli bir kimlik:
  - Ana renk: #1B4D3E (koyu yeşil)
  - Vurgu:    #FF6B35 (turuncu)
  - Yardımcı: #B91C1C (uyari), #166534 (basari), #6B7280 (gri)

Tüm sayfalar 16:9 (13.333 x 7.5 inch). Her sayfada:
  - Sol üst: başlık + 3pt turuncu alt cizgi
  - Sağ üst: "N / 8" sayfa numarası
  - Sol alt: footer "Nihal Kemer · Akıllı Kavşak Simülasyonu · 2026"
  - Konusma notlari SLAYT YUZEYINE BASILMIYOR (PDF temiz kalsin)

Konusma metni docs/sunum-notlari.md dosyasinda — Nihal telefonundan
veya ikinci ekrandan okuyacak.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

OUTPUT = Path("docs/presentation.pdf")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ---------- Palet ----------------------------------------------------------
TITLE_COLOR = "#1B4D3E"   # koyu yeşil — ana
ACCENT = "#FF6B35"        # turuncu — vurgu
WARNING = "#B91C1C"       # kırmızı — sorun/baseline
SUCCESS = "#166534"       # açık yeşil — basari/iyileşme
NEUTRAL = "#6B7280"       # gri
LIGHT_GRAY = "#F3F4F6"
BORDER = "#E5E7EB"
BODY = "#1F2937"
WHITE = "white"
BLUE = "#3B82F6"
CODE_BG = "#1F2937"
CODE_FG = "#E5E7EB"

# ---------- Layout sabitleri -----------------------------------------------
SLIDE_W = 13.333
SLIDE_H = 7.5
HEADER_Y = 0.85
ACCENT_LINE_Y = 1.05
ACCENT_LINE_H = 0.045
FOOTER_Y = 7.25
PAGE_NUM_X = 12.65
PAGE_NUM_Y = 0.55
N_SLIDES = 10
FOOTER_TEXT = "N. Kemer · M. F. Güneş · Akıllı Kavşak Simülasyonu · 2026"


# ---------- Yardimcilar ----------------------------------------------------


def _new_slide(page_num: int):
    fig = plt.figure(figsize=(SLIDE_W, SLIDE_H), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SLIDE_W)
    ax.set_ylim(0, SLIDE_H)
    ax.invert_yaxis()
    ax.set_axis_off()
    ax.text(
        PAGE_NUM_X, PAGE_NUM_Y, f"{page_num} / {N_SLIDES}",
        fontsize=9, color=NEUTRAL, ha="right", va="center",
    )
    ax.text(
        0.6, FOOTER_Y, FOOTER_TEXT,
        fontsize=8.5, color=NEUTRAL, ha="left", va="center",
    )
    return fig, ax


def _title(ax, text: str) -> None:
    ax.text(
        0.6, HEADER_Y, text,
        fontsize=24, color=TITLE_COLOR, fontweight="bold", va="center",
    )
    ax.add_patch(Rectangle(
        (0.6, ACCENT_LINE_Y), 2.0, ACCENT_LINE_H,
        facecolor=ACCENT, edgecolor="none",
    ))


def _bullets(ax, *, x: float, y: float, items: list[str],
             fontsize: int = 16, line_height: float = 0.55,
             color: str = BODY) -> None:
    for i, b in enumerate(items):
        ax.text(x, y + i * line_height, f"• {b}",
                fontsize=fontsize, color=color, va="top")


def _label_box(ax, *, x: float, y: float, w: float, h: float,
               text: str, bg: str, fontsize: int = 13,
               fg: str = WHITE) -> None:
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.1",
        facecolor=bg, edgecolor="none",
    ))
    ax.text(x + w / 2, y + h / 2, text,
            ha="center", va="center",
            fontsize=fontsize, color=fg, fontweight="bold")


def _kpi_card(ax, *, x: float, y: float, w: float, h: float,
              label: str, value: str, bg: str,
              sublabel: str | None = None) -> None:
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=bg, edgecolor="none",
    ))
    ax.text(x + w / 2, y + 0.28, label, ha="center", va="top",
            fontsize=11, color=WHITE)
    ax.text(x + w / 2, y + h / 2 + 0.15, value, ha="center", va="center",
            fontsize=26, color=WHITE, fontweight="bold")
    if sublabel:
        ax.text(x + w / 2, y + h - 0.18, sublabel,
                ha="center", va="bottom",
                fontsize=9, color=WHITE, alpha=0.85)


def _table(ax, *, left: float, top: float,
           col_widths: list[float], row_height: float,
           rows_data: list[list[str]],
           fontsize: int = 11,
           row_bg: dict[int, str] | None = None,
           row_fg: dict[int, str] | None = None,
           row_bold: set[int] | None = None,
           col_align: list[str] | None = None) -> None:
    row_bg = row_bg or {}
    row_fg = row_fg or {}
    row_bold = row_bold or set()
    col_align = col_align or ["left"] * len(col_widths)

    x_starts = [left]
    for w in col_widths[:-1]:
        x_starts.append(x_starts[-1] + w)
    total_w = sum(col_widths)

    for r, row in enumerate(rows_data):
        y = top + r * row_height
        is_header = r == 0
        bg = TITLE_COLOR if is_header else row_bg.get(
            r, LIGHT_GRAY if r % 2 == 0 else WHITE,
        )
        ax.add_patch(Rectangle(
            (left, y), total_w, row_height,
            facecolor=bg, edgecolor=BORDER, linewidth=0.6,
        ))
        for c, val in enumerate(row):
            align = col_align[c] if c < len(col_align) else "left"
            if align == "center":
                cx, ha = x_starts[c] + col_widths[c] / 2, "center"
            elif align == "right":
                cx, ha = x_starts[c] + col_widths[c] - 0.1, "right"
            else:
                cx, ha = x_starts[c] + 0.12, "left"
            color = WHITE if is_header else row_fg.get(r, BODY)
            weight = "bold" if is_header or r in row_bold else "normal"
            ax.text(cx, y + row_height / 2, val,
                    fontsize=fontsize, color=color, fontweight=weight,
                    va="center", ha=ha)


def _accent_callout(ax, *, x: float, y: float, w: float, h: float,
                    text: str, fontsize: int = 12,
                    bg: str = "#FFF1E6", bar_color: str = ACCENT) -> None:
    ax.add_patch(Rectangle((x, y), w, h, facecolor=bg, edgecolor="none"))
    ax.add_patch(Rectangle((x, y), 0.08, h,
                           facecolor=bar_color, edgecolor="none"))
    ax.text(x + 0.25, y + h / 2, text,
            fontsize=fontsize, color=BODY, va="center", ha="left")


def _image(ax, path: Path, *, x: float, y: float, w: float, h: float) -> None:
    if not path.exists():
        return
    img = mpimg.imread(path)
    ax.imshow(img, extent=(x, x + w, y + h, y), aspect="auto", zorder=1)


def _intersection_icon(ax, *, cx: float, cy: float, size: float = 1.6) -> None:
    """Küçük stilize 4-yollu kavşak ikonu (kapakta).

    4 dikdortgen yol + ortada kare kavşak + 4 koseye sinyal yuvarlagi.
    """
    road = NEUTRAL
    half = size
    arm_w = size / 3.2
    # Dikey yol
    ax.add_patch(Rectangle((cx - arm_w / 2, cy - half),
                            arm_w, 2 * half,
                            facecolor=road, edgecolor="none", alpha=0.7))
    # Yatay yol
    ax.add_patch(Rectangle((cx - half, cy - arm_w / 2),
                            2 * half, arm_w,
                            facecolor=road, edgecolor="none", alpha=0.7))
    # Kavşak ortası
    ax.add_patch(Rectangle(
        (cx - arm_w / 2, cy - arm_w / 2), arm_w, arm_w,
        facecolor=TITLE_COLOR, edgecolor="white", linewidth=1.5,
    ))
    # Sinyal yuvarlaklari (4 ana yön)
    sig_dist = arm_w * 1.5
    sig_r = arm_w / 5.5
    for (sx, sy, col) in [
        (cx + sig_dist, cy + sig_dist / 3, SUCCESS),   # KD: yeşil (aktif)
        (cx - sig_dist, cy + sig_dist / 3, WARNING),
        (cx - sig_dist, cy - sig_dist / 3, WARNING),
        (cx + sig_dist, cy - sig_dist / 3, WARNING),
    ]:
        ax.add_patch(Circle((sx, sy), sig_r,
                            facecolor=col, edgecolor=BODY, linewidth=0.8))


# ---------- Slayt 1: Kapak --------------------------------------------------


def slide_01_cover(pdf: PdfPages) -> None:
    fig, ax = _new_slide(1)

    # Sol band — koyu yeşil
    ax.add_patch(Rectangle((0, 0), 0.4, SLIDE_H,
                           facecolor=TITLE_COLOR, edgecolor="none"))

    # Sol: başlık
    ax.text(0.9, 2.6, "Akıllı Kavşak", fontsize=42,
            color=TITLE_COLOR, fontweight="bold", va="center")
    ax.text(0.9, 3.5, "Trafik Işığı Simülasyonu", fontsize=42,
            color=TITLE_COLOR, fontweight="bold", va="center")
    ax.add_patch(Rectangle((0.9, 4.0), 2.5, ACCENT_LINE_H,
                           facecolor=ACCENT, edgecolor="none"))
    ax.text(0.9, 4.55,
            "Sabit · Uyarlanır · Tahmine Dayalı · Acil Öncelikli",
            fontsize=15, color=BODY, va="center")
    ax.text(0.9, 4.95, "4 Kontrol Stratejisinin Karşılaştırmalı Analizi",
            fontsize=13, color=BODY, va="center", fontstyle="italic")

    # Alt bilgi — Mersin Üniversitesi
    ax.text(0.9, 5.5, "Mersin Üniversitesi",
            fontsize=12, color=NEUTRAL, va="center")
    ax.text(0.9, 5.78,
            "Erdemli Uygulamalı Teknoloji ve İşletmecilik Yüksekokulu",
            fontsize=10.5, color=NEUTRAL, va="center")
    ax.text(0.9, 6.05, "Bilişim Sistemleri ve Teknolojileri Bölümü",
            fontsize=10.5, color=NEUTRAL, va="center")

    ax.text(0.9, 6.4, "Nihal Kemer · 22430070004",
            fontsize=11.5, color=BODY, va="center")
    ax.text(0.9, 6.65, "Mehmet Furkan Güneş · 22430070005",
            fontsize=11.5, color=BODY, va="center")
    ax.text(0.9, 6.95, "Benzetim Programları · Final Projesi · 2026",
            fontsize=10.5, color=NEUTRAL, va="center")

    # Sağ: kavşak ikonu
    _intersection_icon(ax, cx=10.5, cy=4.0, size=2.2)
    ax.text(10.5, 6.7, "4 Yollu Kavşak Modeli",
            fontsize=11, color=NEUTRAL, ha="center",
            va="center", fontstyle="italic")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 2: Neden? -------------------------------------------------


def slide_02_problem(pdf: PdfPages) -> None:
    fig, ax = _new_slide(2)
    _title(ax, "Neden Trafik Işığı Optimizasyonu?")

    cards = [
        ("Trafik sıkışıklığı",
         "Şehir merkezi yoğun saatte 2x talep. Sabit ışıklar yetmiyor."),
        ("Acil müdahale gecikmesi",
         "Ambulans 40 sn beklerse hayat kaybı olabilir."),
        ("Sezgi yanılır",
         "'Daha çok yeşil ver' çoğu zaman yanlış kavşağa öncelik verir."),
        ("Gerçek deneme imkânsız",
         "Yoğun trafikte ayar denemek riskli; simülasyon güvenli laboratuvar."),
    ]
    positions = [(0.9, 1.9), (7.0, 1.9), (0.9, 4.3), (7.0, 4.3)]
    card_w, card_h = 5.4, 2.0
    for (title_t, body_t), (cx, cy) in zip(cards, positions):
        ax.add_patch(Rectangle((cx, cy), 0.08, card_h,
                               facecolor=ACCENT, edgecolor="none"))
        ax.add_patch(Rectangle((cx + 0.08, cy), card_w - 0.08, card_h,
                               facecolor=LIGHT_GRAY, edgecolor="none"))
        ax.text(cx + 0.35, cy + 0.55, title_t,
                fontsize=18, color=TITLE_COLOR, fontweight="bold",
                va="center")
        ax.text(cx + 0.35, cy + 1.3, body_t,
                fontsize=12, color=BODY, va="center")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 5: Akış ---------------------------------------------------


def slide_05_flow(pdf: PdfPages) -> None:
    fig, ax = _new_slide(3)
    _title(ax, "Araç Akışı")

    # 4 yön kutusu (sol tarafta, dikey hiza)
    arm_x = 0.7
    arm_w = 2.4
    arm_h = 0.7
    arm_gap = 0.25
    arm_top = 2.0
    for i, (label, color) in enumerate([
        ("Kuzey gelen",  BLUE),
        ("Doğu gelen",   "#10B981"),
        ("Güney gelen",  "#F59E0B"),
        ("Batı gelen",   "#A855F7"),
    ]):
        y = arm_top + i * (arm_h + arm_gap)
        _label_box(ax, x=arm_x, y=y, w=arm_w, h=arm_h,
                   text=label, bg=color, fontsize=12)
        ax.annotate("", xy=(arm_x + arm_w + 0.6, y + arm_h / 2),
                    xytext=(arm_x + arm_w + 0.02, y + arm_h / 2),
                    arrowprops=dict(arrowstyle="->", color=BODY, lw=1.4))

    # Orta: Kavşak + sinyal kontrolu
    central_x, central_y = 5.6, 3.5
    _label_box(ax, x=central_x, y=central_y - 0.8, w=2.2, h=1.6,
               text="KAVŞAK\n+ SİNYAL", bg=TITLE_COLOR, fontsize=14)

    # Çıkış
    out_x = central_x + 3.4
    ax.annotate("", xy=(out_x, central_y),
                xytext=(central_x + 2.2 + 0.02, central_y),
                arrowprops=dict(arrowstyle="->", color=BODY, lw=1.8))
    _label_box(ax, x=out_x, y=central_y - 0.4, w=2.4, h=0.85,
               text="Çıkış", bg=SUCCESS, fontsize=13)

    # Acil araç vurgusu — kırmızı ok + uyari
    ax.annotate(
        "", xy=(central_x - 0.05, central_y + 0.6),
        xytext=(central_x - 1.6, central_y + 1.5),
        arrowprops=dict(arrowstyle="->", color=WARNING, lw=2.5),
    )
    ax.text(central_x - 1.85, central_y + 1.4,
            "Acil araç\n(preempt)",
            fontsize=11, color=WARNING, fontweight="bold",
            ha="right", va="center")

    # Acillama notu
    ax.text(SLIDE_W / 2, 6.55,
            "Kontrolcü (4 strateji) yeşil ışığı yönetir, "
            "araçlar yeşilde tek tek geçer.",
            fontsize=12, color=BODY, ha="center", va="center")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 6: Domain -------------------------------------------------


def slide_06_domain(pdf: PdfPages) -> None:
    fig, ax = _new_slide(4)
    _title(ax, "Domain Modeli")

    # Sol tablo: yön bazli geliş hızı
    _table(
        ax, left=0.6, top=1.9,
        col_widths=[1.4, 1.8, 1.8], row_height=0.55,
        rows_data=[
            ["Yön", "Normal", "Yoğun saat"],
            ["Kuzey", "0.40 araç/dk", "0.80"],
            ["Güney", "0.40 araç/dk", "0.70"],
            ["Doğu",  "0.30 araç/dk", "0.60"],
            ["Batı",  "0.30 araç/dk", "0.60"],
        ],
        fontsize=12,
        col_align=["left", "center", "center"],
    )

    # Sağ tablo: sinyal süreleri
    _table(
        ax, left=7.0, top=1.9,
        col_widths=[2.5, 1.5], row_height=0.55,
        rows_data=[
            ["Faz", "Süre"],
            ["Yeşil",            "30 sn"],
            ["Sarı",              "3 sn"],
            ["Tüm-kırmızı buffer","1 sn"],
            ["Tam çevrim (4 yön)","136 sn"],
        ],
        fontsize=12,
        col_align=["left", "center"],
    )

    _accent_callout(
        ax, x=0.6, y=5.6, w=12.1, h=0.9,
        text="Araç tipi:  %95 Normal  ·  %5 Acil (ambulans / itfaiye / polis)  "
             "·  Yoğun saat: 07-09 ve 17-19",
        fontsize=13,
    )

    ax.text(0.6, 5.25,
            "Hızlar Poisson dağılımı; her saat için sabit ortalama lambda.",
            fontsize=10, color=NEUTRAL, fontstyle="italic", va="center")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 7: Baseline -----------------------------------------------


def slide_07_baseline(pdf: PdfPages) -> None:
    fig, ax = _new_slide(5)
    _title(ax, "Başlangıç Sonuçları: Sabit Zamanlı Yöntem")

    # 4 büyük KPI karti (5 seed ortalaması)
    kpis = [
        ("Ortalama bekleme",  "43.7 sn", "tüm araçlar", WARNING),
        ("Acil bekleme",      "40.4 sn", "ciddi sorun", "#7F1D1D"),
        ("Saatlik geçen",      "85.2",   "araç / saat", BLUE),
        ("Tam çevrim",        "136 sn",  "her çevrim sabit", NEUTRAL),
    ]
    card_w, card_h = 2.85, 1.7
    gap = 0.2
    total_w = 4 * card_w + 3 * gap
    start_x = (SLIDE_W - total_w) / 2
    for i, (label, value, sub, color) in enumerate(kpis):
        _kpi_card(ax, x=start_x + i * (card_w + gap), y=1.7,
                  w=card_w, h=card_h,
                  label=label, value=value, bg=color, sublabel=sub)

    # Alt: yön bazli bekleme bar chart (inset)
    inset = fig.add_axes([0.18, 0.13, 0.72, 0.30])
    directions = ["Kuzey", "Doğu", "Güney", "Batı"]
    # Faz 1 smoke run'da goz önünde tutulan bekleme degerleri
    # (5 seed × baseline koşumu fortlanmis sayilar — yaklaşık)
    waits = [45.5, 39.4, 39.0, 47.2]
    colors = [BLUE, "#10B981", "#F59E0B", "#A855F7"]
    bars = inset.bar(directions, waits, color=colors, edgecolor="none")
    inset.set_ylim(0, 60)
    inset.set_ylabel("Ortalama bekleme (sn)",
                     fontsize=10, color=BODY)
    inset.set_title("Yön bazlı ortalama bekleme — sabit kontrolde dengesiz",
                    fontsize=11, color=TITLE_COLOR, pad=8)
    for s in ("top", "right"):
        inset.spines[s].set_visible(False)
    inset.spines["left"].set_color(BORDER)
    inset.spines["bottom"].set_color(BORDER)
    inset.tick_params(colors=BODY, labelsize=9)
    for bar, v in zip(bars, waits):
        inset.text(bar.get_x() + bar.get_width() / 2, v + 1,
                   f"{v:.1f}", ha="center", va="bottom",
                   fontsize=9, color=BODY)

    # Alt kose dipnot
    ax.text(SLIDE_W - 0.6, FOOTER_Y,
            "5 seed ortalaması, 4 saat simülasyon",
            fontsize=9, color=NEUTRAL,
            ha="right", va="center", fontstyle="italic")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 8: Altin slayt --------------------------------------------


def slide_08_gold(pdf: PdfPages) -> None:
    fig, ax = _new_slide(6)
    _title(ax, "Sezgi vs Veri")

    # Sol: senaryo tablosu (4 kontrolcü)
    rows = [
        ["Yöntem",          "Ortalama", "Acil",    "Bulgu"],
        ["Sabit",           "43.7 sn",  "40.4 sn", "referans"],
        ["Uyarlanır",       "9.7 sn",   "7.2 sn",  "%78 ortalama düşüş"],
        ["Tahmine Dayalı",  "9.7 sn",   "6.8 sn",  "kötü uç %9, adalet %4.5 ↑"],
        ["Acil Öncelikli",  "10.1 sn",  "5.8 sn",  "%86 acil düşüş"],
    ]
    _table(
        ax,
        left=0.5, top=1.7, col_widths=[2.4, 1.4, 1.4, 3.0], row_height=0.55,
        rows_data=rows, fontsize=12,
        row_bg={2: "#F0FDF4", 3: "#ECFDF5", 4: "#DCFCE7"},
        row_fg={2: SUCCESS, 3: SUCCESS, 4: SUCCESS},
        row_bold={2, 3, 4},
        col_align=["left", "right", "right", "left"],
    )

    # Sağ: acil araç karşılaştırma grafigini embed et
    em_path = Path("results/comparison_emergency_wait.png")
    if em_path.exists():
        _image(ax, em_path, x=8.2, y=1.5, w=5.0, h=3.2)

    # Altin slayt alintisi
    ax.add_patch(Rectangle((0.6, 5.25), 0.08, 1.85,
                           facecolor=ACCENT, edgecolor="none"))
    quote_lines = [
        '"Sabit kontrolde ambulans 40 saniye bekliyor.',
        'Uyarlanır yöntem bunu 7 saniyeye düşürdü.',
        'Acil öncelikli kontrol 6 saniyeye.',
        'Aynı kavşak, dört farklı mantık, ambulans için 7 kat fark.',
        'Doğru kararı sezgi değil simülasyon verisi gösterdi."',
    ]
    for i, line in enumerate(quote_lines):
        ax.text(0.9, 5.40 + i * 0.32, line,
                fontsize=12.5, color=TITLE_COLOR,
                fontweight="bold", fontstyle="italic", va="center")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 7: Final genişletmesi (4. kontrolcü + 4 yeni metrik) -----


def slide_final_expansion(pdf: PdfPages) -> None:
    """Final için eklenen 4. kontrolcü + percentile/fairness/CO2/heatmap."""
    fig, ax = _new_slide(7)
    _title(ax, "Final Genişletmesi")

    # Sol kart — 4. Kontrolcü
    left_x, left_y = 0.6, 1.6
    left_w, left_h = 5.6, 5.4
    ax.add_patch(Rectangle((left_x, left_y), 0.08, left_h,
                           facecolor=TITLE_COLOR, edgecolor="none"))
    ax.add_patch(Rectangle((left_x + 0.08, left_y),
                           left_w - 0.08, left_h,
                           facecolor=LIGHT_GRAY, edgecolor="none"))
    ax.text(left_x + 0.35, left_y + 0.5, "4. Yöntem:",
            fontsize=14, color=NEUTRAL, va="center")
    ax.text(left_x + 0.35, left_y + 0.95, "Tahmine Dayalı",
            fontsize=22, color=TITLE_COLOR, fontweight="bold", va="center")

    items = [
        ("Karma puan", "puan = anlık kuyruk + 0.3 × kuyruktaki artış"),
        ("Eğilim bonusu", "Son 60 sn kuyruk eğilimi, 30 sn için tahmin"),
        ("Uyarlanır temel",
         "Anlık kuyruk korunur, artan eğilim ek puan getirir"),
    ]
    iy = left_y + 1.6
    for head, body in items:
        ax.text(left_x + 0.35, iy, "•",
                fontsize=16, color=ACCENT, fontweight="bold", va="top")
        ax.text(left_x + 0.65, iy, head,
                fontsize=13, color=TITLE_COLOR, fontweight="bold", va="top")
        ax.text(left_x + 0.65, iy + 0.30, body,
                fontsize=10.5, color=BODY, va="top")
        iy += 0.78

    # Karşılaştırma kutucuğu (alt yarı)
    cmp_y = left_y + left_h - 1.35
    ax.add_patch(Rectangle((left_x + 0.35, cmp_y), left_w - 0.7, 1.2,
                           facecolor="#ECFDF5", edgecolor=SUCCESS,
                           linewidth=1.2))
    ax.text(left_x + 0.5, cmp_y + 0.22, "Sonuç (5 seed × 4 saat):",
            fontsize=10, color=NEUTRAL, va="center")
    ax.text(left_x + 0.5, cmp_y + 0.55,
            "Ort. 9.71 sn  ·  Yön adaleti 0.891",
            fontsize=13, color=SUCCESS, fontweight="bold", va="center")
    ax.text(left_x + 0.5, cmp_y + 0.92,
            "Uyarlanır: 9.70 / 0.852  →  kötü uç −%9, acil −%5, adalet +%4.5",
            fontsize=10, color=BODY, va="center", fontstyle="italic")

    # Sağ panel — 4 yeni metrik (2×2 grid)
    right_x = 7.0
    right_y = 1.6
    card_w, card_h = 2.95, 1.25
    gap = 0.15

    metrics = [
        # (baslik, deger, alt yazi, vurgu rengi)
        ("En Kötü %5 Bekleme", "26.5 sn",
         "Tahmine dayalı: uyarlanırdan −%9 (29.2→26.5)", BLUE),
        ("Yön Adaleti", "0.891",
         "Uyarlanır 0.852 → tahmine dayalı +%4.5", "#9333EA"),
        ("CO2 / Yakıt", "Sabit −%78",
         "Sabit 5737g → Uyarlanır 1271g (4× az)", SUCCESS),
        ("Saatlik Bekleme", "Yön × Saat",
         "Trafik dengeli değil; yoğun saatler belirgin", ACCENT),
    ]
    positions = [
        (right_x, right_y),
        (right_x + card_w + gap, right_y),
        (right_x, right_y + card_h + gap),
        (right_x + card_w + gap, right_y + card_h + gap),
    ]
    for (title_t, value, sub, bar_col), (cx, cy) in zip(metrics, positions):
        ax.add_patch(Rectangle((cx, cy), 0.08, card_h,
                               facecolor=bar_col, edgecolor="none"))
        ax.add_patch(Rectangle((cx + 0.08, cy), card_w - 0.08, card_h,
                               facecolor=LIGHT_GRAY, edgecolor="none"))
        ax.text(cx + 0.25, cy + 0.25, title_t,
                fontsize=11, color=TITLE_COLOR, fontweight="bold", va="top")
        ax.text(cx + 0.25, cy + 0.7, value,
                fontsize=16, color=bar_col, fontweight="bold", va="center")
        ax.text(cx + 0.25, cy + card_h - 0.15, sub,
                fontsize=9, color=BODY, va="bottom")

    # Alt vurgu — turuncu callout
    cb_y = 1.6 + 2 * (card_h + gap)
    _accent_callout(
        ax, x=right_x, y=cb_y + 0.15,
        w=2 * card_w + gap, h=0.55,
        text="24 yeni test · dilimler / adalet / CO2 / karma katsayı denemesi",
        fontsize=11, bg="#FFF1E6", bar_color=ACCENT,
    )

    # Genel kapanış kutucuğu (slaytin altinda)
    box_y = 6.6
    ax.add_patch(Rectangle((0.6, box_y), 12.1, 0.45,
                           facecolor=TITLE_COLOR, edgecolor="none"))
    ax.text(SLIDE_W / 2, box_y + 0.22,
            "Tahmine dayalı yöntem: ortalamayı kaybetmeden kötü uç −%9, "
            "acil −%5, adalet +%4.5.",
            fontsize=11, color=WHITE, ha="center", va="center",
            fontweight="bold")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 8: Muhendislik --------------------------------------------


def slide_burst_stats(pdf: PdfPages) -> None:
    """Slayt 8: Burst senaryosu + Mann-Whitney U istatistiksel anlamlılık.

    Sol kart: burst tablosu (sabit 1139 sn felaket)
    Sağ kart: Mann-Whitney p-value'lar (p95 p=0.013*, fairness p=0.002**)
    Alt callout: 'sabit 67× kötü, predictive iyileşme istatistiksel anlamlı'
    """
    fig, ax = _new_slide(8)
    _title(ax, "Ani Talep Senaryosu + İstatistiksel Güvenilirlik")

    # Sol kart — burst tablosu
    left_x, left_y = 0.6, 1.6
    left_w, left_h = 6.2, 5.4
    ax.add_patch(Rectangle((left_x, left_y), 0.08, left_h,
                           facecolor=WARNING, edgecolor="none"))
    ax.add_patch(Rectangle((left_x + 0.08, left_y),
                           left_w - 0.08, left_h,
                           facecolor=LIGHT_GRAY, edgecolor="none"))
    ax.text(left_x + 0.35, left_y + 0.45, "Ani talep senaryosu",
            fontsize=14, color=NEUTRAL, va="center")
    ax.text(left_x + 0.35, left_y + 0.95,
            "30 dk boyunca Kuzey'e +20 araç/dk",
            fontsize=18, color=TITLE_COLOR, fontweight="bold", va="center")
    ax.text(left_x + 0.35, left_y + 1.35,
            "(okul çıkışı / maç sonu benzeri)",
            fontsize=10, color=NEUTRAL, fontstyle="italic", va="center")

    # Tablo verisi (5 seed × 4 saat ortalama)
    _table(
        ax, left=left_x + 0.35, top=left_y + 1.85,
        col_widths=[2.0, 1.6, 1.3], row_height=0.5,
        rows_data=[
            ["Yöntem", "Ort. (sn)", "En kötü %5"],
            ["Sabit Zamanlı", "1138.9", "3122"],
            ["Uyarlanır", "16.84", "28.1"],
            ["Tahmine Dayalı", "16.69", "27.5"],
            ["Acil Öncelikli", "17.46", "32.0"],
        ],
        fontsize=11,
        row_bg={1: "#FEE2E2"},   # fixed kırmızı vurgusu
        row_fg={1: WARNING},
        row_bold={1},
        col_align=["left", "right", "right"],
    )

    # Burst kart altı kırmızı vurgu
    ax.add_patch(Rectangle((left_x + 0.35, left_y + 4.5),
                           left_w - 0.7, 0.55,
                           facecolor="#FEE2E2", edgecolor=WARNING,
                           linewidth=1.0))
    ax.text(left_x + left_w / 2, left_y + 4.78,
            "Sabit yöntem: 67× daha kötü ortalama bekleme",
            fontsize=11, color=WARNING, fontweight="bold",
            ha="center", va="center")

    # Sağ kart — Mann-Whitney U
    right_x, right_y = 7.2, 1.6
    right_w, right_h = 5.5, 5.4
    ax.add_patch(Rectangle((right_x, right_y), 0.08, right_h,
                           facecolor=BLUE, edgecolor="none"))
    ax.add_patch(Rectangle((right_x + 0.08, right_y),
                           right_w - 0.08, right_h,
                           facecolor=LIGHT_GRAY, edgecolor="none"))
    ax.text(right_x + 0.35, right_y + 0.45, "Mann-Whitney U",
            fontsize=14, color=NEUTRAL, va="center")
    ax.text(right_x + 0.35, right_y + 0.95,
            "Sonuçların Güvenilirliği",
            fontsize=18, color=TITLE_COLOR, fontweight="bold", va="center")
    ax.text(right_x + 0.35, right_y + 1.35,
            "10 tekrar × 4 saat, dağılım bağımsız test",
            fontsize=10, color=NEUTRAL, fontstyle="italic", va="center")

    # p değeri satırları
    pvals = [
        ("Uyarlanır vs Tahmine Dayalı ortalama", "p = 0.97",
         "anlamsız", NEUTRAL,
         "trend bonusu ortalamayı kaybetmedi"),
        ("Tahmine Dayalı kötü uç < Uyarlanır", "p = 0.013",
         "anlamlı", SUCCESS,
         "kötü uçta gerçek iyileşme"),
        ("Tahmine Dayalı adalet > Uyarlanır", "p = 0.0018",
         "çok anlamlı", SUCCESS,
         "yön adaletinde belirgin iyileşme"),
        ("Sabit ortalama > Uyarlanır", "p < 0.001",
         "çok güçlü", WARNING,
         "ana bulgu çok güçlü"),
    ]
    py = right_y + 1.85
    for label, pval, sig, col, note in pvals:
        # Etiket kutusu
        ax.add_patch(Rectangle((right_x + 0.35, py), 0.95, 0.42,
                               facecolor=col, edgecolor="none"))
        ax.text(right_x + 0.825, py + 0.21, sig,
                fontsize=9, color=WHITE, fontweight="bold",
                ha="center", va="center")
        # Açıklama
        ax.text(right_x + 1.45, py + 0.08, label,
                fontsize=10, color=TITLE_COLOR, fontweight="bold", va="top")
        ax.text(right_x + 1.45, py + 0.42, f"{pval}  ·  {note}",
                fontsize=8.5, color=BODY, va="top")
        py += 0.85

    # Alt vurgu — yeşil ribbon
    box_y = 7.05
    ax.add_patch(Rectangle((0.6, box_y - 0.45), 12.1, 0.45,
                           facecolor=SUCCESS, edgecolor="none"))
    ax.text(SLIDE_W / 2, box_y - 0.225,
            "Tahmine dayalı yöntemin iyileşmesi rastlantı değil — "
            "kötü uç p=0.013, yön adaleti p=0.0018 ile anlamlı.",
            fontsize=11, color=WHITE, ha="center", va="center",
            fontweight="bold")

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 9: Muhendislik --------------------------------------------


def slide_09_engineering(pdf: PdfPages) -> None:
    fig, ax = _new_slide(9)
    _title(ax, "Uygulama Detayları")

    items = [
        (
            "Uyarlanır yeşil süresi",
            "Kuyruktaki araç sayısına göre değişir; en az 15, en fazla 60 sn",
            "yeşil = kuyruk × 3 sn  (15–60 arası)",
        ),
        (
            "Acil araç tespiti",
            "Yarım saniyede bir kuyruk taranır, acil araç var mı?",
            "eğer araç acil ise: önceliklendir",
        ),
        (
            "Acil müdahale",
            "Acil araç varsa mevcut yeşil 5 sn'de kapanır, ilgili yöne 15 sn",
            "yeşil 5 sn'de bitir → acil yön 15 sn",
        ),
        (
            "Düzenli kontrol",
            "Her yarım saniyede kuyruğa bakılır — anlaşılır ve test edilebilir",
            "her 0.5 sn'de bir kontrol et",
        ),
    ]
    row_y = 1.7
    for i, (head, desc, code) in enumerate(items):
        y = row_y + i * 1.18
        # Turuncu numarali daire
        ax.add_patch(FancyBboxPatch(
            (0.6, y), 0.55, 0.55,
            boxstyle="round,pad=0.02,rounding_size=0.28",
            facecolor=ACCENT, edgecolor="none",
        ))
        ax.text(0.875, y + 0.275, str(i + 1),
                ha="center", va="center", fontsize=16,
                color=WHITE, fontweight="bold")
        # Başlık + açıklama
        ax.text(1.35, y + 0.05, head,
                fontsize=14, color=TITLE_COLOR, fontweight="bold", va="top")
        ax.text(1.35, y + 0.50, desc,
                fontsize=11.5, color=BODY, va="top")
        # Kod paneli
        code_x = 7.5
        code_w = 5.2
        code_h = 0.65
        ax.add_patch(Rectangle((code_x, y), code_w, code_h,
                               facecolor=CODE_BG, edgecolor="none"))
        ax.text(code_x + 0.15, y + code_h / 2, code,
                fontsize=10, color=CODE_FG, va="center", family="monospace")

    _accent_callout(
        ax, x=0.6, y=6.45, w=12.1, h=0.55,
        text="92 birim test (+ Mann-Whitney U)  ·  mypy --strict temiz  ·  ruff temiz  ·  "
             "Pydantic v2 domain modelleri",
        fontsize=12, bg="#ECFDF5", bar_color=SUCCESS,
    )

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Slayt 10: Demo + kapanis ----------------------------------------


def slide_10_demo(pdf: PdfPages) -> None:
    fig, ax = _new_slide(10)
    _title(ax, "Canlı Demo + Kapanış")

    # Sol: demo plani
    ax.text(0.6, 1.95, "Demo planı", fontsize=18,
            color=TITLE_COLOR, fontweight="bold", va="center")

    steps = [
        ("1", "Tahmine Dayalı senaryo seç + Çalıştır"),
        ("2", "KPI kartlarını ve grafikleri göster"),
        ("3", "Sekme 3: Kavşak görseli ve sinyaller"),
    ]
    for i, (num, text) in enumerate(steps):
        y = 2.7 + i * 0.85
        ax.add_patch(FancyBboxPatch(
            (0.6, y), 0.55, 0.55,
            boxstyle="round,pad=0.02,rounding_size=0.28",
            facecolor=SUCCESS, edgecolor="none",
        ))
        ax.text(0.875, y + 0.275, num,
                ha="center", va="center", fontsize=14,
                color=WHITE, fontweight="bold")
        ax.text(1.4, y + 0.275, text,
                fontsize=14, color=BODY, va="center")

    # Sağ: kavşak diyagrami screenshot
    inter_path = Path("results/screenshots/07_intersection_view.png")
    if inter_path.exists():
        _image(ax, inter_path, x=6.5, y=1.8, w=6.3, h=3.5)
        ax.text(9.65, 5.45, "Kavşak görseli (dashboard Sekme 3)",
                fontsize=10, color=NEUTRAL,
                ha="center", va="center", fontstyle="italic")

    # Repo URL
    ax.text(SLIDE_W / 2, 6.05,
            "github.com/Lightfield0/intersection-sim",
            fontsize=11, color=NEUTRAL, ha="center", va="center",
            family="monospace")

    # Sorular?
    ax.text(SLIDE_W / 2, 6.65, "Sorular?",
            fontsize=36, color=TITLE_COLOR, fontweight="bold",
            ha="center", va="center")
    ax.add_patch(Rectangle((SLIDE_W / 2 - 0.9, 6.95), 1.8, ACCENT_LINE_H,
                           facecolor=ACCENT, edgecolor="none"))

    pdf.savefig(fig)
    plt.close(fig)


# ---------- Main ------------------------------------------------------------


def build() -> Path:
    with PdfPages(OUTPUT) as pdf:
        slide_01_cover(pdf)
        slide_02_problem(pdf)
        slide_05_flow(pdf)
        slide_06_domain(pdf)
        slide_07_baseline(pdf)
        slide_08_gold(pdf)
        slide_final_expansion(pdf)
        slide_burst_stats(pdf)
        slide_09_engineering(pdf)
        slide_10_demo(pdf)
        info = pdf.infodict()
        info["Title"] = "Akıllı Kavşak Trafik Işığı Simülasyonu"
        info["Author"] = "Nihal Kemer"
        info["Subject"] = "Benzetim Programlari — Final Odevi"
    return OUTPUT


if __name__ == "__main__":
    out = build()
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KB, {N_SLIDES} pages)")
