"""Final raporu PDF builder — ReportLab Platypus, Türkçe karakter destekli.

Hocaya elden teslim için yazdırılabilir akademik rapor formatı.
Bütün bulgular, tablolar, grafikler embed edilir.

Çıktı: docs/rapor.pdf (~18-20 sayfa, A4 portrait).
Font: Times New Roman (akademik standart, Türkçe karakter destekli).
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUTPUT_PATH = Path("docs/rapor.pdf")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------- Türkçe karakter destekli font (Times New Roman) ----------------


def _register_fonts() -> tuple[str, str, str]:
    """Akademik Times font ailesini kaydet."""
    fonts_dir = Path("/System/Library/Fonts/Supplemental")
    try:
        pdfmetrics.registerFont(TTFont(
            "TR", str(fonts_dir / "Times New Roman.ttf"),
        ))
        pdfmetrics.registerFont(TTFont(
            "TRBold", str(fonts_dir / "Times New Roman Bold.ttf"),
        ))
        pdfmetrics.registerFont(TTFont(
            "TRItalic", str(fonts_dir / "Times New Roman Italic.ttf"),
        ))
        return "TR", "TRBold", "TRItalic"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


FONT_REGULAR, FONT_BOLD, FONT_ITALIC = _register_fonts()


# ---------- Stiller --------------------------------------------------------


_STYLES = getSampleStyleSheet()


def _style(name: str, **kwargs) -> ParagraphStyle:
    base = ParagraphStyle(name=name, parent=_STYLES["Normal"])
    base.fontName = kwargs.pop("fontName", FONT_REGULAR)
    base.fontSize = kwargs.pop("fontSize", 11)
    base.leading = kwargs.pop("leading", 15)
    base.alignment = kwargs.pop("alignment", TA_JUSTIFY)
    base.textColor = kwargs.pop("textColor", colors.black)
    base.spaceAfter = kwargs.pop("spaceAfter", 6)
    base.spaceBefore = kwargs.pop("spaceBefore", 0)
    for k, v in kwargs.items():
        setattr(base, k, v)
    return base


STYLE_BODY = _style("Body")
STYLE_BODY_FIRST = _style("BodyFirst", firstLineIndent=20)
STYLE_H1 = _style("H1", fontName=FONT_BOLD, fontSize=16, leading=20,
                  textColor=colors.HexColor("#1B4D3E"),
                  spaceBefore=14, spaceAfter=10, alignment=TA_LEFT)
STYLE_H2 = _style("H2", fontName=FONT_BOLD, fontSize=13, leading=17,
                  textColor=colors.HexColor("#1B4D3E"),
                  spaceBefore=10, spaceAfter=6, alignment=TA_LEFT)
STYLE_H3 = _style("H3", fontName=FONT_BOLD, fontSize=11.5, leading=14,
                  textColor=colors.HexColor("#1B4D3E"),
                  spaceBefore=8, spaceAfter=4, alignment=TA_LEFT)
STYLE_CAPTION = _style("Caption", fontSize=9, leading=12,
                       textColor=colors.HexColor("#4B5563"),
                       fontName=FONT_ITALIC,
                       alignment=TA_CENTER, spaceAfter=10, spaceBefore=4)
STYLE_CODE = _style("Code", fontName="Courier", fontSize=9.5, leading=12.5,
                    textColor=colors.HexColor("#1F2937"),
                    backColor=colors.HexColor("#F3F4F6"),
                    borderPadding=6, borderRadius=2, spaceAfter=8)
STYLE_TOC = _style("TOC", fontSize=11, leading=18,
                   alignment=TA_LEFT, spaceAfter=2)
STYLE_BULLET = _style("Bullet", leftIndent=15, bulletIndent=0,
                      spaceAfter=4)

# Kapak stilleri
STYLE_COVER_UNI = _style("CoverUni", fontName=FONT_BOLD, fontSize=14,
                         leading=18, alignment=TA_CENTER, spaceAfter=4)
STYLE_COVER_FAC = _style("CoverFac", fontSize=12, leading=15,
                         alignment=TA_CENTER, spaceAfter=2)
STYLE_COVER_TITLE = _style("CoverTitle", fontName=FONT_BOLD,
                           fontSize=22, leading=28,
                           textColor=colors.HexColor("#1B4D3E"),
                           alignment=TA_CENTER, spaceAfter=10)
STYLE_COVER_SUB = _style("CoverSub", fontSize=12, leading=15,
                         fontName=FONT_ITALIC,
                         alignment=TA_CENTER, spaceAfter=8)
STYLE_COVER_INFO = _style("CoverInfo", fontSize=11.5, leading=15,
                          alignment=TA_CENTER, spaceAfter=3)
STYLE_COVER_NAME = _style("CoverName", fontName=FONT_BOLD, fontSize=13,
                          leading=16, alignment=TA_CENTER, spaceAfter=3)


# ---------- Sayfa çerçevesi (header/footer) -------------------------------


def _on_page(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_REGULAR, 8.5)
    canvas.setFillColor(colors.HexColor("#6B7280"))
    canvas.drawString(
        2 * cm, 1.2 * cm,
        "N. Kemer · M. F. Güneş · Akıllı Kavşak Trafik Işığı Simülasyonu · 2026",
    )
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Sayfa {doc.page}")
    canvas.restoreState()


def _on_cover(canvas, doc) -> None:
    pass


# ---------- Helper: tablo --------------------------------------------------


def _make_table(
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float],
    col_align: list[str] | None = None,
    header_bg: str = "#1B4D3E",
    alt_row_bg: str = "#F3F4F6",
) -> Table:
    """Standart tablo. col_align verilmezse: 1. sütun LEFT, kalan RIGHT."""
    data = [headers, *rows]
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    n_cols = len(headers)
    if col_align is None:
        col_align = ["LEFT"] + ["RIGHT"] * (n_cols - 1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#374151")),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
    ]
    # Sütun bazlı hizalama
    for i, align in enumerate(col_align):
        style.append(("ALIGN", (i, 0), (i, -1), align))
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i),
                          colors.HexColor(alt_row_bg)))
    tbl.setStyle(TableStyle(style))
    return tbl


def _figure(path: str, caption: str, max_width_cm: float = 14.0):
    p = Path(path)
    if not p.exists():
        return Paragraph(f"<i>[grafik bulunamadı: {path}]</i>", STYLE_CAPTION)
    img = Image(path, width=max_width_cm * cm,
                height=max_width_cm * cm * 0.6, kind="proportional")
    return KeepTogether([img, Paragraph(caption, STYLE_CAPTION)])


# ---------- Bölümler -------------------------------------------------------


def section_cover() -> list:
    """Kapak sayfası — tek sayfada sığacak şekilde sıkıştırıldı."""
    flow = []
    flow.append(Spacer(1, 1.5 * cm))
    flow.append(Paragraph(
        "MERSİN ÜNİVERSİTESİ", STYLE_COVER_UNI,
    ))
    flow.append(Paragraph(
        "Erdemli Uygulamalı Teknoloji ve İşletmecilik Yüksekokulu",
        STYLE_COVER_FAC,
    ))
    flow.append(Paragraph(
        "Bilişim Sistemleri ve Teknolojileri Bölümü", STYLE_COVER_FAC,
    ))

    flow.append(Spacer(1, 3 * cm))
    flow.append(Paragraph("AKILLI KAVŞAK TRAFİK IŞIĞI", STYLE_COVER_TITLE))
    flow.append(Paragraph("SİMÜLASYONU", STYLE_COVER_TITLE))
    flow.append(Spacer(1, 0.4 * cm))
    flow.append(Paragraph(
        "Sabit, Uyarlanır, Tahmine Dayalı ve Acil Öncelikli "
        "4 Kontrol Stratejisinin Karşılaştırmalı Analizi",
        STYLE_COVER_SUB,
    ))

    flow.append(Spacer(1, 2 * cm))
    flow.append(Paragraph("Benzetim Programları", STYLE_COVER_INFO))
    flow.append(Paragraph("Final Projesi · 2026", STYLE_COVER_INFO))

    flow.append(Spacer(1, 1.5 * cm))
    flow.append(Paragraph("Hazırlayanlar", STYLE_COVER_INFO))
    flow.append(Spacer(1, 0.2 * cm))
    flow.append(Paragraph("Nihal Kemer · 22430070004", STYLE_COVER_NAME))
    flow.append(Paragraph(
        "Mehmet Furkan Güneş · 22430070005", STYLE_COVER_NAME,
    ))

    flow.append(Spacer(1, 1.8 * cm))
    flow.append(Paragraph(
        "GitHub: github.com/Lightfield0/intersection-sim",
        _style("repo", fontSize=10, leading=14, alignment=TA_CENTER,
               textColor=colors.HexColor("#1B4D3E"), fontName=FONT_BOLD),
    ))
    flow.append(PageBreak())
    return flow


def section_abstract() -> list:
    flow = []
    flow.append(Paragraph("ÖZET", STYLE_H1))
    flow.append(Paragraph(
        "Bu çalışmada, dört yollu bir kavşakta dört farklı trafik ışığı "
        "kontrol yöntemi Python diliyle yazılmış bir benzetim programı "
        "üzerinde karşılaştırılmıştır. İncelenen yöntemler şunlardır: "
        "(1) sabit zamanlı yöntem — her yöne sırayla 30 saniye yeşil "
        "veren klasik anlayış; (2) uyarlanır yöntem — en kalabalık yöne "
        "daha uzun yeşil veren strateji; (3) tahmine dayalı yöntem — son "
        "bir dakikanın kuyruk eğilimine bakıp yakın geleceği tahmin eden "
        "karma yaklaşım; (4) acil öncelikli yöntem — uyarlanır mantığa "
        "ambulans önceliklendirmesi ekleyen anlayış.",
        STYLE_BODY,
    ))
    flow.append(Paragraph(
        "5 tekrar × 4 saatlik koşumların ortalaması alındığında, sabit "
        "yöntemin ortalama bekleme süresi 43.7 saniye iken uyarlanır "
        "yönteme geçildiğinde bu süre %77.8 azalarak 9.7 saniyeye "
        "düşmüştür. Acil öncelikli yöntem ambulans bekleme süresini "
        "40.4 saniyeden 5.8 saniyeye indirmiştir (yedi kat azalma). "
        "Çevresel açıdan da sabit yöntem, uyarlanır yönteme göre "
        "yaklaşık 4 kat daha fazla karbondioksit (CO2) salımına yol "
        "açmaktadır.",
        STYLE_BODY,
    ))
    flow.append(Paragraph(
        "Bunlara ek olarak; bekleme süresi dağılım dilimleri "
        "(%50–%99 aralığı), yön bazlı adalet ölçütü, yakıt ve CO2 "
        "tahmini ile saatlik bekleme haritası hesaplanmıştır. Tahmine "
        "dayalı yöntemin ortalama beklemesi uyarlanır yöntemle istatistiksel "
        "olarak aynı (p=0.97) çıkarken, en kötü %5 dilim %9 daha düşük "
        "(p=0.013) ve adalet ölçütü %4.5 daha yüksek (p=0.0018) bulunmuştur. "
        "Ani talep yığılması senaryosunda ise sabit yöntem, uyarlanır "
        "yönteme göre 67 kat daha kötü sonuç vermiştir.",
        STYLE_BODY,
    ))
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        "<b>Anahtar Kelimeler:</b> trafik ışığı, benzetim, uyarlanır "
        "kontrol, tahmine dayalı kontrol, acil öncelik, kuyruk teorisi, "
        "bekleme süresi.",
        STYLE_BODY,
    ))
    flow.append(PageBreak())
    return flow


def section_toc() -> list:
    flow = []
    flow.append(Paragraph("İÇİNDEKİLER", STYLE_H1))
    flow.append(Spacer(1, 0.4 * cm))
    entries = [
        ("ÖZET", "2"),
        ("1. GİRİŞ", "4"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;1.1. Problem Tanımı", "4"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;1.2. Amaç ve Kapsam", "4"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;1.3. Motivasyon", "4"),
        ("2. YÖNTEM VE TASARIM", "5"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;2.1. Benzetim Yaklaşımı", "5"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;2.2. Modelin Parçaları", "5"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;2.3. Dört Yöntemin Mantığı", "5"),
        ("3. UYGULAMA DETAYLARI", "7"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;3.1. Programın Yapısı", "7"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;3.2. Acil Araç Önceliği Nasıl Çalışır", "7"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;3.3. Tahmine Dayalı Yöntemin Geliştirilmesi", "7"),
        ("4. BULGULAR", "8"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;4.1. Sabit Yöntemin Sonuçları", "8"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;4.2. Dört Yöntemin Karşılaştırılması", "8"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;4.3. Ek Ölçütler", "10"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;4.4. Ani Talep Senaryosu", "11"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;4.5. Sonuçların İstatistiksel Güvenilirliği",
         "12"),
        ("5. TARTIŞMA", "13"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;5.1. Adalet Yanılgısı", "13"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;5.2. İlk Tasarımın Başarısızlığı ve "
         "Geliştirilmesi", "13"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;5.3. Çevresel Etkinin Değerlendirilmesi", "13"),
        ("6. SONUÇ VE GELECEK ÇALIŞMALAR", "14"),
        ("KAYNAKÇA", "15"),
        ("EKLER", "16"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;Ek A. GitHub Linki ve Proje Yapısı", "16"),
        ("&nbsp;&nbsp;&nbsp;&nbsp;Ek B. Ekran Görüntüleri", "17"),
    ]
    for title, page in entries:
        dots = "." * max(1, 75 - len(title.replace("&nbsp;", " ")) - 6)
        flow.append(Paragraph(
            f"{title}<font color='#9CA3AF'>&nbsp;{dots}&nbsp;</font>{page}",
            STYLE_TOC,
        ))
    flow.append(PageBreak())
    return flow


def section_introduction() -> list:
    flow = []
    flow.append(Paragraph("1. GİRİŞ", STYLE_H1))

    flow.append(Paragraph("1.1. Problem Tanımı", STYLE_H2))
    flow.append(Paragraph(
        "Şehir merkezi trafik kavşakları, yoğun saatlerde talebin iki "
        "katına çıktığı, kaynağın (yeşil ışığın) ise sabit kaldığı tipik "
        "bir kuyruk problemi olarak modellenebilir. Sabit zamanlı sinyal "
        "kontrolü, boş yöne bile 30 saniyelik yeşil periyodu vermeyi "
        "sürdüren basit bir çevrim mantığı kullanır. Bu yaklaşım, yoğun "
        "yöndeki kuyruğun birikmesine ve ortalama bekleme süresinin "
        "kabul edilemez seviyelere çıkmasına neden olur. Ayrıca acil "
        "araçların (ambulans, itfaiye, polis) ortalama bir sürücü kadar "
        "beklemesi can güvenliği açısından kritik bir sorundur.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Gerçek bir trafik ışığı sistemiyle deneme yapmak — parametre "
        "ayarı, alternatif algoritma denenmesi — yoğun trafik altında "
        "riskli ve etik değildir. Bu noktada olay tabanlı simülasyon "
        "(Discrete Event Simulation, DES) güvenli bir laboratuvar "
        "ortamı sunar; gerçek bir kayıp riski olmadan farklı kontrol "
        "stratejileri test edilebilir.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("1.2. Amaç ve Kapsam", STYLE_H2))
    flow.append(Paragraph(
        "Bu çalışmanın amacı, dört farklı trafik ışığı kontrol "
        "stratejisini Python tabanlı SimPy kütüphanesi ile modelleyip "
        "karşılaştırmaktır. Spesifik olarak şu sorulara yanıt aranmıştır:",
        STYLE_BODY_FIRST,
    ))
    bullets = [
        "Sabit zamanlı yöntemin, uyarlanır yönteme göre ne kadar "
        "performans kaybı yaşattığı,",
        "Acil araç önceliği uygulayan yöntemin, ambulans bekleme "
        "süresine etkisi,",
        "Gelecek talebi tahmin eden dördüncü bir yöntemin, uyarlanır "
        "yönteme göre ek bir kazanç sağlayıp sağlamadığı,",
        "Sabit zamanlı yöntemin, ani talep yığılması durumunda nasıl "
        "davrandığı,",
        "Dört yön arasındaki adalet ve karbondioksit (CO2) salımı "
        "açılarından yöntemler arası farklar.",
    ]
    for b in bullets:
        flow.append(Paragraph(f"&bull; {b}", STYLE_BULLET))

    flow.append(Paragraph("1.3. Motivasyon", STYLE_H2))
    flow.append(Paragraph(
        "Yönetici sezgisi çoğu zaman 'darboğazı çözmek için kaynak "
        "ekleyelim' yönünde olur. Ancak simülasyon, doğru kararın sezgi "
        "yerine veriye dayanmasını sağlar. Bu çalışmanın temel "
        "motivasyonu, aynı kavşak üzerinde dört farklı kontrol felsefesini "
        "aynı trafiğe uygulayıp nicel sonuçlarını göstermektir. Sunum "
        "hikâyemizin özeti: <i>'Aynı kavşak, dört farklı mantık, ambulans "
        "için yedi kat fark — doğru kararı sezgi değil simülasyon verisi "
        "gösterdi.'</i>",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())
    return flow


def section_method() -> list:
    flow = []
    flow.append(Paragraph("2. YÖNTEM VE TASARIM", STYLE_H1))

    flow.append(Paragraph(
        "2.1. Benzetim Yaklaşımı", STYLE_H2,
    ))
    flow.append(Paragraph(
        "Çalışma Python diliyle yazılmıştır. Benzetimi yürütmek için "
        "SimPy adlı bir kütüphane kullanılmıştır. Programın her parçası "
        "(araç üretici, sinyal denetimi, kavşaktan geçiş) ayrı bir süreç "
        "olarak çalışır ve benzetim zamanı bu süreçler üzerinden "
        "ilerletilir. Bu yöntem gerçek zamanda değil, sayısal olarak "
        "çalıştığı için 4 saatlik bir koşum yaklaşık 1-2 saniyede biter; "
        "5 tekrar ile dört kontrol yönteminin karşılaştırılması ise "
        "yaklaşık 30 saniye sürer.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Benzetim her olayı (araç varışı, yeşilin bitmesi, geçişin "
        "başlaması gibi) ayrı bir nokta olarak işler. Bu, trafik kavşağı "
        "gibi olayların belli anlarda meydana geldiği sistemleri "
        "doğal biçimde modellemeyi sağlar. Modeldeki tüm veri yapıları "
        "için gelen değerlerin doğruluğu çalışma sırasında kontrol "
        "edilmektedir (örneğin geliş hızı sıfırdan büyük olmalı).",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("2.2. Modelin Parçaları", STYLE_H2))
    flow.append(Paragraph("Modelin temel bileşenleri şunlardır:", STYLE_BODY))
    domain_table = _make_table(
        headers=["Bileşen", "Açıklama"],
        rows=[
            ["Yön", "Dört yön: Kuzey, Güney, Doğu, Batı"],
            ["Araç", "Numara, geldiği yön, tipi (normal/acil), varış ve "
                    "geçiş zamanları"],
            ["Geliş profili", "Saatlik değişen geliş hızları "
                             "(07-09 ve 17-19 yoğun)"],
            ["Ani yığın", "Belirli bir anda ve yönde gelen ek talep"],
            ["Sinyal ayarları", "Yeşil, sarı ve kırmızı süreleri ile alt-üst "
                              "sınırlar"],
            ["Veri toplayıcı", "Koşum boyunca olayları ve anlık ölçümleri "
                              "kaydeder"],
            ["Sonuç raporu", "Ortalama bekleme, en kötü dilim, adalet, CO2 "
                            "gibi özet bilgiler"],
        ],
        col_widths=[3.5 * cm, 11 * cm],
    )
    flow.append(domain_table)
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        "Geliş hızları literatür değerlerine yakındır. Kuzey ve Güney "
        "yönlerinde dakikada ortalama 0.4 araç (yoğun saatte 0.7-0.8); "
        "Doğu ve Batı yönlerinde 0.3 araç (yoğun saatte 0.6) gelmektedir. "
        "Gelen araçların %5'i acil araçtır (literatürde bu oran %2-7 "
        "arasında değişmektedir).",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("2.3. Dört Yöntemin Mantığı", STYLE_H2))

    flow.append(Paragraph("Sabit Zamanlı Yöntem", STYLE_H3))
    flow.append(Paragraph(
        "Klasik referans yöntem. Her yöne sırayla (Kuzey → Doğu → Güney "
        "→ Batı) 30 saniye yeşil, 3 saniye sarı, 1 saniye tüm yönlerin "
        "kırmızı kaldığı güvenlik aralığı verilir. Bir tam tur 136 "
        "saniye sürer ve trafik yoğunluğuna duyarsızdır. Boş yöne bile "
        "yeşil verirken, kalabalık yön sırasını beklemek zorundadır.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("Uyarlanır Yöntem", STYLE_H3))
    flow.append(Paragraph(
        "Her yeşil verilmeden önce dört yönün kuyruğuna bakılır ve en "
        "kalabalık yön seçilir. Yeşil süresi şu kurala göre belirlenir:",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "yeşil süresi = kuyruktaki araç sayısı × 3 saniye "
        "(en az 15, en fazla 60 saniye)",
        STYLE_CODE,
    ))
    flow.append(Paragraph(
        "En düşük 15 ve en yüksek 60 saniye sınırları, diğer yönlerin "
        "uzun süre yeşil bekleyişinde kalmamasını güvence altına alır.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("Tahmine Dayalı Yöntem", STYLE_H3))
    flow.append(Paragraph(
        "Uyarlanır yöntemin geliştirilmiş halidir. Son bir dakikadaki "
        "kuyruk uzunluklarına bakılarak yakın geleceğin (30 saniye "
        "sonrası) kuyruk uzunluğu tahmin edilir. Yön seçilirken bu "
        "tahmin de hesaba katılır:",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "puan = anlık kuyruk + 0.3 × (kuyruktaki artış miktarı)",
        STYLE_CODE,
    ))
    flow.append(Paragraph(
        "Anlık kuyruk her zaman temel alınır. Kuyruk artıyorsa ekstra "
        "puan eklenir; azalıyorsa bir ceza uygulanmaz. Buradaki 0.3 "
        "katsayısı, çok sayıda denemeyle en iyi sonucu veren değer "
        "olarak belirlenmiştir.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("Acil Öncelikli Yöntem", STYLE_H3))
    flow.append(Paragraph(
        "Uyarlanır yönteme ek bir kural getirir: her yarım saniyede tüm "
        "yönlerin kuyruğu denetlenir. Bir acil araç görüldüğünde, mevcut "
        "yeşil 5 saniye içinde kapatılır (sarı ve güvenlik aralığı "
        "geçilir) ve acil aracın bulunduğu yöne 15 saniye sabit yeşil "
        "verilir. Bu süre içinde acil araç mutlaka kavşağı geçer.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())
    return flow


def section_implementation() -> list:
    flow = []
    flow.append(Paragraph("3. UYGULAMA DETAYLARI", STYLE_H1))

    flow.append(Paragraph("3.1. Programın Yapısı", STYLE_H2))
    flow.append(Paragraph(
        "Sistemin merkezinde bir kavşak sınıfı vardır. Bu sınıf, dört "
        "yön için ayrı bekleme kuyrukları tutar. Her yön için ayrı bir "
        "araç üretici çalışır ve bu üreticiler, geliş profilinde "
        "belirtilen hıza göre yeni araçları kuyruğa ekler. Araç gelişleri "
        "birbirinden bağımsız olduğu için Poisson dağılımı kullanılmıştır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Yöntemler, kuyrukları her yarım saniyede bir kontrol eder. Bu "
        "basit yaklaşım, daha karmaşık olay yakalama yöntemlerine göre "
        "tercih edilmiştir; çünkü hem anlatması kolay (yarım saniyede "
        "bir kuyruğa bak) hem de hata ayıklaması basittir.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("3.2. Acil Araç Önceliği Nasıl Çalışır", STYLE_H2))
    flow.append(Paragraph(
        "Acil öncelikli yöntem, yeşil aktif olduğu sürece tüm yönleri "
        "yarım saniyede bir denetler. Başka bir yönde acil araç "
        "görülürse şu adımlar uygulanır:",
        STYLE_BODY_FIRST,
    ))
    pre_steps = [
        "Mevcut yeşil 5 saniye içinde kapatılır (kısa süreli sarı).",
        "1 saniye boyunca tüm yönler kırmızı (güvenlik aralığı).",
        "Acil aracın yönüne 15 saniye sabit yeşil verilir.",
        "Bu süre içinde acil araç kavşağı geçer.",
        "Ardından normal uyarlanır yönteme dönülür.",
    ]
    for s in pre_steps:
        flow.append(Paragraph(f"&bull; {s}", STYLE_BULLET))
    flow.append(Paragraph(
        "Bir koşum boyunca bu mekanizmanın kaç kez devreye girdiği "
        "ayrı bir göstergede tutulmaktadır.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("3.3. Tahmine Dayalı Yöntemin Geliştirilmesi", STYLE_H2))
    flow.append(Paragraph(
        "Tahmine dayalı yöntemin ilk tasarımında yalnızca gelecekteki "
        "kuyruk uzunluğu hesaba katılıyordu. Bu yaklaşım 16 farklı "
        "parametre denemesinden geçirilmiş, ancak hiçbiri uyarlanır "
        "yöntemi geçememiştir. Her denemede uyarlanır yönteme göre 2.5 "
        "ile 3.7 saniye arasında daha kötü sonuç alınmıştır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Sebep şudur: bu ilk tasarım, kuyruğun şu anki durumunu göz "
        "ardı edip yalnızca geleceğe bakıyordu. Bu olumsuz sonuç "
        "üzerine yöntem, hem şu anki kuyruğu hem de gelecekteki artışı "
        "birlikte değerlendiren karma bir yapıya dönüştürülmüştür:",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "puan = anlık kuyruk + 0.3 × kuyruktaki artış",
        STYLE_CODE,
    ))
    flow.append(Paragraph(
        "Bu sayede:",
        STYLE_BODY_FIRST,
    ))
    hybrid_features = [
        "Kuyruk değişmiyorsa: puan, anlık kuyruğa eşittir ve uyarlanır "
        "yöntemle aynı karar verilir.",
        "Kuyruk artıyorsa: puan biraz daha yüksek olur ve o yöne daha "
        "erken yeşil verilir.",
        "Kuyruk azalıyorsa: ek bir ceza uygulanmaz; yine anlık kuyruk "
        "esas alınır.",
    ]
    for f in hybrid_features:
        flow.append(Paragraph(f"&bull; {f}", STYLE_BULLET))

    flow.append(Paragraph(
        "Buradaki 0.3 sayısı, sıfır ile iki arasında çeşitli değerler "
        "denenerek belirlenmiştir. 0.1 ile 1.0 arasındaki değerler "
        "uyarlanır yöntemle çok yakın sonuç vermiş; bu aralığın ortası "
        "olan 0.3 seçilmiştir.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())
    return flow


def section_results() -> list:
    flow = []
    flow.append(Paragraph("4. BULGULAR", STYLE_H1))

    flow.append(Paragraph(
        "Tüm sonuçlar 5 farklı tekrarın ortalaması olarak verilmiştir; "
        "her tekrar 4 saatlik bir koşumdur. Aynı sonuçları üretmek için "
        "aşağıdaki komut kullanılabilir:",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4",
        STYLE_CODE,
    ))

    flow.append(Paragraph("4.1. Sabit Yöntemin Sonuçları", STYLE_H2))
    flow.append(Paragraph(
        "Sabit zamanlı kontrolün 4 saatlik sonuçları şunlardır:",
        STYLE_BODY,
    ))
    baseline_table = _make_table(
        headers=["Metrik", "Değer"],
        rows=[
            ["Ortalama bekleme", "43.72 sn"],
            ["En kötü %5 bekleme", "101.52 sn"],
            ["Acil araç bekleme", "40.43 sn"],
            ["Saatte geçen araç sayısı", "85.2"],
            ["Yön adaleti (0–1 arası)", "0.996"],
            ["Tahmini CO2 salımı", "5737 g"],
            ["Tam tur sayısı", "yaklaşık 106"],
        ],
        col_widths=[6 * cm, 4 * cm],
    )
    flow.append(baseline_table)
    flow.append(Spacer(1, 0.3 * cm))
    flow.append(Paragraph(
        "Sabit yöntem her yöne yaklaşık eşit bekleme dağıttığı için "
        "adalet ölçütü 0.996 gibi yüksek bir değer almaktadır; fakat "
        "ortalama bekleme 43.7 saniye gibi kabul edilemez bir "
        "seviyededir. Bu durum 'adalet yanılgısı' olarak Bölüm 5.1'de "
        "ele alınmaktadır.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("4.2. Dört Yöntemin Karşılaştırılması", STYLE_H2))
    flow.append(Paragraph(
        "Tablo 4.1 dört yöntemin temel sonuçlarını bir arada "
        "göstermektedir.",
        STYLE_BODY,
    ))
    comp_table = _make_table(
        headers=["Yöntem", "Ortalama", "En kötü %5", "Acil",
                 "Saatlik", "Adalet", "CO2 (g)"],
        rows=[
            ["Sabit Zamanlı", "43.72", "101.52", "40.43",
             "85.2", "0.996", "5737"],
            ["Uyarlanır", "9.70", "29.24", "7.20", "85.2", "0.852", "1271"],
            ["Tahmine Dayalı", "9.71", "26.51", "6.83",
             "85.2", "0.891", "1273"],
            ["Acil Öncelikli", "10.11", "29.91", "5.78",
             "85.3", "0.864", "1328"],
        ],
        col_widths=[3.0 * cm, 1.8 * cm, 2.0 * cm, 1.4 * cm,
                    1.6 * cm, 1.6 * cm, 1.7 * cm],
        col_align=["LEFT", "CENTER", "CENTER", "CENTER",
                   "CENTER", "CENTER", "CENTER"],
    )
    flow.append(comp_table)
    flow.append(Paragraph(
        "Tablo 4.1: 5 tekrar × 4 saat ortalaması. Bekleme süreleri "
        "saniye, geçiş ise saatte kavşağı geçen araç sayısıdır.",
        STYLE_CAPTION,
    ))

    flow.append(_figure(
        "results/comparison_emergency_wait.png",
        "Şekil 4.1: Acil araç bekleme süresi karşılaştırması. Sabit "
        "yöntemde 40.4 saniye olan bekleme, uyarlanır yöntemde 7.2 "
        "saniyeye, acil öncelikli yöntemde 5.8 saniyeye düşmektedir "
        "(yedi kat azalma).",
    ))

    flow.append(Paragraph(
        "Karşılaştırmadan çıkan ana sonuçlar:",
        STYLE_BODY,
    ))
    findings = [
        "Sabit yöntemden uyarlanır yönteme geçildiğinde ortalama "
        "bekleme %77.8 azalmaktadır (43.7 → 9.7 saniye).",
        "Sabit yöntemden acil öncelikli yönteme geçildiğinde acil araç "
        "bekleme süresi %85.7 azalmaktadır (40.4 → 5.8 saniye) — yedi "
        "kat azalma.",
        "Saatte geçen araç sayısı tüm yöntemlerde yaklaşık 85'tir; "
        "çünkü araç gelişleri yöntemden bağımsızdır ve yöntemin görevi "
        "bekleme süresini kısaltmaktır, gelen aracı durdurmak değil.",
        "Tahmine dayalı yöntem ortalama beklemede uyarlanır yöntemle "
        "neredeyse aynı sonucu vermiş (9.71 ile 9.70 saniye), ancak en "
        "kötü %5 dilimde %9.3 daha iyi (26.51 / 29.24) ve adalet "
        "ölçütünde %4.5 daha yüksek (0.891 / 0.852) çıkmıştır.",
    ]
    for f in findings:
        flow.append(Paragraph(f"&bull; {f}", STYLE_BULLET))

    flow.append(PageBreak())

    flow.append(Paragraph("4.3. Ek Ölçütler", STYLE_H2))
    flow.append(Paragraph("Bekleme Süresi Dilimleri", STYLE_H3))
    flow.append(Paragraph(
        "Ortalama tek başına yeterli bir ölçü değildir. Uyarlanır "
        "yöntemde bekleme süreleri dilimlere göre şöyledir:",
        STYLE_BODY,
    ))
    pct_table = _make_table(
        headers=["Dilim", "Değer (saniye)"],
        rows=[
            ["Ortanca (sürücülerin yarısı altında)", "6.17"],
            ["%75 dilim", "13.88"],
            ["%90 dilim", "18.08"],
            ["%95 dilim (en kötü %5)", "24.21"],
            ["%99 dilim (en kötü %1)", "45.74"],
        ],
        col_widths=[7 * cm, 4 * cm],
    )
    flow.append(pct_table)
    flow.append(Paragraph(
        "Sürücülerin yarısı 6 saniyede geçmesine rağmen, her 20 sürücüden "
        "1'i 24 saniye, her 100'den 1'i 46 saniye beklemektedir. Bu yüzden "
        "yalnızca ortalamaya değil, en kötü %5'in nasıl beklediğine de "
        "bakmak gereklidir.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("Yön Adaleti Ölçütü", STYLE_H3))
    flow.append(Paragraph(
        "Bu ölçüt, bekleme süresinin dört yön arasında ne kadar eşit "
        "dağıldığını gösterir. Değeri 0 ile 1 arasındadır: 1'e yakın "
        "olması her yöndeki sürücülerin yaklaşık aynı süreyi beklediğini, "
        "0.25 ise yalnızca tek bir yönün avantajlı olduğunu gösterir. "
        "Sabit yöntemde bu değerin 0.996 olması Bölüm 5.1'de açıklanan "
        "bir yanılgıya yol açmaktadır.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("Çevresel Etki: Yakıt ve CO2", STYLE_H3))
    flow.append(Paragraph(
        "Beklerken motoru çalışan araçların harcadığı yakıt, literatür "
        "değerleri kullanılarak tahmin edilmektedir. Çevre Koruma "
        "Ajansı'nın (EPA) verilerine göre boşta çalışan bir otomobil "
        "saatte yaklaşık 0.6 litre yakıt tüketmekte ve her litre benzin "
        "yaklaşık 2.3 kg karbondioksit (CO2) açığa çıkarmaktadır. Bu "
        "değerlerle tüm araçların toplam bekleme süresinden tahmini "
        "CO2 salımı hesaplanmıştır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Sabit yöntemin 5737 gram CO2 salımı, uyarlanır yöntemin 1271 "
        "gramı ile karşılaştırıldığında yaklaşık <b>4 katı daha fazla "
        "kirletici</b> üretildiğini ortaya koymaktadır. Ortalama bir "
        "otomobilin kilometre başına yaklaşık 120 gram CO2 saldığı "
        "düşünüldüğünde, sabit yöntemin ürettiği fazla salım yaklaşık "
        "37 kilometrelik bir araç yolculuğuna denk gelmektedir.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())

    flow.append(Paragraph("4.4. Ani Talep Senaryosu", STYLE_H2))
    flow.append(Paragraph(
        "Standart koşumun yarısında (30. dakika) 30 dakika boyunca "
        "Kuzey yönüne dakikada 20 araç ek talep gönderilerek ani bir "
        "talep yığılması oluşturulmuştur. Bu durum okul çıkışı, maç sonu "
        "stadyum trafiği veya kaza nedeniyle yönlendirme gibi gerçek "
        "hayatta sıkça yaşanan örnekleri temsil etmektedir.",
        STYLE_BODY_FIRST,
    ))
    burst_table = _make_table(
        headers=["Yöntem", "Ort. (sn)", "En kötü %5 (sn)",
                 "Acil (sn)", "Adalet"],
        rows=[
            ["Sabit Zamanlı", "1138.89", "3122.32", "1067.54", "0.293"],
            ["Uyarlanır", "16.84", "28.09", "19.39", "0.864"],
            ["Tahmine Dayalı", "16.69", "27.46", "22.40", "0.875"],
            ["Acil Öncelikli", "17.46", "32.00", "10.13", "0.892"],
        ],
        col_widths=[3.5 * cm, 2.0 * cm, 2.6 * cm, 2.0 * cm, 2 * cm],
    )
    flow.append(burst_table)
    flow.append(Paragraph(
        "Tablo 4.2: Ani talep senaryosu sonuçları (5 tekrar × 4 saat).",
        STYLE_CAPTION,
    ))

    flow.append(_figure(
        "results/comparison_burst.png",
        "Şekil 4.2: Ani talep senaryosunda ortalama bekleme ve en kötü "
        "%5 dilim. Logaritmik ölçek kullanılmıştır (sabit yöntemin "
        "değeri diğer yöntemlerle aynı eksene sığmamaktadır).",
    ))

    flow.append(Paragraph(
        "Bulgu: Sabit yöntem, ani talep senaryosunda <b>uyarlanır "
        "yönteme göre 67 kat daha kötü</b> ortalama bekleme üretmiştir "
        "(1139 saniyeye karşı 16.84 saniye). En kötü %5 dilim 3122 "
        "saniyeyi (yaklaşık 52 dakika) bulmuştur. Bu sonuç, sabit "
        "yöntemin talebin hızla değiştiği durumlarda ciddi bir performans "
        "çöküşü yaşadığını ortaya koymaktadır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Tahmine dayalı yöntem bu senaryoda da uyarlanır yönteme yakın "
        "bir ortalama bekleme süresi vermiştir (16.69 ile 16.84 saniye). "
        "Ancak en kötü %5 dilimde daha iyi (27.46 ile 28.09) ve adalet "
        "ölçütünde daha yüksek (0.875 ile 0.864) sonuç elde edilmiştir. "
        "Tahmine dayalı yöntemin eğilim yakalama özelliği, ani talep "
        "yığılması durumlarında daha belirgin biçimde ortaya çıkmıştır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())

    flow.append(Paragraph("4.5. Sonuçların İstatistiksel Güvenilirliği", STYLE_H2))
    flow.append(Paragraph(
        "Tahmine dayalı yöntemin uyarlanır yönteme göre 'en kötü %5 "
        "dilimi' ve 'adalet' ölçütlerinde gözlenen küçük iyileşmenin "
        "gerçekten bir iyileşme mi yoksa rastlantı sonucu mu olduğunu "
        "anlamak için Mann-Whitney U adlı istatistiksel test "
        "uygulanmıştır. Bu test, verilerin belirli bir dağılıma uymak "
        "zorunda olmadığı durumlarda da güvenle kullanılabilir.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "10 tekrar × 4 saat koşumun sonuçları aşağıdaki tabloda "
        "gösterilmiştir. p değeri ne kadar küçükse, gözlenen farkın "
        "rastlantı eseri olma olasılığı o kadar düşüktür.",
        STYLE_BODY,
    ))
    stats_table = _make_table(
        headers=["Karşılaştırma", "p değeri", "Anlamlılık", "Yorum"],
        rows=[
            ["Uyarlanır ile Tahmine Dayalı ortalama bekleme", "0.97",
             "anlamlı değil", "ortalama kaybedilmedi"],
            ["Tahmine Dayalı'nın en kötü %5 dilimi daha iyi", "0.013",
             "anlamlı", "kötü uçta gerçek iyileşme"],
            ["Tahmine Dayalı adalet daha yüksek", "0.0018",
             "çok anlamlı", "yön adaletinde belirgin iyileşme"],
            ["Sabit ortalama, Uyarlanır'dan büyük", "<0.001",
             "çok güçlü", "ana sonuç istatistiksel olarak çok güçlü"],
        ],
        col_widths=[5.0 * cm, 1.6 * cm, 2.3 * cm, 4.5 * cm],
        col_align=["LEFT", "CENTER", "CENTER", "LEFT"],
    )
    flow.append(stats_table)
    flow.append(Paragraph(
        "Tablo 4.3: İstatistiksel test sonuçları. p değeri 0.05'in "
        "altındaysa fark 'anlamlı', 0.01'in altındaysa 'çok anlamlı' "
        "kabul edilmiştir.",
        STYLE_CAPTION,
    ))
    flow.append(Paragraph(
        "Birden fazla karşılaştırma yapıldığı için daha sıkı bir eşik "
        "(0.05/4 = 0.0125) kullanılsa bile, adalet sonucu (0.0018) çok "
        "rahat geçer, en kötü %5 sonucu (0.013) ise sınırda kalır. Bu "
        "durum, tahmine dayalı yöntemin uyarlanır yönteme göre küçük "
        "ama gerçek bir iyileşme sağladığını göstermektedir; sonuçlar "
        "rastlantıya bağlanamaz.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())
    return flow


def section_discussion() -> list:
    flow = []
    flow.append(Paragraph("5. TARTIŞMA", STYLE_H1))

    flow.append(Paragraph("5.1. Adalet Yanılgısı", STYLE_H2))
    flow.append(Paragraph(
        "Sabit zamanlı yöntemin adalet ölçütü 0.996 değerine ulaşarak "
        "dört yöntem içinde en yüksek olanıdır. İlk bakışta bu, sabit "
        "yöntemin 'en adil yöntem' olduğu izlenimini verir. Ancak bu "
        "ölçüt yalnızca dört yön arasındaki bekleme süresinin ne kadar "
        "eşit dağıldığını ölçer; bekleme süresinin kendisinin iyi mi "
        "yoksa kötü mü olduğu hakkında bilgi vermez.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Sabit yöntemde her yön yaklaşık 43.7 saniye beklediği için "
        "dağılım eşittir; ancak bu eşit dağılım aslında "
        "<i>herkesi eşit ölçüde kötü bekletmek</i> anlamına gelmektedir. "
        "Uyarlanır yöntemin adaleti (0.852) bir miktar daha düşüktür "
        "çünkü kalabalık yönlere daha çok yeşil verilmektedir. Buna "
        "karşın ortalama bekleme süresi 9.7 saniyeye inmiştir. Yani "
        "<b>adalet ölçütü ile ortalama bekleme birlikte değerlendirilmelidir</b>: "
        "küçük bir adalet farkına karşın elde edilen büyük süre kazancı "
        "toplam fayda açısından çok daha değerlidir.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Tahmine dayalı yöntem ise bu dengeyi daha da iyileştirmiştir. "
        "Uyarlanır yöntemle aynı ortalama bekleme süresini korurken, "
        "adalet ölçütünü 0.852'den 0.891'e yükseltmiştir. Bu fark "
        "istatistiksel olarak da anlamlı bulunmuştur (p=0.0018).",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph(
        "5.2. İlk Tasarımın Başarısızlığı ve Geliştirilmesi", STYLE_H2,
    ))
    flow.append(Paragraph(
        "Tahmine dayalı yöntemin ilk hâlinde yalnızca gelecekteki "
        "kuyruk uzunluğuna göre karar veriliyordu. 16 farklı parametre "
        "kombinasyonu denenmiş, ancak hiçbiri uyarlanır yöntemi "
        "geçememiştir. Bu, tasarımın başarısız olduğunu kabul edip "
        "yöntemi yenilemenin gerekli olduğunu gösteren bir sonuçtu.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Başarısızlığın nedeni şudur: ilk tasarım, şu anki kuyruğu "
        "görmezden gelip yalnızca gelecekteki tahminle karar veriyordu. "
        "Örneğin bir yönde şu an 10 araç bekliyor olsa bile, tahmin "
        "düşüş gösteriyorsa (örneğin 2 araca düşecek diyorsa) o yön "
        "atlanıyordu. Oysa o 10 araç hâlâ kuyrukta bekleyen gerçek "
        "araçlardı.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Geliştirilmiş tasarım bu hatayı ortadan kaldırmıştır: artık "
        "şu anki kuyruk temel alınmakta, yalnızca kuyrukta bir <b>artış</b> "
        "varsa buna ek bir puan eklenmektedir. Kuyruk azalıyorsa "
        "herhangi bir ceza verilmemektedir. Olumsuz bir sonuçtan yola "
        "çıkarak daha iyi bir tasarıma ulaşmak, çalışmanın yöntemsel "
        "katkılarından biridir.",
        STYLE_BODY_FIRST,
    ))

    flow.append(Paragraph("5.3. Çevresel Etkinin Değerlendirilmesi", STYLE_H2))
    flow.append(Paragraph(
        "CO2 ve yakıt hesabı doğrudan ölçümle değil, literatürdeki "
        "ortalama değerlerle yapılmıştır (saatte 0.6 litre boşta yakıt "
        "tüketimi, litre başına 2310 gram CO2). Mutlak rakamlar "
        "tartışılabilir; çünkü gerçekte bazı araçlar kavşakta motoru "
        "kapatır, ortalama yakıt tüketimi araç tipine göre değişir. "
        "Ancak yöntemler arası göreli karşılaştırma sağlamdır: sabit "
        "yöntem, uyarlanır yönteme göre dört kat daha fazla salım "
        "üretmektedir.",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "Dört saatlik bir koşumda sabit yöntemin uyarlanır yönteme "
        "göre 4466 gram fazla CO2 üretmesi, ortalama bir otomobille "
        "yaklaşık 37 kilometre fazladan yol gitmenin yarattığı kirliliğe "
        "denk gelmektedir. Bu sonuç, trafik ışığı tasarımının yalnızca "
        "süre değil, çevre boyutuyla da değerlendirilmesi gerektiğini "
        "ortaya koymaktadır.",
        STYLE_BODY_FIRST,
    ))
    flow.append(PageBreak())
    return flow


def section_conclusion() -> list:
    flow = []
    flow.append(Paragraph("6. SONUÇ VE GELECEK ÇALIŞMALAR", STYLE_H1))
    flow.append(Paragraph(
        "Bu çalışmada Python ile yazılmış bir benzetim programı "
        "kullanılarak dört yollu bir trafik kavşağında dört farklı "
        "ışık kontrol yöntemi karşılaştırılmıştır. Elde edilen başlıca "
        "sonuçlar şunlardır:",
        STYLE_BODY_FIRST,
    ))
    conclusions = [
        "<b>Uyarlanır yöntem</b>, sabit yönteme göre büyük bir iyileşme "
        "sağlamaktadır: ortalama bekleme süresi %77.8 azalmış, CO2 "
        "salımı %78 düşmüştür.",
        "<b>Acil öncelikli yöntem</b> ambulans bekleme süresini %85.7 "
        "kısaltmaktadır (40.4 → 5.8 saniye). Bu yedi kat azalma, hayat "
        "kurtarıcı bir öneme sahip olabilir.",
        "<b>Tahmine dayalı yöntem</b>, uyarlanır yöntemle ortalama "
        "beklemede aynı sonucu vermekle birlikte (p=0.97) en kötü %5 "
        "dilimde %9 ve adalet ölçütünde %4.5 anlamlı iyileşme "
        "sağlamaktadır (sırasıyla p=0.013 ve p=0.0018).",
        "<b>Ani talep senaryosunda</b> sabit yöntem 67 kat daha kötü "
        "sonuç vermektedir. Bu, gerçek hayatta okul çıkışı veya kaza "
        "sonrası yönlendirme gibi durumlarda neden uyarlanır sistemlerin "
        "tercih edildiğini sayısal olarak ortaya koymaktadır.",
        "<b>Adalet yanılgısı</b>, sabit yöntemin yüksek adalet "
        "değerine rağmen aslında kötü performans gösterdiğini ve bu "
        "ölçütün tek başına yorumlanamayacağını göstermektedir.",
    ]
    for c in conclusions:
        flow.append(Paragraph(f"&bull; {c}", STYLE_BULLET))

    flow.append(Paragraph("Gelecek Çalışmalar", STYLE_H2))
    future = [
        "Bağlı kavşak ağı modellemesi (yeşil dalga ve birbirini etkileyen "
        "kavşaklar).",
        "Yaya ve bisikletli modunun eklenmesi.",
        "Sola/sağa dönüş şeritleri ile çoklu şerit modellemesi.",
        "Pekiştirmeli öğrenme yöntemiyle çalışan bir kontrolcü — "
        "sabit kurallar yerine deneme-yanılma ile öğrenen bir yapı.",
        "Gerçek hastane/şehir trafik verisi ile parametre kalibrasyonu.",
        "Hava koşulları (yağmur, sis) ve gece-gündüz etkilerinin "
        "eklenmesi.",
    ]
    for f in future:
        flow.append(Paragraph(f"&bull; {f}", STYLE_BULLET))

    flow.append(PageBreak())
    return flow


def section_references() -> list:
    flow = []
    flow.append(Paragraph("KAYNAKÇA", STYLE_H1))

    refs = [
        "[1] Team SimPy. (2024). <i>SimPy 4.1 Documentation</i>. "
        "https://simpy.readthedocs.io/",
        "[2] Jain, R., Chiu, D.M., Hawe, W.R. (1984). A Quantitative "
        "Measure of Fairness and Discrimination for Resource Allocation "
        "in Shared Computer Systems. <i>DEC Research Report</i>, TR-301.",
        "[3] Sims, A.G., Dobinson, K.W. (1980). The Sydney Coordinated "
        "Adaptive Traffic (SCAT) System Philosophy and Benefits. "
        "<i>IEEE Transactions on Vehicular Technology</i>, 29(2), 130-137.",
        "[4] Hunt, P.B., Robertson, D.I., Bretherton, R.D., Royle, M.C. "
        "(1982). The SCOOT On-Line Traffic Signal Optimisation Technique. "
        "<i>Traffic Engineering & Control</i>, 23(4), 190-192.",
        "[5] Mann, H.B., Whitney, D.R. (1947). On a Test of Whether One "
        "of Two Random Variables is Stochastically Larger than the Other. "
        "<i>The Annals of Mathematical Statistics</i>, 18(1), 50-60.",
        "[6] U.S. Environmental Protection Agency (EPA). (2018). "
        "<i>Greenhouse Gas Emissions from a Typical Passenger Vehicle</i>. "
        "EPA-420-F-18-008.",
        "[7] Pydantic Team. (2024). <i>Pydantic v2 Documentation</i>. "
        "https://docs.pydantic.dev/",
        "[8] McKinney, W. (2010). Data Structures for Statistical "
        "Computing in Python. <i>Proceedings of the 9th Python in Science "
        "Conference</i>, 56-61.",
        "[9] Hunter, J.D. (2007). Matplotlib: A 2D Graphics Environment. "
        "<i>Computing in Science & Engineering</i>, 9(3), 90-95.",
        "[10] Streamlit Inc. (2024). <i>Streamlit Documentation</i>. "
        "https://docs.streamlit.io/",
    ]
    for r in refs:
        flow.append(Paragraph(
            r,
            _style("ref", fontSize=10, leading=13, leftIndent=20,
                   firstLineIndent=-20, spaceAfter=6, alignment=TA_LEFT),
        ))
    flow.append(PageBreak())
    return flow


def section_appendix() -> list:
    flow = []
    flow.append(Paragraph("EKLER", STYLE_H1))

    flow.append(Paragraph("Ek A. GitHub Linki ve Proje Yapısı", STYLE_H2))
    flow.append(Paragraph(
        "Tüm kaynak kodu, testler, dokümantasyon ve sonuçlar aşağıdaki "
        "GitHub deposunda mevcuttur:",
        STYLE_BODY_FIRST,
    ))
    flow.append(Paragraph(
        "<b>github.com/Lightfield0/intersection-sim</b>",
        _style("gh", fontSize=12, leading=16, alignment=TA_CENTER,
               textColor=colors.HexColor("#1B4D3E"), fontName=FONT_BOLD,
               spaceAfter=10, spaceBefore=6),
    ))
    flow.append(Paragraph("Proje yapısı (özet):", STYLE_BODY))
    proj_struct = """intersection-sim/
├── dashboard.py                 # Etkileşimli panel (7 sekme)
├── docs/
│   ├── presentation.pdf         # 10 slayt sunum
│   ├── rapor.pdf                # Bu rapor
│   ├── faq.md                   # SSS + yanıtlar
│   ├── scenario-findings.md     # Detaylı bulgular
│   └── sunum-notlari.md         # Sunum konuşma metni
├── results/
│   ├── comparison.csv           # 4 yöntem × 5 tekrar temel sonuçlar
│   ├── comparison_burst.csv     # Ani talep senaryosu sonuçları
│   └── comparison_*.png         # Karşılaştırma grafikleri
├── scripts/
│   ├── build_presentation_pdf.py
│   ├── build_report_pdf.py      # Bu raporu üretir
│   └── capture_screenshots.py
├── src/intersection_sim/
│   ├── controllers/             # fixed, adaptive, predictive, preemptive
│   ├── domain/                  # Direction, Vehicle, SignalConfig
│   ├── metrics/                 # MetricsCollector + Report
│   ├── scenarios/               # 4 senaryo + ani talep + karşılaştırma komutu
│   ├── simulation/              # Intersection, arrivals, crossing
│   └── plots/                   # matplotlib karşılaştırma grafikleri
└── tests/                       # 92 birim test (mypy strict, ruff temiz)"""
    flow.append(Paragraph(
        proj_struct.replace("\n", "<br/>").replace(" ", "&nbsp;"),
        STYLE_CODE,
    ))

    flow.append(PageBreak())

    flow.append(Paragraph("Ek B. Ekran Görüntüleri", STYLE_H2))
    flow.append(Paragraph(
        "Çalışmanın etkileşimli paneli yedi sekmeden oluşur. Aşağıda "
        "seçilen sekmelerin ekran görüntüleri yer almaktadır.",
        STYLE_BODY_FIRST,
    ))
    screenshots = [
        ("results/screenshots/01_kpi_summary.png",
         "Şekil B.1: Senaryo Çalıştır sekmesi. Üst sırada temel "
         "göstergeler (ortalama bekleme, acil araç beklemesi, saatte "
         "geçen araç, acil müdahale sayısı), alt sırada ek göstergeler "
         "(en kötü %5 bekleme, yön adaleti, tahmini CO2 salımı, toplam "
         "bekleme süresi) yer alır. Altta yön bazlı bekleme grafiği "
         "ve zaman serisi gösterilir."),
        ("results/screenshots/02_comparison.png",
         "Şekil B.2: Yöntem Karşılaştırma sekmesi. Dört yöntemin temel "
         "sonuçları tablo halinde ve altta karşılaştırma grafikleri "
         "olarak sunulur."),
        ("results/screenshots/03_distribution.png",
         "Şekil B.3: Dağılım ve Çevre sekmesi. Bekleme süresi dilimleri "
         "tablosu, dağılım ve kutu grafikleri, çevresel etki (yakıt, "
         "CO2) blokları."),
        ("results/screenshots/04_heatmap.png",
         "Şekil B.4: Saatlik Bekleme Isısı sekmesi. Yön ve saat "
         "bilgisine göre ortalama bekleme süresinin renkli haritası, "
         "yanında saatlik geçen araç sayısı."),
        ("results/screenshots/05_burst.png",
         "Şekil B.5: Ani Talep Senaryosu sekmesi. Sabit zamanlı "
         "yöntemin uyarlanır yönteme göre 67 kat daha kötü performans "
         "gösterdiği logaritmik ölçekli karşılaştırma grafiği."),
        ("results/screenshots/07_intersection_view.png",
         "Şekil B.6: Kavşak Görseli sekmesi. Koşumun seçilen anındaki "
         "kavşak durumu (yeşil yön ve her yöndeki kuyruk uzunluğu) "
         "yukarıdan görünüm olarak çizilir; kaydırma çubuğu ile farklı "
         "zamanlara bakılabilir."),
    ]
    for path, caption in screenshots:
        flow.append(_figure(path, caption, max_width_cm=14))
        flow.append(Spacer(1, 0.2 * cm))

    return flow


# ---------- Build ----------------------------------------------------------


def build() -> Path:
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        title="Akıllı Kavşak Trafik Işığı Simülasyonu - Final Raporu",
        author="Nihal Kemer, Mehmet Furkan Güneş",
        subject="Benzetim Programları Final Projesi 2026",
    )

    story: list = []
    story.extend(section_cover())
    story.extend(section_abstract())
    story.extend(section_toc())
    story.extend(section_introduction())
    story.extend(section_method())
    story.extend(section_implementation())
    story.extend(section_results())
    story.extend(section_discussion())
    story.extend(section_conclusion())
    story.extend(section_references())
    story.extend(section_appendix())

    doc.build(story, onFirstPage=_on_cover, onLaterPages=_on_page)
    return OUTPUT_PATH


if __name__ == "__main__":
    out = build()
    size_kb = out.stat().st_size / 1024
    print(f"wrote {out} ({size_kb:.1f} KB)")
