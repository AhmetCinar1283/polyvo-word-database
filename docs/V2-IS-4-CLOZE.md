# İş 4 — `modules/cloze`: anlam başına 3 çoktan seçmeli boşluk sorusu

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul:** İş 1, İş 2, İş 2b bitti. İş 3 (çeviri katmanı) ile aynı anda
yürüyebilir ama cloze **çevirisi** İş 3'ün kurduğu çeviri desenini kullanır.

Önce oku: `DURUM.md` → `docs/V2-BRIEF.md` §4 (kullanıcı kararları) →
`docs/V2-IS-3-CEVIRI.md` → kod.

---

## Görev

Ödenmiş 957 onaylı kartın üstüne, **her anlam için 3 boşluk doldurma sorusu**
üretmek — sonra bunları 4 dile çevirmek.

Bu, mimarinin sınavıdır: yeni bir içerik türü **bir klasör** olarak girmeli,
mevcut hiçbir dosyayı düzenletmemeli.

---

## Soru biçimi (kullanıcı kararı — pazarlığa kapalı)

Her soru: içinde tam bir boşluk olan **İngilizce** bir cümle + **4 şık**.
Şıkların biri doğru cevap, **üçü çeldirici**. Çeldiricisiz soru **yok** —
üç sorunun üçü de çoktan seçmelidir.

Anlam başına üç soru, üçü de **o anlamın CEFR seviyesinin içinde**:

| soru | cümle uzunluğu | çeldirici yakınlığı | amaç |
|---|---|---|---|
| kolay | kısa | uzak — belirgin biçimde başka anlam alanı | kelimeyi tanıyor mu |
| orta | orta | ilgili alan ama cümleye açıkça uymuyor | anlamı ayırt ediyor mu |
| zor | uzun | **yakın anlamlı** — anlamı yakın, kullanımı yanlış | nerede kullanıldığını biliyor mu |

Zor sorunun zorluğu **şık sayısından değil çeldiricinin yakınlığından**
gelir. Seçenek sunmak soruyu kolaylaştırır (tanıma, hatırlamadan kolaydır);
zor soru ancak çeldiriciler gerçekten yakın anlamlıysa zor olur. Örnek:

> I need to **\_\_\_\_** money from my account.
> **withdraw** ✓ · remove · extract · subtract

Dördü de "çıkarmak" anlamına yakın; yalnızca `withdraw` bu bağlamda doğru.
Buna karşılık `quickly` gibi bir çeldirici bedava eleme sağlar — kelimeyi
bilmeyen de eler, soru bir şey ölçmez.

**Üçü de kendi CEFR seviyesinin dışına çıkmaz.** A1 bir anlamın "zor"
sorusu, A1 öğrencisini zorlayan ama A1 kalan bir sorudur; B1 sorusu değildir.

---

## Bugün ne oluyor (ölçüldü, 2026-09-06)

| şey | durum |
|---|---|
| `sense_cards` | 957 approved (her birinde `gloss_en` + 2 örnek cümle) |
| `item_level.cefr` | 1000 kelimenin **840'ında var, 160'ında YOK** |
| cloze | **hiç yok** |
| gömme (embedding) katmanı | **yok** — anlamsal yakınlık ölçülemez |

Geçmiş şikâyet: üretilen cümleler birbirine benziyor ("I eat cake"
tekdüzeliği). Bu İş 2'de bilerek kapsam dışı bırakıldı ve buraya devredildi.

---

## İstenen davranış

### A. Modül sınırı

1. **`modules/cloze` yeni bir klasördür.** Kendi `app.py`si, kendi `Job`u,
   kendi deposu, kendi QA'sı, kendi panel sayfası olur.

2. **`lexicon_card`a bağımlılık DAR ve TEK YÖNLÜ olur.** Cloze'un ödenmiş
   karta (headword, pos, `gloss_en`, örnekler, CEFR) ihtiyacı gerçektir —
   ama `lexicon_card`ın içine dağılmış importlar **yasaktır**. `lexicon_card`
   tek bir **okuma yüzeyi** ilan eder (örn. `lexicon_card/public.py`) ve
   cloze **yalnızca** onu import eder.

3. **`test_layering` bu kuralı ölçmelidir.** Bugünkü test yalnızca katmanlar
   arasına bakıyor (`modules` = 3), yani iki modülün birbirini import etmesi
   testten **sessizce geçer**. Ekle: `modules/*` altındaki bir paket başka bir
   `modules/*` paketinden **yalnızca ilan edilmiş okuma yüzeyini** import
   edebilir, ve `lexicon_card` **hiçbir koşulda** `cloze`u import edemez.
   Kural yazılı değil ölçülü olsun.

4. Cloze'un panel sayfası `APP.panel` ile gelir; **`polyvo.panel` paketini
   import etmez** (demir kural). Host'ta tek satır değişmemeli.

### B. Üretim

5. **Anlam başına TEK çağrı, üç soru birden.** Model üçünü aynı anda görürse
   birbirinden farklı olmalarını sağlayabilir; üç ayrı çağrı üç kez aynı
   kalıbı üretir. Zorluk etiketi (`kolay`/`orta`/`zor`) modelden gelmez,
   **istekte biz veririz** ve hangi cevabın hangi zorluk olduğu sabittir.

6. **Kart bağlam olarak verilir** (`gloss_en` + mevcut örnek cümleler),
   iki sebeple: (a) model kelimeyi değil **o anlamı** sormalı; (b) mevcut
   örnek cümleler **tekrar edilmemesi gereken** metin olarak verilir.

7. **Çeşitlilik prompt'a "çeşitli ol" yazarak sağlanmaz** — ölçülmeyen istek
   tutulmaz. Bunun yerine her soruya sabit bir listeden bir **sahne/alan
   kısıtı** verilir (ev, iş, yolculuk, okul, sağlık, alışveriş...), ve o kısıt
   `stable_key` + soru sırasından **deterministik** seçilir. Saatten,
   rastgeleden ya da koşu kimliğinden türetilmez: aynı birim yeniden
   koşulduğunda **aynı kısıt** gelmeli, yoksa "bir kere ödenir" kuralı kırılır.

8. **Cümleler doğru ve mantıklı olacak.** Boşluğa giren kelime cümlede
   **tam bir kez** geçmeli; doğru cevap hedef kelimenin o anlamdaki doğru
   çekimi olmalı.

### C. QA — neyin reddettiği, neyin uyardığı

9. **Reddeden** (garanti edilebilir):
   - şık sayısı 4 değil; şıklar birbirinin aynısı
   - doğru cevap şıklar arasında yok
   - bir çeldirici hedef kelimenin kendisi ya da çekimli/türemiş biçimi
   - çeldiricilerin sözcük türü hedefle aynı değil
   - hedef kelime cümlede yok ya da birden çok kez var
   - cümle uzunluğu, o sorunun zorluk bandının dışında
   - bir anlamın üç cümlesi aynı açılış n-gram'ıyla başlıyor (tekdüzelik kapısı)
   - cümledeki diğer içerik kelimeleri anlamın CEFR seviyesinin üstünde
     (**yalnızca CEFR biliniyorsa** — bkz. 10)

10. **CEFR bilinmediğinde reddetme.** 1000 kelimenin 160'ında `cefr` YOK.
    Bilinmeyen seviye bir red gerekçesi değildir → **uyarı**. "Bilmiyorum"
    bir satırı çöpe attırmaz.

11. **Uyaran, reddetmeyen** (garanti edilemez):
    - "çeldirici gerçekten boşluğa uymuyor mu" — bunu mekanik doğrulamanın
      yolu yok (gömme katmanı yok). **Kesinlikle red yapma**; uyar ve insan
      denetimine bırak. Bu, bu işin bilinen en büyük kalite riskidir ve
      dürüstçe böyle raporlanmalıdır.
    - "zor sorunun çeldiricileri gerçekten yakın anlamlı mı"
    - cümlenin kendi CEFR seviyesine uygunluğu (uzunluk ve kelime dağarcığı
      ölçülür, üslup ölçülemez)

12. **Ölçülebilir bir çeldirici kapısı vardır ve kullanılmalıdır:** çeldirici
    bizim evrenimizdeki bir kelimeyse, CEFR'i hedef anlamın CEFR'ini
    **aşmamalı** — yoksa soru, hedef kelime yüzünden değil çeldiriciyi
    tanımadığı için zorlaşır. Evren dışı çeldiricide ölçüm yok → uyarı.

---

## Ölçüldükten sonra revize edilen kurallar (2026-09-07)

İlk gerçek koşu (`run_id 20260907-012908`, 50 birim, 93 ödenmiş çağrı)
onay oranını **%16** ölçtü. Denemeler okundu; sebep model değil kapının
kendisiydi. Aşağıdaki üç değişiklik **ölçüme dayanır**, tercihe değil.
Aynı ham cevaplar yeni kapıdan geçirildiğinde onay **%64**.

1. **§12'nin bir band payı vardır** (`cefr.LEVEL_TOLERANCE = 1`) ve **"zor"
   bandında reddetmez, uyarır** (`Band.enforce_distractor_level`). Gerekçe:
   §12 ile soru biçimi tablosunun "zor = **yakın anlamlı** çeldirici" satırı
   A1 anlamlar için aynı anda tutulamaz — bir A1 kelimesinin yakın
   anlamlıları tanım gereği daha seyrektir (`be`←`remain` A2,
   `above`←`beneath` B1, `about`←`approximately` B1). Evrende 812 A1 kelime
   var; bunun aynı POS + yakın anlamlı alt kümesi neredeyse boş. 42 CEFR
   reddinin 27'si tam olarak buydu. Aynı pay §9'un son satırına (cümlenin
   kelime dağarcığı) da uygulanır: A1 bir anlamın 15-25 kelimelik "zor"
   cümlesi yalnızca A1 kelimeyle kurulamaz.

2. **Cümle uzunluğu payı `WORD_COUNT_TOLERANCE = 3`tür ve YALNIZCA QA'da
   genişler.** Modele dar band söylenir (`difficulty.BANDS`), pay ölçen
   tarafta verilir — geniş bandı modele söylemek bandın *ortasını* kaydırır.

3. **`units.CLOZE_POS`: yalnızca noun/verb/adj/adv birim üretir.** Koşulan 50
   birimin 10'u edat/tanımlık/bağlaç/zamirdi; "the"/"to"/"of" 15-25
   kelimelik bir cümlede tam bir kez geçemez (§9), WordNet'te bu türler yok
   (çeldirici türü ölçülemez), ve bir edatın çoktan seçmeli boşluğu kelime
   bilgisi değil dilbilgisi sorusudur.

Ayrıca `cefr.load` içinde bir **sıralama hatası** düzeltildi: `rank(...) or 99`
yazımı A1'in sırası 0 olduğu için A1'i her karşılaştırmada kaybettiriyordu —
sözlüğün 8641 kelimesinden 246'sı (hepsi A1) yanlış seviyedeydi (`take`→B1,
`go`→B1, `but`→B1). Sözlük artık `(kelime, POS)` başına da okunur; çeldiricinin
POS'u zaten hedefle aynı olmak zorunda olduğu için o satır kullanılır.

## İkinci ölçüm: sahne kısıtı ve işlev sözcükleri (2026-09-07, ikinci koşu)

Yukarıdaki üç değişiklikten sonra gerçek koşu (`run_id 20260907-095434`,
`--redo bad --force self`, 24 birim, 44 ödenmiş çağrı) onayı yalnızca
**%33** ölçtü. 64 red denemesi tek tek okundu. Başarısız 16 birimin
**tamamı** iki yapısal sebebe iniyordu; hiçbiri "model zayıf" değildi.

4. **Sahne kısıtı ZORUNLU değil ÖNERİDİR** (`prompt.py`, `prompt_version`
   v1→v2). Sahne yalnızca `stable_key` hash'inden türüyor, yani kelimenin
   anlamıyla ilgisi yok: `vacation` → "food, cooking and eating out",
   `fax` → "nature, weather and outdoors". Model doğru davranıyordu — sahneye
   ait bir cümle yazıp hedef kelimeyi ya zorla içine sıkıştırıyor ("I want to
   eat pizza during my **vacation**") ya da tamamen düşürüyordu ("The weather
   forecast says a heavy rain will come tomorrow", cevap `fax`). Bu tek sebep
   **üç ayrı kapıyı** birden ateşliyordu ve reddin %58'iydi:

   | kapı | koşudaki sayı | sahnenin payı |
   |---|---|---|
   | `celdirici_cefr_hedefin_ustunde` | 22 | bankacılık sahnesi A1 bir anlama `salary` B2, `debt`/`insurance` B1 çeldiricisi ürettirdi |
   | `hedef_kelime_cumlede_yok` | 10 | sahne cümlesi yazıldı, hedef kelime düştü |
   | `cumlede_anlamin_seviyesinin_ustunde_kelime` | 5 | ofis sahnesi A1 bir anlamı `presentation` (B1) yazmaya zorladı |

   Kapılar **doğru** çalışıyordu; hatalı olan istekti. İki zorunlu istek (bu
   sahne + bu seviye) aynı anda tutulamaz, tutulamayan istek modele
   söylenmez (§6.7). Bedeli açıkça kabul edildi: "üçü de aynı sahne hissi
   veriyor" hali artık garanti değil — ama o zaten hiç ölçülemiyordu; ölçülen
   tek çeşitlilik açılış n-gram'ıdır ve o kapı reddetmeye devam eder.
   Ayrıca "çeldiriciyi **sahneden değil hedef kelimeden** seç" kuralı eklendi.

5. **`units.FUNCTION_WORDS`: POS etiketi yetmez.** Sözlük edatları `adv`,
   zamirleri `noun` etiketliyor; `above`, `after`, `in`, `non`, `o'clock`,
   `it` `CLOZE_POS` filtresinden geçip birim oluyordu — başarısız 16 birimin
   7'si buydu ve `it` **yanlışlıkla onaylanmıştı**, yani bu yalnızca ucuz
   olanı atlamıyor, kötü bir kartı da depoya girmekten alıyor. Liste bilerek
   dar: yalnızca kapalı sınıf sözcükler ve bağımlı biçimler.
   `core/text/qa.py::ENGLISH_MARKERS` **bilerek yeniden kullanılmadı** — o
   liste dil tespiti için geniş tutulmuştur ve `take`/`make`/`go`/`see`/
   `know`/`want`/`need` gibi tam da öğretilecek A1 fiillerini içerir. Birkaç
   kapalı sınıf sözcüğün gerçek bir içerik kullanımı olduğu için istisna
   (kelime, POS) düzeyinde yazıldı: `can` (teneke kutu), `will` (irade),
   `while` (bir süre). Onaylı 957 anlamın 805'i cloze birimi olur (110'u POS,
   42'si işlev sözcüğü elemesi).

6. **CEFR araması çekimli biçimi köküne indirir** (`cefr.Levels.get`, WordNet
   `morphy`). Sözlükte çekimli biçimler ayrı ve **daha yüksek** satırlar
   olabiliyor: `removed` C1 iken `remove` B1; `took`/`bought` sözlükte hiç
   yokken `take`/`buy` A1. Yüzey ile kökün **düşüğü** kazanır — sınıfın geri
   kalanıyla aynı yön (öğrenci kelimeyi ilk gördüğü yerde öğrenir, şüphe
   reddetmez). Yalnızca çekim çözülür, türetme değil (`health` ≠ `healthy`).
   `add` fiili tam bu yüzden reddedilmişti (`removed` C1 okunuyordu).

Ölçüm (194 kayıtlı ham cevap **eski** prompt'la üretilmiş, yeni QA'dan
geçirildi — yani 4. maddenin etkisi bu sayıda **yok**): 21 birim artık hiç
sorulmayacak; kalan 40 birimde onay %67.5 → **%75**. Kalan reddin çoğu
(26 çeldirici-CEFR + 13 hedef-kelime-yok) tam olarak 4. maddenin hedefidir
ve ancak yeni prompt'la ödenmiş bir koşuda ölçülebilir.

### D. Çeviri

13. **Cloze önce İngilizce üretilir ve onaylanır; çeviri AYRI bir koşudur.**
    Böylece beşinci bir dil eklemek cloze'u yeniden ödettirmez.

14. **Çevrilen şey cümledir, şıklar değil.** Şıklar İngilizce kalır — bu bir
    İngilizce alıştırmasıdır; şıkların çevirisi soruyu anlamsızlaştırır.
    Çeviri **boşluğu doldurulmuş tam cümlenin** çevirisidir; ne zaman
    gösterileceği uygulamanın kararıdır.

15. **Çeviri deseni İş 3'ün aynısıdır:** anlam başına dil başına tek çağrı
    (üç cümle birlikte), tek doğal çeviri, ikinci bir "birebir çeviri" alanı
    **YOK**. Diller `tr` · `es` · `pt-BR` · `de`, dördü eşit, şema dille
    büyümez.

---

## Kapsam dışı — dokunma

- `delivery/`e dokunma. Cloze'un sevkiyatı İş 3'ün (modül katkı dikişi) ve
  İş 7'nin işidir. **`delivery materialize --l1 <tr disinda>` KOŞULMASIN.**
- `lexicon_card`ın üretimini değiştirme; kartı, örnek cümleleri, `gloss_en`i
  yeniden üretme. Cloze **okur**, yazmaz.
- `core/jobs/` motorunu değiştirme.
- Gömme/embedding katmanı kurma (v2'ye ertelendi) — anlamsal yakınlığı
  ölçmeye çalışma, uyarıyla yetin.
- Kendi başına büyük parali koşu başlatma.

---

## Pilot — kademelilik

Kullanıcı önce küçük koşacak; sen bunu mümkün kılacaksın.

- Önce `--limit 50 --dry-run`: kaç birim, kaç çağrı — para harcamadan.
- Gerçek koşu tek modele sabit (`model_quality.json` global).
- Koşudan sonra §9.4 biçiminde rapor: işlenen / onaylanan / reddedilen +
  sebep dökümü.
- **Sayıya güvenme, örneği oku.** `job_attempts.raw_response`tan en az 10
  soru elle okunup şu üçü kontrol edilir: cümle mantıklı mı, çeldiriciler
  gerçekten uymuyor mu, üç cümle birbirine benziyor mu. Sebep: `es`
  pilotunda reddedilen 3 birimin üçü de **doğru cevaptı**; orana bakıp geçmek
  bunu kaçırdı. Cloze'da aynı tuzağın tersi geçerli — **QA'nın ölçemediği
  şey kabul edilmiş görünür.**
- Tekdüzelik ölçülür ve raporlanır: üretilen cümlelerin kaç farklı açılış
  kalıbı kullandığı sayılır. Kötüyse **prompt/sahne listesi düzeltilir,
  koşu büyütülmez.**
- Çeviriye ancak İngilizce üretimin kalitesi görüldükten sonra geçilir.

---

## Kabul ölçütleri

- `modules/cloze` **bir klasör** olarak girdi; `core/`, `curriculum/`,
  `delivery/`, `panel/` ve `lexicon_card`ın üretim dosyaları
  **değişmedi** (`git diff` ile göster). Tek istisna: `test_layering`e
  eklenen modüller-arası kural ve `lexicon_card`ın ilan ettiği okuma yüzeyi.
- `test_layering` artık modüller arası kuralı da ölçüyor ve
  `lexicon_card → cloze` importunu **yakalıyor** (testle göster).
- Cloze panel sayfası host'ta **tek satır değişmeden** görünüyor;
  `polyvo.panel` importu yok (testle çivile).
- `--dry-run` tek kuruş harcamıyor ve **tek satır yazmıyor**.
- İkinci koşu → **0 ödenecek çağrı** (artımlılık).
- Kartsız / onaylanmamış anlam cloze koşusuna **girmiyor**.
- Anlam başına tam **3 soru**, her soruda tam **4 şık**, tam **1 doğru cevap**.
- Hedef kelimenin kendisini/çekimini çeldirici yapan cevap **reddediliyor**.
- CEFR'i bilinmeyen kelime **reddedilmiyor**, uyarı alıyor (testle göster).
- Aynı anlamın üç cümlesi aynı açılış kalıbıyla başlayamıyor (testle göster).
- Sahne kısıtı **deterministik**: aynı birim iki kez planlandığında aynı
  kısıt üretiliyor (testle göster).
- "Çeldirici uymuyor mu" kontrolü **red değil uyarı** olarak duruyor ve
  bunun neden böyle olduğu docstring'de yazılı.
- Çeviri koşusu şıkları **çevirmiyor**, cümleyi çeviriyor.
- Beşinci bir dil eklemek **şema değişikliği gerektirmiyor**.
- İnsan satırı (tier 0) varken o birim için çağrı **istenmiyor**;
  `review` cloze'u da düzeltebiliyor.
- Mevcut 235 test yeşil.
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- Türkçe kısa docstring'ler baştan yazılmış (sonradan eklenmiş değil).
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı — tekdüzelik
  sayımı ve elle okunan 10 sorunun değerlendirmesi dahil.
