# Sunum Notlari — Akıllı Kavşak Trafik Işığı Simülasyonu

**Hazırlayanlar:** Nihal Kemer · Mehmet Furkan Güneş
**Toplam süre:** ~13 dakika · **Slayt sayısı:** 10
· **Demo:** Slayt 10'da (1.5–2 dakika)

Bu notlar PDF'te gorunmuyor. Sunum sırasında telefonundan veya ikinci
ekrandan okuyabilirsin. Her slaytin altinda **tam konusma metni** + **olası
sorular ve cevaplari** var. Akıcı okumak için paragraf biçimi kullanildi —
"merhaba", "simdi", "bir sonraki slaytta" gecisleri dahil. Detayli SSS için
`docs/faq.md` dosyasini ac.

---

## Slayt 1 — Kapak (30 sn)

### Konusma metni
"Merhaba, biz Nihal Kemer ve Mehmet Furkan Güneş. Bugün size finalde sunmak üzere hazırladığımız
**Akıllı Kavşak Trafik Işığı Simülasyonu** projesini anlatacağım. Sağdaki
şema 4 yollu bir kavsagi temsil ediyor — yeşil daire o an aktif yeşil ışığı,
kirmiziler ise diger üç yondeki bekleyenleri gösteriyor.

Projenin amacı tek bir kelimeyle özetlenebilir: **karşılaştırma**. Ayni
kavsakta üç farkli trafik ışığı kontrol stratejisini calistirdik — sabit
zamanlı, uyarlanır ve acil öncelikli — ve sayilarla hangisi daha iyi diye
sorduk. Sonuç bizi biraz şaşırttı: ambulans bekleme süresi acisindan
**dört kontrolcü arasinda yedi kat fark** çıktı.

Yaklaşık on dakika surecek. Sonunda dashboard üzerinden canli demo da
yapacagim, sorulara hazırım."

### Olası sorular
**S: Projeyi tek basina mi yaptin?**
C: Ekip çalışması. Kod yazımı sırasında AI asistandan destek aldık
(spec yazma, hata ayiklama). Mimari kararlar, senaryo seçimi, parametre
ayarlari, sunum hikayesi ekipten çıktı.

---

## Slayt 2 — Neden Trafik Işığı Optimizasyonu? (60 sn)

### Konusma metni
"Bu projeyi yapma motivasyonumuz dört başlık altinda toplanir.

Birincisi, **trafik sıkışıklığı** somut bir sorun. Şehir merkezi yoğun
saatte talep iki kati. Sabit isiklar bu degisime tepki vermiyor; boş yöne
bile eşit yeşil veriyor.

İkincisi, **acil müdahale gecikmesi** can kritik. Bir ambulansın kavsakta
40 saniye beklemesi tipi bir olaya göre hayat kaybı anlamina gelebilir.
Trafik ışıkları acil araclari farkindali olmalı.

Üçüncüsü, **sezgi yanilir**. Bir yonetici 'daha çok yeşil verelim' derken
çoğu zaman yanlis kavsaga öncelik veriyor. Hangi yön ne kadar yoğun?
Hangisi onceliklendirilmeli? Bu sorulara icgudune göre degil veriye göre
cevap vermek gerekiyor.

Dördüncüsü, **gerçek hayatta deneme yapmak imkânsız**. Yoğun trafikte
ayar denemek riskli. İşte tam bu yuzden simülasyon devreye giriyor —
guvenli bir laboratuvarda 'ya böyle yapsaydik?' sorusunun cevabini
arıyoruz."

### Olası sorular
**S: Bu calismayi gerçek bir kavsakta kullanabilir miyiz?**
C: Doğrudan degil. Gerçek dünya parametreleri — sensor, kamera, donanım
maliyeti — modelin disinda. Ama benzer mantikla gerçek sistemler kuruluyor.
SCATS ve SCOOT sistemleri trafiklerin akisini canli olarak uyarlanır olarak
yonetiyor. Bizim model bu sistemlerin basitlestirilmis bir tasarimi.
## Slayt 3 — Araç Akışı (60 sn)

### Konusma metni
"Bu slayt projenin omurgasini gösteriyor. Sol tarafta dört yön var —
Kuzey, Doğu, Güney, Batı. Her yön için ayrı bir kuyruk; araçlar
geldiklerinde o yön kuyruguna giriyor.

Ortada KAVSAK + SINYAL kutusu. Kontrolcü burada karar verir: hangi yöne
yeşil verilecek, kac saniye surecek? Sabit kontrolcü sırayla dolanir,
uyarlanır kuyruk uzunluğuna bakar, acil öncelikli ise acil araç varsa
prioriteyi degistirir. Yeşil verilen yondeki araçlar tek tek karşıya
geciyor — her gecis 2 saniye suruyor.

Çıkış tarafta hangi yönden gelen olursa olsun sistemi terk ediyor.
Throughput dedigimiz bu — saatte kac araç karşıya geciyor.

Sağ tarafta kırmızı ok ile **acil araç vurgusu** var. Acil araç (ambulans,
itfaiye, polis) geldiginde, eger kavsakta başka yön yeşil ise, o yeşil 5
saniyede kapatilir ve acil aracın yönü yesile cevriliyor. Buna preemption
diyoruz."

### Olası sorular
**S: Kavşak icinde araçlar nasil siralaniyor?**
C: Her yön kuyruğu FIFO — geliş sirasiyla. Tek istisna acil araçlar:
yön icinde de öncelik almazlar (gerçek hayatta sirena calar sıra atlarlar
ama biz bu basitlikten kaçtık). Önceliği sadece sinyal kontrolu düzeyinde
ele aliyoruz.

---

## Slayt 4 — Domain Modeli (50 sn)

### Konusma metni
"Sayilar boş yere secilmedi — gerçek dünya gozlemlerine yakin tutuldu.

Sol tabloda **yön bazli araç geliş hızı**. Kuzey ve Güney yönleri biraz
daha yoğun (0.4 araç dakika), Doğu ve Batı yönleri biraz sakin (0.3).
Yoğun saatlerde — yani sabah 07'den 09'a, akşam 17'den 19'a — bu hizlar
neredeyse iki katina cikiyor. Şehir trafiginde gözlenen pattern bu.

Sağ tablo **sinyal süreleri**. Bir yön için tam dongu: 30 saniye yeşil, 3
saniye sarı (gecis), 1 saniye tüm kırmızı (guvenlik buffer'i). Dört yön
için toplam: 4 çarpı 34 esittir **136 saniye** bir tam çevrim. Bu sabit
kontrolcünün dönüş süresi.

Altta turuncu kutuda: **araç tipi dağılımı yüzde 95 normal, yüzde 5 acil
araç**. Bu literaturde yaygin kabul edilen orana yakın. Ayrıca yoğun
saatler 7-9 sabah ve 17-19 akşam — gerçek sehirlerdeki rush hour."

### Olası sorular
**S: %5 acil araç orani nereden geldi?**
C: ESI literaturunden ve trafik yogunluk raporlarindan tahmin. Gerçek
sehirlerde bu oran genelde %2-7 arasinda. %5 makul bir orta nokta.
Parametre ayarlanabilir, comparison.csv'yi yeni oranla yeniden uretmek
30 saniye surer.

---

## Slayt 5 — Baseline: Sabit Zamanlı Kontrol (75 sn)

### Konusma metni
"Sabit kontrolcuyle 4 saat boyunca 5 farkli seed'le simülasyonu kosturduk.
Sonuçlar dört büyük kutuda ozetleniyor.

**Ortalama bekleme 43.7 saniye** — kırmızı renkli çünkü iyi degil. Ufak bir
araç kavsakta neredeyse bir dakika bekliyor. **Acil bekleme 40.4 saniye**
koyu kırmızı çünkü bu **ciddi sorun**. Bir ambulansi 40 saniye bekletmek
hayat kaybı demek.

**Throughput saatte 85 araç** — bu kötü degil, kavşak araclari geciriyor.
**Tam çevrim 136 saniye** sabit, hiçbir sey degismez. Yoğun yön boş yön
ayni sureyi alır.

Altta bar chartta yön bazli ortalama bekleme süresi var. Kuzey 45.5
saniye, Batı 47.2 saniye — bu iki yön daha yoğun oldugu için daha çok
bekliyor. Doğu ve Güney 39 saniye civarinda — daha sakin yönler.

Önemli olan sunu fark etmek: **sabit kontrol yön yoğunluğuna kor**. Hep
ayni sırayla, ayni sureyle, sırası gelen yön yeşil aliyor. Bu zayifligi
bir sonraki slaytta cozecegiz."

### Olası sorular
**S: Bu sayilar tek bir kosumdan mi?**
C: Hayir, **5 seed ortalaması**. Her seed farkli rastgele araç sırası
üretir; ortalama almakla varyans yuyumusatildi. Standart sapma da
hesaplandi, comparison.csv'de mevcut.

---

## Slayt 6 — Sezgi vs Veri (90 sn)

### Konusma metni
"Bu sunumun en önemli slaytı. Lutfen butun dikkati buraya verin.

Tabloda dört kontrolcü var. Sabit zamanlı — referansimiz. Uyarlanır — kuyruk
uzunluğuna duyarlı; eger bir yön dolu ise daha uzun yeşil veriyor. Acil
öncelikli — uyarlanır üzerine ek olarak ambulans gordugunde mevcut yesili
kapatip acil yöne öncelik veriyor.

Önce **ortalama bekleme** sutununa bakalim. Sabit kontrolde 43.7. Uyarlanır
kontrole gectigimizde **9.7 saniyeye** düştü — yüzde 78 iyileşme. Acil
öncelikli ile 10.1 saniyede kaldı, uyarlanır ile neredeyse ayni. Yanı
'acil öncelikli' ekstra is normal araclari neredeyse hiç etkilemiyor.

Simdi sağ taraftaki **acil sutuna** bakalim. Buradaki hikaye farkli.
Sabit kontrolde acil araç 40.4 saniye bekliyor. Uyarlanır kontrolle 7.2'ye
düştü. Acil öncelikli kontrole gectigimizde **5.8 saniyeye** indi. Sabit
zamanlidan acil onceliklie toplamda **yüzde 86 düşüş** — yani **yedi kat
fark**. Bir ambulans için bu zorunlu fark olabilir.

Sağdaki grafikte ayni hikaye gorsellestirilmis. Kırmızı sabit, sarı
uyarlanır, yeşil acil öncelikli — yeşil bar açık ara en küçük.

Alintida özet: **Sabit kontrolde ambulans 40 saniye bekliyor. Uyarlanır
kontrol bunu 7 saniyeye düşürdü. Acil öncelikli kontrol 6 saniyeye. Ayni
kavşak, üç farkli mantık, ambulans için 7 kat fark. Doğru kararı sezgi
degil simülasyon verisi gösterdi.**"

### Olası sorular

**S: Throughput neden 4 kontrolcude de ayni (~85/saat)?**
C: Throughput araç gelisine bağlı, kontrolcüye degil. Poisson hızı sabit;
ayni saatte ayni araç sayısı geliyor ve hepsi en sonunda gecer. Kontrolcü
**bekleme suresini** optimize eder, gelen aracı durduramaz. Bu yuzden
throughput ayni, bekleme dramatik farkli.

**S: Acil öncelikli normal trafigi aksatmiyor mu?**
C: 4 saatte ortalama **7 preemption** tetikleniyor — yani saatte iki
kez. Her tetiklemede yaklaşık 5 saniyelik kesinti oluyor. Normal araç
beklemesi uyarlanırdan acil onceliklie sadece 0.4 saniye artıyor (9.7 →
10.1) — hayat kurtarmanin makul bedeli.

---

## Slayt 7 — Final Genişletmesi: 4. Kontrolcü + Yeni Metrikler (90 sn)

### Konusma metni
"Final için projeyi iki yönde derinlestirdim. Birincisi **dördüncü
kontrolcü**, ikincisi **dört yeni metrik ailesi**.

**Dördüncü kontrolcü: Tahmine Dayalı (hibrit).** İlk denememde saf trend
mantığı kullandım — sadece 30 saniye sonrası kuyruğa bakıyordu. 16 farklı
parametre kombinasyonu test ettim; hiçbiri uyarlanıri geçemedi, +2.5 ila +3.7
saniye daha kötüydü. Sebep: anlık kuyruğu görmezden geliyordu.

Çözüm hibrit skor: `score = anlık_kuyruk + 0.3 × max(0, tahmin − anlık)`.
Yani anlık karar temel, sadece kuyruk artıyorsa trend bonusu eklenir.
Azalan trend ceza yapmaz. α=0.3 sweep ile seçildi.

Sonuç (5 seed × 4 saat):
- Ortalama bekleme **uyarlanırla eşdeğer**: 9.71 vs 9.70 saniye, gürültü içinde
- **p95 kötü uç uyarlanırdan %9 daha iyi**: 26.5 vs 29.2 saniye
- **Acil araç beklemesi %5 daha iyi**: 6.83 vs 7.20 saniye
- **Fairness +%4.5**: 0.891 vs 0.852

Yani: uyarlanırın ortalama performansını kaybetmeden adalet ve kötü uçta
iyileşme. Bu **gerçek bir akademik bulgu** — saf trend hatalı, hibrit
düzgün çalışıyor.

**Dört yeni metrik ailesi.** Birincisi, **percentile** — ortalama yanıltıcı,
p95 'kötü uç' gösterir. Uyarlanırte ortalama 9.7 saniye ama p95 yirmi
dört saniye; her yirmi kişiden biri 24 saniye bekliyor.

İkincisi, **Jain's fairness index** — yönler arası eşit dağılım. Burada
ilginç bir paradoks var: sabit kontrol fairness 0.996 — en adil görünür.
Ama bu **herkesi eşit ölçüde kötü bekletmek** demek. Uyarlanır 0.852 —
biraz daha düşük, çünkü kuyruk yoğunluğuna duyarlı; performans için
adaleti biraz feda eder.

Üçüncüsü, **çevresel etki** — idle motorlardan tahmini CO2. Sabit
kontrol 4 saatte 5737 gram CO2 üretirken uyarlanır sadece 1271 gram —
**dört kat fark**. Sezgisel sabit kontrolun maliyeti sadece zaman değil,
çevre.

Dördüncüsü, **saatlik heatmap** — yön × saat ortalama bekleme matrisi.
Trafik homojen değil; bazı yönler bazı saatlerde çok daha yoğun. Sağdaki
heatmap'te Güney yönü saat 1'de 19 saniyeye çıkıyor."

### Olası sorular

**S: Tahmine Dayalı neden uyarlanırte yenemedi?**
C: Bu soruyu gerçekten ciddiye aldım. İlk denememde saf trend mantığı
kullandım (sadece 30 sn sonrası tahmin); 16 parametre kombinasyonunu
sweep ettim, hepsi uyarlanıri her seed'de geride bıraktı. Sebep: anlık
kuyruğu görmezden geliyordu. Hibrit çözüme geçtim: `score = anlık +
0.3 × max(0, tahmin − anlık)`. Şimdi ortalama bekleme uyarlanırla eşdeğer
(9.71 vs 9.70), AMA p95 %9 daha iyi, acil %5 daha iyi, fairness +%4.5.
Bu negatif bulgudan pozitif tasarıma giden iyi bir akademik süreç.

**S: Sabit kontrolün fairness'ı 0.996, neden 'kötü' diyorsun?**
C: Fairness Jain's index — sadece **dağılımın eşitliğini** ölçer; mutlak
değerin iyi olup olmadığını söylemez. Sabit kontrol herkesi 43 saniye
bekletiyor, hepsi yaklaşık eşit → fairness ~1. Ama 43 saniye 'kötü'.
Fairness × ortalama bekleme birlikte okunmalı.

**S: CO2 sayıları gerçek mi?**
C: Gerçek ölçüm değil, EPA literatür sabitleriyle proxy (idle 0.6 L/saat,
2310 g CO2/L benzin). Mutlak sayı tartışılabilir ama **göreceli karşılaştırma
sağlam**: sabit kontrolün uyarlanıra göre 4 katı verimsiz olduğu kesin.

---

## Slayt 8 — Burst Senaryosu + İstatistiksel Anlamlılık (75 sn)

### Konusma metni
"Şimdi iki ekstra katman: **burst senaryosu** ve **istatistiksel anlamlılık**.

Sol tarafta burst senaryosu. Standart 4 saatlik koşumun ortasında 30
dakika boyunca Kuzey'e ekstra 20 araç/dakika ek talep verdik — okul
çıkışı, maç sonu, kaza yönlendirmesi gibi gerçek dünyada görülen
durumları taklit ediyor. Sonuçlar dramatik. **Sabit kontrol burst'te
ciddi performans çöküşü eder: ortalama 1139 saniye bekleme, p95 3122
saniye — yani 50 dakika**. Uyarlanır ve hibrit predictive 16-17 saniye
bandında kalıyor. Sabit kontrol burada **uyarlanırdan 67 kat daha kötü**.

Sağ tarafta istatistiksel anlamlılık. 10 seed × 4 saat koşum,
Mann-Whitney U testi — non-parametrik, küçük örneklemde geçerli.
Dört sonuç:

- Birinci: uyarlanır ile predictive **ortalama bekleme** arasında fark
  istatistiksel olarak anlamsız, p=0.97. Yani 'trend bonusu ortalamayı
  kaybetmedi' iddiamız doğrulandı.

- İkinci: predictive **p95'i** uyarlanırdan düşük, p=0.013 — yıldız
  seviyesinde anlamlı.

- Üçüncü: predictive **fairness'ı** uyarlanırdan yüksek, p=0.0018 — iki
  yıldız, çok anlamlı.

- Dördüncü sanity check: sabit kontrol uyarlanırdan kötü, p<0.001 —
  üç yıldız, ana bulgu istatistiksel olarak çok güçlü.

Yani **hibrit predictive iyileşmesi seed gürültüsü değil** — Mann-Whitney
U ile p95 ve fairness'taki iyileşmeler istatistiksel olarak anlamlı."

### Olası sorular

**S: Mann-Whitney U niye seçildi, neden t-testi değil?**
C: Non-parametrik (normal dağılım varsaymıyor), küçük örneklemde de
geçerli (10 seed). Bekleme süreleri çoğu zaman çarpık dağılım gösterir
(kötü uçta uzun kuyruk), normal değildir. Mann-Whitney U bu yüzden
daha sağlam tercih.

**S: 67 kat fark — bu gerçek bir hastane/şehir trafiğinde olur mu?**
C: Senaryomuz idealize: tek yöne sabit 30 dk ekstra Poisson. Gerçek
hayatta etki bu kadar uç olmaz çünkü insanlar alternatif rotaya
yönelir, sürücüler sabırla bekler veya başka noktaya gider. Ama
ORANSAL fark — sabit kontrolün burst senaryosunda dramatik bozulması —
gerçek dünyada da görülen bir davranış. SCATS/SCOOT sistemleri tam bu
yüzden gerçek şehirlerde uyarlanır kontrol kullanır.

**S: p-değerleri için Bonferroni düzeltmesi yaptın mı?**
C: Hayır, çoklu test düzeltmesi yapmadım — 4 test var. Eğer Bonferroni
uygulasaydık α threshold 0.05/4 = 0.0125 olurdu. p95 (p=0.013) sınırda,
fairness (p=0.0018) çok kolay geçer. Yani sonuçlar Bonferroni-stabil
sayılabilir; özellikle fairness çok anlamlı kalıyor.

---

## Slayt 9 — Muhendislik Detaylari (60 sn)

### Konusma metni
"Hizlica bir kaç teknik detay paylasayim.

Birincisi, **uyarlanır yeşil süresi**: bir formul ile hesaplaniyor. Kuyrukta
kac araç varsa, her birine 3 saniye veriyoruz. Minimum 15 saniye, maksimum
60 saniye sınırla. Yanı kuyruk boş olsa bile 15 saniye yeşil aliyor, çok
dolu olsa bile 60 saniyeyi gecmiyor — bu sinirlar diger yonlerin de hak
edemesini garanti ediyor.

İkincisi, **acil araç tespiti**: her tick'te kuyrukta bekleyenlere
bakiyoruz. Acil tipi varsa kontrolcü farkina variyor. Kod tarafinda
basit bir liste taramasi.

Üçüncüsü, **preemption mekanizmasi**: acil araç gorulurse mevcut yesili
5 saniyede kapatiyoruz, sarı + buffer geciyoruz, acil aracın yonune
**15 saniye sabit yeşil** veriyoruz. Bu pencere icinde acil araç mutlaka
geciyor.

Dördüncüsü, **polling pattern**. Her yarım saniyede bir kuyruga bakiyoruz.
Bu daha karmaşık event-driven SimPy idiomlarından **kasten** secilen sade
bir yaklaşım — kod okumasi ve hata ayiklamasi çok kolay.

Altta yeşil cercevede kalite metrikleri: **92 birim test** (Mann-Whitney U
dahil), mypy strict tip kontrolu temiz, ruff lint temiz, Pydantic v2 ile
domain modelleri."

### Olası sorular

**S: Neden polling pattern, neden SimPy events degil?**
C: Anlaşılırlık önceliğimizdi. Polling pattern her yarım saniyede kuyruga
bakar — savunmasi ve debug'i kolay. SimPy interrupt + Store cancel
kombinasyonu daha karmaşık; bizim sade tutmamiz gerekiyordu.

**S: 92 test sayısı yüksek degil mi, gerek var miydi?**
C: Her senaryo karşılaştırması için testler, parametre limitleri,
hipotezler, reproducibility testleri var. Final genişletmesi 37 yeni
test ekledi (percentile correctness, Jain's fairness sınırları, CO2
formul testi, predictive hibrit trend, burst event davranışı, ve
Mann-Whitney U ile istatistiksel anlamlılık doğrulaması). Test
sayısı yüksek demek proje kalitesi yüksek demek.

---

## Slayt 10 — Canli Demo + Kapanis (45 sn + demo 1.5-2 dk)

### Konusma metni
"Simdi dashboard'a geciyorum. Beş sekmeli yapıyı görsel olarak
dolaşacağız.

Bir: sidebar'dan **Tahmine Dayalı** senaryosunu secip Çalıştır butonuna
basiyorum — final genişletmesinin yıldız kontrolcüsü. Birkaç saniye
sonra sonuçlar belirecek.

İki: **Senaryo Çalıştır sekmesinde** sekiz KPI kartını gosterecegim.
Üst sıra: ortalama bekleme, acil bekleme, throughput, preemption sayısı.
Alt sıra: **p95 bekleme, Fairness, CO2 tahmini, toplam idle** — yeni
metrikler.

Üç: **Dağılım & Çevresel sekmesine** geciyorum. Percentile tablosu, bekleme
histogrami, çevresel etki blokları görünür. Buradan 'ortalama yanıltıcıdır,
p95'e bakın' mesajı veriyorum.

Dört: **Saatlik Heatmap sekmesi** — yön × saat matrix, hücrelerde
ortalama bekleme. Trafiğin homojen olmadığını gözle görüyoruz.

Beş: **Kavşak Görseli sekmesi** — 4 yollu kavsagi yukaridan goren statik
bir diyagram. Yeşil yön + kuyruktaki araçlar. Slider ile zamana
ilerleyebiliyorum.

Böyle. Sorulariniz için hazırım. Teşekkür ederim."

### Olası sorular

**S: Bu sayıları ben de uretmek istesem?**
C: Repo'da koşma komutu `python -m intersection_sim.scenarios.compare
--seeds 5 --duration-hours 4`. Yaklaşık 30 saniye surer ve ayni sayıları
üretir. Seed deterministik.

---

## Demo akışı (kısa kontrol listesi)

Sunum öncesi terminalde aciyim:

```bash
streamlit run dashboard.py
```

1. Sidebar -> **Tahmine Dayalı** seç (yıldız kontrolcü)
2. Süre: **4 saat**, Seed: **42** olarak birak
3. **Çalıştır** (5-10 saniye surer)
4. **Senaryo Çalıştır** sekmesinde 8 KPI kartını işaret et (üst sıra
   klasik 4, alt sıra Faz Final: p95, Fairness, CO2, idle)
5. **Dağılım & Çevresel** sekmesine geç, percentile tablosu + histogram
   + CO2 blokları
6. **Saatlik Heatmap** sekmesine geç — yön × saat matrisi, Güney pik
7. **Kavşak Görseli** sekmesine geç, slider'ı sona kaydır
8. (Zaman varsa) **4 Kontrolcü Karşılaştırma** sekmesi, tabloda yeni
   kolonları (p95, Fairness, CO2) işaret et

## Hocanın olası sorularina hazirlik

Detayli SSS `docs/faq.md` dosyasinda. En sik beklenenler:

- "Throughput neden ayni?" -> Poisson sabit, kontrolcü bekleme suresini
  optimize eder.
- "Acil öncelikli normal aracları aksatiyor mu?" -> Sadece +0.4 sn.
- "Uyarlanır neden %78 düşürdü?" -> Boş yönü atlamak + queue × 3 sn.
- "Kullandiginiz parametreleri nasil sectiniz?" -> Literatür + sezgisel
  baslangic, sonra parametre sweep.
- "Tahmine Dayalı neden uyarlanırte yenmedi?" -> Hibrit tasarımla ortalama
  uyarlanırla eşdeğer (9.71 vs 9.70 sn), AMA p95 %9, acil %5, fairness %4.5
  daha iyi. Saf trend mantığı önce başarısızdı (sweep ile elendi); hibrit
  doğru tasarım.
- "Fairness 0.996 sabitte, sabit mi en iyi?" -> Fairness sadece eşitliği
  ölçer, mutlak değeri değil. Sabit fair ama "kötü ölçüde eşit". CO2
  4 katı verimsiz.
- "CO2 sayıları gerçek mi?" -> Literatür proxy (EPA), göreceli karşılaştırma
  için sağlam; mutlak sayı tartışılır.
- "p95 nedir?" -> En kötü %5'lik dilim. Ortalama 10 sn ama p95 24 sn —
  yirmide biri kötü deneyim yaşıyor. Ortalama yanıltıcı.
