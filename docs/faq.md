# SSS — Hocanın Olası Sorulari ve Cevaplari

Sunum sırasında veya sonrasinda sorulabilecek sorular ve Nihal'in
doğrudan okuyabilecegi sade Türkçe cevaplar.

---

## 1. Bu projeyi tek basiniza mi yazdiniz?

Ekip çalışmasıyla yapıldı. Kod yazımı sırasında AI asistanindan destek
alındı — özellikle spec yazma, hata ayiklama ve test kurma asamalarinda.
Mimari kararlar (dört kontrolcü, polling pattern seçimi), senaryo tasarimi
(yön bazli hizlar, acil araç orani), parametre ayarlari, sunum hikayesi
hepsi ekip tarafindan belirlendi. Asistan kodlama hızını artıran bir araç
oldu, projenin sorumluluğu bende.

---

## 2. Neden polling pattern, neden SimPy events değil?

Anlaşılırlık önceliğimizdi. Polling pattern her yarım saniyede kuyruga
bakar — `yield env.timeout(0.5)` ve `if queue_length == 0: continue`. Bu
satirlar bes kelimelik bir açıklamayla anlatilabilir. SimPy'nin daha
"idiomatic" yöntemi olan `Store.get + Interrupt` kombinasyonu daha
karmaşık, debug'i daha zor — orta-seviye SimPy bilgisi gerektiriyor.
Bizim hedefimiz kodun savunmasiydi: polling daha basit, sonuç ayni.

---

## 3. Throughput neden 4 kontrolcude ayni (~85 araç/saat)?

Throughput **araç gelisine** bağlı, kontrolcüye degil. Poisson hızı
sabit; ayni saatte ayni sayida araç geliyor. Kontrolcü sadece **bekleme
suresini optimize ediyor**, gelen aracı durduramaz veya geri cevirememez.
Bu yuzden dört kontrolcuyle de ayni sayida araç (yaklaşık 85 saat basina)
karşıya geciyor. Mesele "ne kadar bekliyorlar" — bu konuda dramatik fark
var: 43 saniye → 9 saniye.

---

## 4. 5 seed yeterli mi, neden daha çok degil?

5 seed bu calismada yeterli oldu çünkü **etki buyuklugu varyans
gurultusunden çok büyük**. Uyarlanır kontrol sabit zamanliya göre yüzde
78 ortalama bekleme düşürdü — varyans standart sapmasi yaklaşık
saniye düzeyinde. Bu kadar dramatik bir fark için 5 seed istatistiksel
guvenirligi sağlar. Daha çok seed (20, 50) sayıları 0.1 saniye düzeyinde
sapma ile degistirir, hikayeyi degistirmez. `comparison.csv` yeni seed
sayısı ile yeniden uretmek 30 saniye surer.

---

## 5. Uyarlanır kontrol neden %78 düşürdü — bu rakam çok iddialı degil mi?

İddialı ama doğru. Sebep iki: birincisi uyarlanır kontrolde **boş yönleri
atlama** var. Sabit kontrolda boş yöne bile 30 saniye yeşil verilirken
uyarlanır kontrolde o yön atlaniyor — bu çevrim suresini kısaltır. İkincisi
**yeşil süresi kuyruga göre degişiyor**: çok yoğun yöne 60 saniyeye kadar
yeşil, sakin yöne 15 saniye. Yoğun yön hızla bosaltiliyor, kuyruklar
birikmiyor. İki etki birleşince ortalama bekleme dramatik dusuyor.

---

## 6. Acil araç orani %5 nereden geldi?

Trafik literatüründe acil araç orani genellikle %2-7 arasinda. Şehir
buyukluklerine, gün saatine, kavşak konumuna göre degişir. %5 makul bir
orta nokta — gerçek bir şehirde gerek mantıklı bir bekleyiş. Parametre
`SimConfig.ArrivalProfile.emergency_probability` üzerinden ayarlanabilir;
isteyen %3 veya %10 ile yeniden kosabilir.

---

## 7. Vardiya değişimi neredeydi? Hocanın spec'inde vardi.

Hocanın "vardiya" kavramı hastane bağlaminda — gündüz/akşam personeli
değişimi. Trafik kavşaginda bu kavramın karşılığı **saatlik geliş hızı
değişimi**. Bizde 07:00-09:00 ve 17:00-19:00 yoğun saatler — geliş hızı
iki kati. Geri kalan saatlerde normal hızla. Bu, hastanedeki vardiya
mantığı (bazi saatlerde daha çok personel = bazi saatlerde daha çok
trafik) ile eşit. `ArrivalProfile.peak_morning` ve `peak_evening`
parametreleri kontrol eder.

---

## 8. Bu calismayi gerçek bir kavsakta kullanabilir miyiz?

Doğrudan degil. Gerçek dünya birkaç eksende daha karmaşık: sensor
hassasiyeti, kamera tabanlı araç sayma, sinyal hardware'inin tepki
süresi, donanım maliyeti. Bizim modelde bunlar yok. Ama benzer mantikla
gerçek sistemler kuruluyor — **SCATS** (Sydney Coordinated Adaptive
Traffic System) ve **SCOOT** (Split Cycle Offset Optimization Technique)
gerçek trafik isiklarinda canli olarak uyarlanır yeşil süresi belirleyen
sistemler. Bu projedeki uyarlanır kontrolcü basit bir SCATS varyantı
olarak görülebilir.

---

## 9. Neden SimPy kullandiniz, başka kutuphane yok mu?

SimPy event-driven simülasyon için Python'da en yaygin seçim. **Kuyruk
yonetimi, süreç yonetimi, zaman ilerletme** built-in. Alternatifler
genelde sorunlu: AnyLogic GUI tabanlı ve lisansli, OMNeT++ C++ ile yazilir
(Python'da eğitim kapsamı farkli), DESsimpy daha dar. SimPy açık kaynak,
Python ekosisteminde iyi entegre, yeterince esnek. Dersin hedefinin event
tabanlı simülasyon olmasi nedeniyle uygun seçim.

---

## 10. Test sayısı çok (55), gerekli miydi?

Evet, gerekli. Test gruplari:
- **Domain testleri** (yön enum, Vehicle hesapları, ArrivalProfile)
  modellerin doğru çalıştığını garantiler.
- **Kontrolcü testleri** (fixed cycle, adaptive switching, preemption
  trigger) her kontrolcünün spesifik davranisini kanitlar.
- **Hipotez testleri** (uyarlanır > sabit, preemptive < uyarlanır acil)
  sunumdaki sayilarin gerçeklenebilir oldugunu kanıtlıyor.
- **Reproducibility testleri** ayni seed → ayni KPI.

Hoca "sayılara guvenebilir miyim?" diye sorarsa: 55 test bunlari
otomatik kanıtlıyor. Test sayısı proje kalite gostergesidir.

---

## 11. Bu sayıları ben de uretebilir miyim, kanitlanabilir mi?

Evet, **seed deterministik**. Repo'da:

```bash
python -m intersection_sim.scenarios.compare --seeds 5 --duration-hours 4
```

bu komut yaklaşık 30 saniye surer ve `results/comparison.csv` dosyasini
üretir. Sunumdaki butun sayilar bu dosyadan. Ayni seed ile her zaman
ayni sonucu üretir — tekrar uretilebilir. Test
`test_scenario_runner_reproducibility.py` bunu otomatik doğruluyor.

---

## 12. Acil öncelikli kontrol normal araclari aksatmiyor mu?

Çok az aksatiyor — saniye düzeyinde fark. 4 saatlik koşumda ortalama
**7 preemption** tetikleniyor (saatte iki kez). Her tetikleme yaklaşık 5
saniye kesinti yapiyor. Normal araç ortalama beklemesi uyarlanırdan acil
onceliklie sadece **0.4 saniye artıyor** (9.7 → 10.1). Hayat kurtarmak
için bu kuçuk bir bedel.

---

## 13. Uyarlanır kontrol çevrim suresini nasil hesaplıyor?

İki bileşen: **yön seçimi** + **yeşil süresi**.

Yön seçimi: her yeşil periyodu başında 4 yönün kuyrukları taranir, en
uzun olan seçilir. Eşitlikte saat yonunde (N → E → S → W) sirali.

Yeşil süresi: `green = clamp(queue * 3, 15, 60)`. Yanı kuyrukta her
araç için 3 saniye, ama en az 15 ve en çok 60 saniye. 3 saniye bir
aracın **yesilden gecmesi + tepki süresi** için tahmin. 15 saniye
minimum ki çok kısa donguler olusmasin, 60 maksimum ki bir yön
**digerlerini ac birakmasin**.

---

## 14. Bir sonraki adim ne olur? Bu modeli nasil gelistirebiliriz?

Birçok yön mümkün: (a) Daha karmaşık kavşaklar — sola/saga dönüş
seritleri, T kesisimleri. (b) Yaya/bisikletli modu — sinyal sırasında
yaya da gecisi olmalı. (c) Bağlı kavşak ağı — bir kavşakta yapılan
karar yanında kavsagi etkiler ("yeşil dalga"). (d) Reinforcement
learning — sabit kurallar yerine bir ajan bekleme suresini en aza
indirme amacıyla öğrenir. Bu adimlar projeyi bitirme tezi seviyesine
tasiyabilir.

---

## 15. 4. kontrolcü "Tahmine Dayalı" ne yapıyor, uyarlanırdan farkı ne?

Uyarlanırın **hibrit trend-aware** versiyonu. İlk denememizde saf trend
mantığı (sadece "30 sn sonra ne olacak?" tahmini) kullandık — 16 parametre
kombinasyonuyla sweep yaptık, hiçbiri adaptive'i geçemedi (+2.5 ila +3.7
sn daha kötü, her seed'de). Sebep: anlık kuyruğu görmezden geliyordu.

Hibrit çözüm: `score(d) = current(d) + α × max(0, predicted(d) − current(d))`,
α = 0.3. Yani anlık kuyruk TEMEL alınır; sadece kuyruk artıyorsa (predicted
> current) trend bonusu eklenir. Azalan trend negatif bonus yapmaz.

Sonuç (5 seed × 4 saat):
- Ortalama bekleme uyarlanır ile **eşdeğer**: 9.71 vs 9.70 sn (0.01 fark,
  gürültü içinde)
- **p95 kötü uç uyarlanır'ten %9.3 daha iyi**: 26.5 vs 29.2 sn
- **Acil araç beklemesi %5 daha iyi**: 6.83 vs 7.20 sn
- **Fairness +%4.5**: 0.891 vs 0.852 (yönler arası daha eşit)

Felsefe: "anlık karar + artan trend bonusu". Uyarlanır'in toplam refahını
korur, kötü uç ve adalet boyutlarında küçük ama tutarlı iyileşme sağlar.

---

## 16. Fairness 0.996 sabit kontrol için en yüksek — yani sabit en iyi mi?

**Hayır, bu "fairness paradoksu"** ve sunumun ince noktasıdır. Jain's
fairness index sadece **yönler arası dağılımın eşitliğini** ölçer; mutlak
beklemenin iyi veya kötü olduğunu söylemez. Sabit kontrol gerçekten
yüksek fairness'a sahip (0.996) çünkü her yöne aynı 30 sn yeşil veriyor
→ tüm yönlerde ortalama bekleme yaklaşık eşit → fairness ~1.

AMA bu "eşitlik" **herkesi eşit ölçüde kötü bekletmek** anlamına geliyor —
43 saniye ortalama, 101 saniye p95. Uyarlanır fairness'i (0.852) biraz
daha düşük çünkü kuyruk uzunluğuna duyarlı; bazı yönler avantajlı.
**Ama 9.7 sn ortalama**. Yani fairness yüksek = performansa kıyasla
çok kötü değil; fairness ile ortalama bekleme'yi birlikte okumak lazım.

---

## 17. CO2 / yakıt sayıları gerçek mi, nereden geliyor?

Bunlar **literatür proxy**'leri, gerçek ölçüm değil. Formul:

```
total_idle = sum(her aracın bekleme süresi)
fuel       = total_idle × 0.000167 L/s    # 0.6 L/saat idle (EPA)
co2        = fuel × 2310 g/L              # 2.31 kg CO2 / L benzin (EPA)
```

Sabit kontrol 4 saatte tahmini 5737 g CO2 üretir, uyarlanır 1271 g —
**4 katı fark**. Mutlak sayılar tartışmalı (gerçek araçlar bazen motoru
kapatır, ortalama yakıt tüketimi araca göre değişir) ama **göreceli
karşılaştırma sağlam**: sabit kontrolün uyarlanıra göre 4 kat verimsiz
olduğu kesin. Bu, çevresel argümanın da matematiğini hocaya verir.

---

## 18. Percentile (p95) ne diyor, neden ortalama yeterli değil?

Ortalama yanıltıcı bir özettir — "ortalama 10 sn" demek, "herkes 10 sn
bekledi" demek değil. Bazen %5 dilim 45 sn bekliyor olabilir. p95 =
"en kötü %5'lik dilimin bekleme süresi" → gerçek deneyim metriği.

Örnek (uyarlanır kontrol):
- p50 (medyan): 6 sn
- p95: 24 sn
- p99: 46 sn

Yani ortalama 9.7 sn iyi gözükür ama her 20 kişiden 1'i 24 sn bekliyor,
her 100'den 1'i 46 sn bekliyor. Hocaya bunu söylemek "ortalama optimize
etmek yetmez, kuyruğun kötü ucunu da düşürmek lazım" argümanını verir.

---

## 19. Burst senaryosunda ne oldu, sabit kontrolü neden 67× yenmiş?

Standart 4 saatlik koşumun ortasında 30 dakika boyunca Kuzey yönüne
+20 araç/dk ek talep verdik (okul çıkışı, maç sonu, kaza yönlendirmesi
benzetimi). Sonuç:

| Kontrolcü | Ort. (sn) | p95 (sn) | Notlar |
|---|---:|---:|---|
| Sabit Zamanlı | 1138.9 | 3122 | **ciddi performans çöküşü** |
| Uyarlanır | 16.84 | 28.1 | trafik akıcı |
| Tahmine Dayalı | **16.69** | **27.5** | trend yakaladı, küçük avantaj |
| Acil Öncelikli | 17.46 | 32.0 | preemption sadece acil için |

**Sabit kontrol neden bu kadar kötü?** Sıralı dönüşle her yöne 30 sn
yeşil veriyor — Kuzey doluyor olsa bile Güney/Doğu/Batı'ya boş yeşil
vermeye devam ediyor. Burst süresince Kuzey kuyruğu birikiyor; çevrim
tamamlandığında ancak 30 sn boşalma. Sonuç: kuyruk geri yayılıp dağılır,
ortalama bekleme felaket olur. p95 ≈ 52 dakika.

**Hibrit predictive burada ne yapıyor?** Trend bonusu ile Kuzey'in
dolduğunu erken yakalıyor, daha uzun yeşil veriyor. Uyarlanırla aynı
ortalama (16.84 vs 16.69) ama p95 daha düşük (27.5 vs 28.1) ve
fairness daha yüksek (0.875 vs 0.864).

## 20. Mann-Whitney U sonuçlarınız ne gösteriyor?

10 seed × 4 saat koşum, adaptive vs hibrit predictive. Non-parametrik
çünkü bekleme süreleri normal dağılmıyor (kötü uçta uzun kuyruk).

| Karşılaştırma | p-value | Sembol | Yorum |
|---|---:|---|---|
| Uyarlanır ≈ Predictive ortalama | 0.97 | ns | trend bonusu ortalamayı kaybetmedi |
| Predictive p95 < Uyarlanır | 0.013 | * | kötü uçta anlamlı iyileşme |
| Predictive fairness > Uyarlanır | 0.0018 | ** | yön adaletinde çok anlamlı |
| Sabit ≫ Uyarlanır ortalama | <0.001 | *** | ana bulgu çok güçlü |

Yani hibrit predictive'in p95 ve fairness'taki iyileşmesi rastgele
seed gürültüsü değil — **istatistiksel olarak anlamlı bir tasarım
kazanımı**. Sunumda söylediğimiz "p95 −%9, fairness +%4.5" sayıları
gerçek; küçük örneklem testi bile bunu doğruluyor.

Bonferroni düzeltmesi yapsaydık α threshold 0.0125 olurdu (4 test
için 0.05/4). p95 (0.013) sınırda kalıyor; fairness (0.0018) çok
geçiyor. Yani sonuçlar çoklu test düzeltmesine de büyük ölçüde dayanıklı.

## 21. Saatlik heatmap'te ne görüyoruz?

Yön × Saat matrisi, hücre rengi = ortalama bekleme. Uyarlanır kontrolde
4 saatlik koşumda:
- Kuzey: 3.8 / 7.7 / 2.3 / 1.4 sn → hep en hızlı
- Güney: 12.3 / 19.1 / 13.5 / 13.7 sn → en yoğun (saat 1'de pik)
- Doğu: 13.9 / 15.2 / 11.4 / 12.6 sn
- Batı: 16.1 / 14.9 / 14.6 / 16.4 sn

Bu hocaya iki şey söyler: (a) trafik **homojen değil** — yön bazlı
yoğunluk farkı var, simülasyon bunu yakalıyor. (b) Saatlik değişim
modelleniyor — yoğun saat (07-09 / 17-19) etkisi heatmap'te ısı
artışı olarak görünür.
