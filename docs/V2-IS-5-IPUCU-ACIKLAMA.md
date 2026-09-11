# İş 5 — ipucu ve şık başına açıklama (cloze üstünde, çevirileriyle)

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul:** İş 4 (cloze) bitti ve en az bir gerçek koşuyla onaylı
`sense_cloze` paketleri var. İş 3'ün çeviri deseni (`variant = l1`, dil bir
SÜTUN) kuruldu.

Önce oku: `DURUM.md` → `docs/V2-IS-4-CLOZE.md` → `docs/V2-IS-3-CEVIRI.md` →
`src/polyvo/modules/cloze/` → bu dosya.

> **Numaralandırma uyarısı.** `docs/V2-BRIEF.md` §2'deki "İş 5 / İş 6 / İş 7"
> başka kalemlerdir (review'i modülden bağımsızlaştırma · panelden düzeltme ·
> çok dilli sevkiyat). Dosya numaraları **teslimat sırasını** gösterir: bu
> dosya İş 5, gramer çıkarımı İş 6, brief'teki o üç kalem **İş 7 · İş 8 ·
> İş 9**'dur. Çelişkide dosya geçerlidir (brief §2'nin kendi kuralı).

---

## Görev

Bugün bir cloze sorusunun **öncesi** ve **sonrası** yok:

- **Öncesi yok:** öğrenci takıldığında verilecek bir **ipucu** yok. Tek
  seçeneği tahmin etmek ya da cevabı görmek.
- **Sonrası yok:** cevabı gördükten sonra **neden o cevap** ve **neden
  diğerleri değil** sorusunu yanıtlayan hiçbir metin yok. Bugün depoda bir
  şıkkın yanlış olduğunun tek kanıtı `is_answer=0` sütunudur.

İstenen: her soruya **bir ipucu**, her **şıkka** (doğru cevap dahil, dördüne
birden) **bir açıklama** — ve ikisinin de dört dile çevirisi.

Ödenmiş cloze paketi **yeniden üretilmez ve yeniden ödenmez**. Bu iş cloze'un
üstüne yazar, içine değil.

---

## Bugün ne var (yaz demeden önce teyit et)

| şey | durum |
|---|---|
| `sense_cloze` | paket durumu (`status`), anlam başına |
| `sense_cloze_question` | `(sense_id, seq)`, tam cümle + `answer`, `difficulty` |
| `sense_cloze_option` | `(sense_id, seq, opt_seq)`, `text`, `is_answer` |
| `sense_cloze_translation(_sentence)` | cümle çevirisi, `l1` bir SÜTUN |
| ipucu | **yok** |
| şık açıklaması | **yok** |
| boşluğun gösterimi | `render.py` — model TAM CÜMLE döndürür, boşluğu biz basarız |

Cloze birimleri `units.is_cloze_target` kapısından geçer (yalnızca
noun/verb/adj/adv, işlev sözcükleri hariç). Bu iş o kapıyı **değiştirmez**;
girdisi kapıdan geçmiş ve **onaylanmış** paketlerdir.

---

## İstenen davranış

### A. Yer ve sınır

1. **Yeni bir klasör: `modules/cloze/rationale/`** — `translate/`in ikizi
   (`units · prompt · qa · store · job`), yeni bir `kind`
   (`cloze_rationale`) ve `commands/rationale_command.py`. Yeni bir **app
   değildir**: ipucu ve şık açıklaması, şıkların kendisini bilmeden
   yazılamaz — yani cloze'a özeldir. (Cloze'a özel OLMAYAN parça İş 6'dır ve
   o ayrı bir app olur.)

2. **`sense_cloze`, `sense_cloze_question`, `sense_cloze_option` tablolarına
   bu koşu HİÇBİR koşulda yazmaz.** Her tablonun tek yazıcısı olur (İş 3
   §11). Kaynak denetimi testiyle çivilenir —
   `test_sense_gloss_l1in_tek_yazicisi_gloss_deposudur` testinin ikizi
   yazılır.

3. **Girdi yalnızca `status='approved'` cloze paketidir.** Reddedilmiş ya da
   hiç üretilmemiş pakete ipucu yazılmaz; açıklanacak bir şey yoktur.

4. `core/jobs/` motoruna, `lexicon_card`a, `delivery/`e ve panel host'una
   dokunulmaz.

### B. Üretim biçimi

5. **Anlam başına TEK çağrı; üç sorunun ipuçları ve 12 şık açıklaması aynı
   istekte.** Gerekçe cloze §5'in aynısı: model üçünü birden görünce
   birbirini tekrar etmeyen açıklama yazabilir, ayrı çağrılar aynı kalıbı üç
   kez üretir. Ayrıca doğru cevabın açıklamasıyla çeldiricininki **birbirine
   gönderme yapabilmelidir** ("`remove` eşya için kullanılır, para için
   `withdraw`") — bu ancak ikisi aynı istekteyse mümkündür.

6. **Paketin hepsi-ya-hiç reddedilmesi meşrudur** (İş 3 §7): tek dil, tek iş,
   tek ürün; eksik alan bir biçim hatasıdır, yeniden denenir. Cloze tarafına
   dokunulmaz.

7. **Plan B önceden onaylıdır ve ölçüme bağlanır.** 15 metinlik tek paket
   büyüktür. Pilotun onay oranı **prompt/QA düzeltmesinden sonra** hâlâ
   %50'nin altındaysa iş **iki `kind`a bölünür** (`cloze_hint` ve
   `cloze_reason`) — o noktada red sebebi içerik değil paket boyudur.
   Bölünme kararını **ölçüm** verir, tercih değil; ve bölünme şemayı
   değiştirmez (aşağıdaki tablolar zaten ayrıdır).

8. **İpucu cevabı vermez, yol gösterir.** Anlam alanını, tipik eşdizimi ya da
   cümledeki dilbilgisi ipini işaret eder. Şıklar ekranda olsun olmasın
   çalışmalıdır — "ikinci şık" gibi konum göndermesi yapamaz.

9. **Açıklama şık başınadır.** Doğru cevabınki "neden bu doğru",
   çeldiricininki "bu kelime ne demek ve bu cümlede neden olmuyor". Tek
   paragrafta toplanan açıklama **kabul edilmez**: kullanıcı şıkka basıp o
   şıkkın açıklamasını görebilmeli, QA da şık başına ölçebilmelidir.

10. **Sayılar tek dosyada.** `rationale/shape.py` (ya da eşdeğeri) ipucu ve
    açıklama uzunluk bandını **tek sabit kümesi** olarak tutar; prompt da QA
    da oradan okur (`difficulty.py` deseni). Bandı iki dosyaya yazmak
    yasaktır.

### C. Depo — dil bir SÜTUN, şema dille büyümez

11. Yeni tablolar `data/stores/cloze.sqlite` içine:

    - `sense_cloze_rationale` — paket durumu: `sense_id` PK, `status`,
      `reject_reason`, `warnings`, `tier`, `source`, `model`, `prompt_hash`,
      **`question_sha256`**, `updated_at`.
    - `sense_cloze_hint` — `(sense_id, seq, hint_seq)` PK, `hint`, `tier`,
      `source`. **`hint_seq` bugün her zaman 1'dir**; ileride "ikinci, daha
      açık ipucu" istenirse SATIR eklenir, sütun/tablo değişmez.
    - `sense_cloze_option_reason` — `(sense_id, seq, opt_seq)` PK, `reason`,
      `tier`, `source`. Anahtar `sense_cloze_option` ile **birebir aynıdır**:
      "her cevap için açıklama" tam anlamıyla şıkka bağlıdır.
    - Çeviri tarafı: `sense_cloze_rationale_translation` (`(sense_id, l1)`
      PK, durum + **`rationale_sha256`**), `sense_cloze_hint_l1`
      (`(sense_id, l1, seq, hint_seq)`), `sense_cloze_option_reason_l1`
      (`(sense_id, l1, seq, opt_seq)`).

    Beşinci dil = yeni satır. Dil başına tablo/sütun açan tasarım reddedilir.

12. **`question_sha256` bir süs değil, bir sözleşmedir.** Açıklama, açıkladığı
    sorunun **o anki** metnine ve şıklarına bağlıdır. Soru insan tarafından
    düzeltilir ya da yeniden üretilirse eski açıklama **yanlıştır** — olmayan
    bir şıkkı açıklayan metin, hiç açıklama olmamasından kötüdür. Bu yüzden:

    - hash, o anlamın üç sorusunun cümle + şık metinlerinden **deterministik**
      üretilir (sabit sıra, normalize boşluk);
    - hash tutmayan satır **bayat**tır: planlayıcı o birimi yeniden
      işlenebilir sayar, panel ve (ileride) sevkiyat onu **göstermez**;
    - aynı kural çeviri için `rationale_sha256` ile tekrarlanır (İngilizce
      açıklama değişirse çevirisi bayattır).

13. **Çeviri AYRI bir koşudur** (`kind = "cloze_rationale_translation"`,
    `variant = l1`) ve mevcut `cloze translate` koşusuyla **birleştirilmez**:
    cümle çevirileri için para ödendi, birleştirmek onları yeniden
    ödettirirdi ("ödenmiş karar yeniden ödenmez").

### D. QA — ne reddeder, ne uyarır (§6.7: garanti edilemeyen reddetmez)

14. **Reddeden** (hepsi mekanik olarak ölçülebilir):

    - soru sayısı 3 değil; bir soruda ipucu yok; bir soruda şık açıklaması
      sayısı 4 değil
    - bir açıklama, o soruda **var olmayan** bir şık metnine bağlanmış
      (eşleme şık metniyle yapılır; eşleşmeyen = red)
    - ipucu, **doğru cevabı ya da onun bir biçimini** içeriyor
      (`qa/distractor.py`deki kelime-biçimi karşılaştırması **yeniden
      kullanılır**, kopyalanmaz)
    - ipucu, şıklardan **herhangi birinin** metnini birebir içeriyor
    - ipucu ya da açıklama uzunluk bandının dışında (§10)
    - bir sorunun dört açıklaması birbirinin **aynısı** ya da normalize
      edildiğinde ayırt edilemiyor (kalıp metin kapısı)
    - bir açıklama, **açıkladığı şıkkın kendi kelimesini** içermiyor. Bu kural
      ucuzdur, promptta modele **söylenir** (ölçtüğümüz şeyi modele söyleriz)
      ve "bu şık cümleye uymuyor" tipi içeriksiz kalıbı tek başına eler.
    - ipucu şıkka konumuyla gönderme yapıyor ("first option", "B şıkkı",
      "ikinci") — kapalı bir kalıp listesiyle ölçülür

15. **Uyaran, reddetmeyen** (garanti edilemez; dürüstçe böyle raporlanır):

    - "ipucu gerçekten yardımcı mı, fazla mı açık ediyor" — ölçülemez
    - "çeldiricinin açıklaması doğru mu" — cloze'un bilinen kalite riskinin
      aynısı (gömme katmanı yok, anlamsal yakınlık ölçülemez). **Kesinlikle
      red yapma.**
    - ipucu/açıklama kelime dağarcığının anlamın CEFR'ini aşması — bu metin
      soru metni değil **üst-dildir** ve zaten L1'e çevrilecektir; üstelik
      1000 kelimenin 160'ında CEFR yok (İş 4 §10). **Uyarı.**

16. **Çeviri QA'sında bilinen tuzak — baştan kapatılacak.** Açıklamanın içinde
    şıkkın **İngilizce** kelimesi geçer ve orada kalmalıdır (İş 4 §14: şıklar
    çevrilmez). `translate/language.py::looks_english_not_l1` bu kelimeleri
    "model çevirmemiş" kanıtı sayarsa **doğru çeviriler reddedilir** — `es`
    pilotunda ödenip çöpe atılan 3 birimin sınıfı tam olarak budur. Çözüm:
    dil kontrolünden önce **bilinen şık metinleri metinden çıkarılır**;
    testle çivilenir (şıkkı içeren doğru bir Türkçe açıklama **onaylanmalı**).

### E. İnsan düzeltmesi ve panel

17. `review/record.py::EDITABLE_FIELDS`e iki alan eklenir: `cloze_rationale`
    (İngilizce paket) ve `cloze_rationale_l1` (`per_l1=True`);
    `review/targets.py::FIELD_TARGETS` ve `CLOZE_FIELDS` güncellenir —
    `apply.py` **tablo bilgisi taşımaz**, haritayı okur. Yazılan satır
    `tier=0`/`source='human'` olur ve `question_sha256` **o anki** sorulardan
    yeniden hesaplanır (insan düzeltmesi bayat doğmaz).

18. Cloze panel sayfası ipucunu ve şık açıklamalarını **salt okunur** gösterir;
    bayat (hash tutmayan) satır açıkça **bayat** etiketiyle görünür, sessizce
    gizlenmez. Panelden yazma yok, `polyvo.panel` importu yok.

---

## Kapsam dışı — dokunma

- Cloze sorusunu/şıklarını yeniden üretme; `sense_cloze*` tablolarını
  **değiştirme** (yeni tablo eklemek serbest, mevcut tabloyu değiştirmek
  yasak).
- `delivery/`e dokunma; ipucu/açıklamanın sevkiyatı çok dilli sevkiyat işinin
  konusudur. **`delivery materialize --l1 <tr dışında>` KOŞULMASIN.**
- Gramer kuralı çıkarma — o İş 6'dır, bu işte **yoktur**. İpucu bir gramer
  kuralı **etiketi** üretmez; ileride İş 6'nın kuralı ipucunun yanında
  gösterilebilir ama iki iş birbirini beklemez.
- Gömme/embedding katmanı kurma.
- `core/jobs/` motorunu ve `model_quality.json` global sırasını değiştirme.
- Kendi başına büyük paralı koşu başlatma.

---

## Pilot — kademelilik

- Önce `rationale --limit 50 --dry-run`: kaç birim, kaç çağrı — para
  harcamadan. Ardından gerçek koşu, tek modele sabit.
- Koşudan sonra §9.4 biçiminde rapor: işlenen / onaylanan / reddedilen +
  **sebep dökümü**.
- **Sayıya güvenme, örneği oku.** `job_attempts.raw_response`tan en az 10
  paket elle okunur ve dört soru yanıtlanır: (a) ipucu cevabı ele veriyor mu,
  (b) çeldirici açıklaması doğru mu, (c) dört açıklama birbirinin kalıbı mı,
  (d) doğru cevabın açıklaması gerçekten *bu* cümleyi mi anlatıyor. Bunlar
  rapora yazılır; "%X onay" tek başına teslim sayılmaz.
- Oran kötüyse prompt/QA düzeltilir, **koşu büyütülmez**; §7'deki bölme kararı
  ancak düzeltmeden sonraki orana bakılarak verilir.
- Çeviriye ancak İngilizce üretim okunduktan sonra geçilir; diller sırayla
  `tr` → `es` → `pt-BR` → `de`.

---

## Kabul ölçütleri

- `modules/cloze/rationale/` bir alt paket olarak girdi; `core/`,
  `curriculum/`, `delivery/`, `panel/` host'u ve `lexicon_card` **tek satır
  değişmedi** (`git diff` ile göster). Dokunulan mevcut yerler yalnızca:
  cloze `schema.py` (yeni tablolar), cloze `app.py` (yeni komut), cloze
  panel'i, `review/record.py`, `review/targets.py`.
- `sense_cloze` / `sense_cloze_question` / `sense_cloze_option` tablolarına bu
  koşunun **INSERT/UPDATE yapmadığı** kaynak denetimi testiyle çivilendi.
- Onaylanmamış / hiç üretilmemiş cloze paketi koşuya **girmiyor** (testle
  göster).
- Anlam başına tam **3 ipucu** (soru başına 1) ve tam **12 açıklama** (soru
  başına 4) yazılıyor; eksik paket **reddediliyor**.
- Doğru cevabı ya da bir biçimini içeren ipucu **reddediliyor** (testle
  göster).
- Dört açıklaması aynı olan soru **reddediliyor**; açıkladığı şıkkın
  kelimesini içermeyen açıklama **reddediliyor** (testle göster).
- CEFR'i bilinmeyen anlam **reddedilmiyor**, uyarı alıyor.
- `--dry-run` tek kuruş harcamıyor ve **tek satır yazmıyor**.
- İkinci koşu → **0 ödenecek çağrı** (artımlılık; İngilizce ve çeviri
  `kind`ları için AYRI AYRI kanıtlanır).
- Cloze sorusu insan düzeltmesiyle değiştiğinde o anlamın açıklaması **bayat**
  oluyor, yeniden işlenebilir sayılıyor ve panelde bayat görünüyor (testle
  göster).
- Çeviri koşusu şıkları **çevirmiyor**; şıkkın İngilizce kelimesini içeren
  doğru bir çeviri **onaylanıyor** (§16, testle göster).
- Beşinci bir dil eklemek **şema değişikliği gerektirmiyor** (uydurma bir
  kodla koşu planlanabiliyor).
- İnsan satırı (tier 0) varken o birim için çağrı **istenmiyor**;
  `review export/import --l1 de` yeni alanları taşıyor.
- Mevcut testlerin hepsi yeşil (işe başlarken `pytest -q` ile sayıyı teyit et;
  2026-09-07 itibarıyla 371).
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- Türkçe kısa docstring'ler **baştan** yazılmış; red/uyarı ayrımının gerekçesi
  ilgili dosyanın docstring'inde yazılı.
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı — elle
  okunan 10 paketin değerlendirmesi dahil.

---

## Verilen kararlar (agent bunları yeniden sormaz)

1. **İpucu ve açıklama önce İngilizce üretilir, sonra çevrilir.** Doğrudan 4
   dilde üretmek 4 kat çağrıdır ve İngilizce bir kayıt bırakmaz; bugünkü
   bütün desen (kart → gloss → çeviri) böyledir.
2. **Soru başına 1 ipucu** (`hint_seq=1`). İkinci kademe ipucu ileride
   **satır** olarak eklenir.
3. **Açıklama şık başınadır**, tek paragraf değildir.
4. **Doğru cevabın da açıklaması vardır** — "neden bu" sorusu "neden diğerleri
   değil" kadar önemlidir.
5. **Ayrı `kind`, ayrı koşu; cloze paketiyle birleştirilmez.**
6. Şıkların **kendisi** hiçbir yerde çevrilmez; açıklamanın içinde İngilizce
   kalırlar.
