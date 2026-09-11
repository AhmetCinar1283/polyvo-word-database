# İş 6 — `modules/grammar`: cümledeki göze çarpan gramer kurallarını çıkarma

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul:** İş 4 (cloze) bitti; onaylı `sense_cloze` paketleri var. İş 5 ile
**aynı anda yürüyebilir**, birbirini beklemez (ikisi de cloze'un üstüne yazar,
farklı tablolara).

Önce oku: `DURUM.md` → `docs/V2-IS-4-CLOZE.md` → `docs/V2-BRIEF.md` §3
(değişmeyecek kurallar) → `src/polyvo/modules/cloze/` +
`src/polyvo/core/cli/app.py` + `discovery.py` → bu dosya.

> **Numaralandırma uyarısı.** `docs/V2-BRIEF.md` §2'deki "İş 5 / İş 6 / İş 7"
> başka kalemlerdir (review'i modülden bağımsızlaştırma · panelden düzeltme ·
> çok dilli sevkiyat); yeni numaralarıyla **İş 7 · İş 8 · İş 9**.

---

## Görev

Bir soruda geçen **en göze çarpan gramer kurallarını** çıkarmak: bariz olandan
ayrıntıya doğru **sıralı**, kimliklenmiş (id'li), açıklamalı ve çevrilebilir.

Örnek — `The bird is able to fly high.`

| sıra | kural id | tetikleyici | neden bu sırada |
|---|---|---|---|
| 1 | `EN.MODAL.BE_ABLE_TO` | `is able to` | cümlenin **taşıyıcı yapısı**; kelime seçimi değil, kalıp |
| 2 | `EN.INF.TO_INFINITIVE` | `to fly` | kalıbın içindeki mastar; birinciyi anlamayan buna takılır |
| 3 | `EN.ADV.FLAT_ADVERB` | `fly high` | ayrıntı: `high` burada zarf, `highly` değil |

Çıkmaması gerekenler aynı cümlede: "`be` fiili `am/is/are` olur",
"`The` belirli tanımlıktır", "isimler tekil/çoğul olur". Bunlar **her** cümlede
vardır; her cümlede tekrarlanan şey o cümle hakkında bilgi taşımaz.

**Bu iş cloze'a özel değildir.** Yarın paragraf, okuma parçası ya da başka bir
soru tipi eklendiğinde aynı modül, **tek satır değişmeden** onların
cümlelerini de işleyebilmelidir. Bu, mimarinin ikinci sınavıdır: İş 4 "yeni
içerik türü bir klasördür"ü kanıtladı, bu iş "**yeni içerik türü mevcut bir
analizciye bedava bağlanır**"ı kanıtlar.

---

## Bugün ne var (teyit et)

- Cümleler `sense_cloze_question.sentence`da **tam cümle** olarak duruyor
  (boşluk gösterimde basılıyor) — yani analiz edilecek metin **hazır** ve
  boşluksuzdur.
- `lexicon_card`ın örnek cümleleri (`sense_examples`, 1914 satır) ikinci bir
  aday kaynaktır ama **bu işte koşulmaz** (para).
- Katkı seam'i olarak bugün yalnızca `APP.panel` var; `APP.dist` henüz yok
  (o başka bir işin konusu). Bu iş **ikinci** bir seam getirir.
- Gramer için hiçbir tablo, hiçbir katalog, hiçbir id uzayı yok.

---

## İstenen davranış

### A. Yer, sınır ve genellik

1. **`modules/grammar/` yeni bir app'tir**: kendi `app.py`si, kendi `Job`u,
   kendi deposu (`data/stores/grammar.sqlite`), kendi QA'sı, kendi panel
   sayfası. Cloze'un içine **girmez** — cloze'a özel olmayan tek parça budur.

2. **`grammar` hiçbir kardeş modülü import ETMEZ.** Cümleler bir **katkı
   seam'i** üzerinden gelir: `core/cli/app.py`ye `APP.sentences` alanı
   eklenir (`PanelPage` gibi, katman 0'da ilan edilen bir sözleşme tipi), her
   app kendi cümlelerini oradan sunar, `grammar` onları `discovery.find_apps()`
   ile toplar. Böylece `grammar`ın statik import grafiğinde `cloze` **hiç
   geçmez** ve beşinci bir soru tipi `grammar`da **tek satır değiştirmez**.

3. **Seam sözleşmesi** (adlar öneri, biçim şart):
   - `SentenceSource(owner: str, loader)` — `owner` app adıdır ve **kimliğin
     parçasıdır**, sonradan değişmez.
   - `loader(tag, l2) -> list[SentenceGroup]`;
     `SentenceGroup(group_key, sentences)`;
     `SentenceRef(ref, text, cefr, focus_word, focus_pos)`.
   - `cloze` bu kaynağı **`cloze/public.py`de** ilan eder (İş 4'ün ilan
     edilmiş okuma yüzeyi deseni): grubu bir anlam, `ref`i `"<sense_id>:<seq>"`,
     `text`i onaylı sorunun tam cümlesi olur. Yalnızca **onaylı** paketler
     sunulur.
   - `focus_word` isteğe bağlıdır (cloze'da hedef kelime): **kural seçimini
     yönlendirmez**, yalnızca prompt'a bağlam olarak girer.

4. **`tests/test_layering.py` bunu ölçer:** `modules/grammar` altında başka bir
   `modules/*` paketine **statik import yoktur**; `cloze` da `grammar`ı import
   edemez. Kural yazılı değil **ölçülü** olsun.

5. **Genellik testle kanıtlanır, sözle değil:** testlerde **sahte bir app**
   (`APP.sentences` ilan eden, kendi cümlelerini veren) tanımlanır ve
   `grammar` onu **hiçbir dosya değişmeden** işler.

### B. Kural kimliği — id biçimi ve katalog

6. **Kural id biçimi sabittir:** `EN.<ALAN>.<KURAL>`
   - büyük harf, nokta ayraçlı, üç parça; `[A-Z0-9_]` dışında karakter yok
   - `EN` dil kodudur (L2). Başka bir L2 eklenirse önek değişir, biçim değişmez.
   - `<ALAN>` **kapalı** bir listeden gelir; başlangıç listesi (gerekirse
     büyütülür, ama gelişigüzel değil): `TENSE` · `ASPECT` · `MODAL` · `VOICE`
     · `INF` · `GER` · `PART` · `COND` · `CLAUSE` · `REL` · `QUES` · `NEG` ·
     `ART` · `NOUN` · `PRON` · `ADJ` · `ADV` · `COMP` · `PREP` · `CONJ` ·
     `QUANT` · `ORDER` · `PHRASAL` · `COLLOC` · `DISC`
   - `<KURAL>` okunur ve **kalıcıdır**: `BE_ABLE_TO`, `TO_INFINITIVE`,
     `FLAT_ADVERB`, `PRESENT_SIMPLE_3SG`.

7. **Katalog kodda/veride durur, depoda değil.** `modules/grammar/catalog/`
   altında insan tarafından yazılmış bir liste; her satır:

   | alan | ne işe yarar |
   |---|---|
   | `id` | yukarıdaki biçim; **hiç değişmez** |
   | `name_en` / `short_en` | kuralın **genel** adı ve 1-2 cümlelik açıklaması — bir kez yazılır, her cümlede yeniden ödenmez |
   | `level` | kuralın öğretildiği CEFR bandı |
   | `assume_known_from` | bu bandın **üstündeki** bir cümlede artık "göze çarpan" sayılmaz |
   | `trivial` | rank 1'de **asla** görünemeyecek kurallar (`EN.BE.PRESENT_FORMS`, `EN.ART.A_AN`, `EN.NOUN.PLURAL_S` gibi) |
   | `merged_into` | boş ya da başka bir id — **birleştirme buradan yapılır** |

8. **Birleştirme satırları yeniden yazmaz.** Kullanıcı iki kuralı aynı şey
   bulup birleştirmek istediğinde katalogda `merged_into` doldurulur; depoda
   yazan **ham id olduğu gibi kalır**, çözümleme okuma anında yapılır
   (`catalog.resolve(id)`). Böylece birleştirme geri alınabilir ve tek satır
   LLM parası harcatmaz. Zincir çözümlemesi döngüye girerse **kapı düşer**
   (katalog denetimi testi).

9. **Model KAPALI SÖZLÜKTEN seçer.** Katalogda olmayan bir kural id'si
   uydurulamaz. Model gerçekten kayda değer ama katalogda olmayan bir yapı
   görürse onu **aday** olarak bildirir (`grammar_candidate` tablosu, önerilen
   ad + tetikleyici + gerekçe). Aday **sevk edilmez, gösterilmez**; insan
   katalogda karşılığını açar. Sebep: id uzayı bir kez şişerse geri
   toplanamaz; "sonradan birleştiririm" ancak id sayısı yönetilebilirse
   mümkündür.

### C. Ne çıkar, hangi sırada

10. **Cümle başına en çok `MAX_RULES_PER_SENTENCE = 3`, en az 1 kural.**
    Sıra (`rank` 1..N) **anlamlıdır**: 1 = cümlenin taşıyıcı yapısı, sonrası
    ayrıntı. Boşluklu/yinelenen rank **reddedilir**.

11. **Her kural bir `trigger` taşır: cümlenin İÇİNDEN alınmış, birebir,
    bitişik bir parça.** `is able to`, `to fly`, `fly high`. Bu, bu işin **en
    güçlü ölçülebilir kapısıdır**: tetikleyici cümlede (büyük/küçük harf ve
    boşluk normalize edilerek) **bulunamıyorsa paket reddedilir**. Kural
    uydurmanın maliyeti böylece sıfıra iner.

12. **Cümleye özel not kısadır ve kuralın genel tanımı DEĞİLDİR.** Katalogdaki
    `short_en` kuralın kendisini anlatır (bir kez yazılır); modelin ürettiği
    `note` yalnızca **bu cümlede nasıl göründüğünü** anlatır (1-2 cümle).
    Böylece `be able to` 400 cümlede 400 kez yeniden anlatılmaz ve kullanıcı
    tek bir tutarlı kural sayfası görür.

13. **Aşikâr kuralın kapısı iki katmanlıdır:**
    - **Reddeder:** `trivial=True` bir kural `rank=1`de geldiyse. (Ölçülebilir,
      tartışmasız.)
    - **Uyarır:** cümlenin/anlamın CEFR'i, kuralın `assume_known_from`
      bandının üstündeyse. Reddetmez, çünkü 1000 kelimenin 160'ında CEFR yok
      (İş 4 §10) ve "bu öğrenci bunu biliyor" garanti edilemez.

14. **Sıralamanın kendisi ölçülemez** — "gerçekten en göze çarpan bu mu"
    sorusunun mekanik yanıtı yoktur. Bu, İş 4'teki "çeldirici gerçekten
    uymuyor mu" riskinin ikizidir: **kesinlikle red yapma**, her onaylı pakete
    uyarı düş ve pilotta **elle oku**. Dosyanın docstring'inde bunun neden
    böyle olduğu yazılı olacak.

### D. Depo

15. `data/stores/grammar.sqlite` (grammar'ın kendi dosyası; başka app'in
    dosyasına tablo eklenmez):

    - `sentence_grammar` — paket durumu, grup başına:
      `(owner, group_key)` PK, `status`, `reject_reason`, `warnings`, `tier`,
      `source`, `model`, `prompt_hash`, **`source_sha256`**, `updated_at`.
    - `sentence_grammar_rule` — `(owner, ref, rank)` PK, `rule_id`, `trigger`,
      `note`, `tier`, `source`.
    - `sentence_grammar_rule_l1` — `(owner, ref, rank, l1)` PK, `note`,
      `tier`, `source`. Cümleye özel notun çevirisi.
    - `grammar_rule_l1` — `(rule_id, l1)` PK, `name`, `short`, `tier`,
      `source`. **Katalog açıklamasının çevirisi**: satır sayısı katalog
      boyutudur (yüzler), külliyat boyutu değil (binler). Beşinci dil bu
      tablodan yalnızca katalog kadar maliyet çıkarır.
    - `grammar_candidate` — `(owner, ref, seq)` PK, önerilen ad, `trigger`,
      gerekçe, `status` (`new`/`promoted`/`rejected`).

    `owner` sütunu kimliğin parçasıdır: `cloze:12:3` ile ileride
    `reading:...:2` aynı tabloda çakışmadan durur. Dil bir SÜTUNDUR.

16. **`source_sha256` — bayatlık kuralı (İş 5 §12 ile aynı sözleşme).** Analiz,
    analiz ettiği **cümlelerin o anki metnine** bağlıdır. Cümle düzeltilir ya
    da yeniden üretilirse eski kural satırları **bayat**tır: yeniden
    işlenebilir sayılır, panelde/sevkiyatta gösterilmez. Aynı kural çeviri
    için `note`un kaynağına uygulanır.

17. **Katalog ile depo tutarlılığı bir kapıdır:** depoda katalogda olmayan bir
    `rule_id` bulunması bir hatadır. Bunu **yazma anında** engelle (QA) ve
    ayrıca bir denetim testiyle ölç. Katalogdan bir id **silinemez**; ancak
    `merged_into` ile yönlendirilir.

### E. Çeviri

18. İki ayrı, farklı büyüklükte koşu — ikisi de `variant = l1`:
    - `grammar_note_translation`: cümleye özel notlar (külliyat boyutunda).
    - `grammar_catalog_translation`: katalog `name`/`short` çevirisi (katalog
      boyutunda, ucuz). İstenirse insan da yazabilir (`tier=0`).
    Kural **id'si ve `trigger` asla çevrilmez**: `trigger` cümlenin İngilizce
    parçasıdır. Çeviri QA'sındaki "model çevirmemiş" sinyali çalıştırılmadan
    önce **`trigger` metni çıkarılır** — yoksa doğru çeviriler reddedilir
    (İş 5 §16'daki tuzağın aynısı, `es` pilotunda ödenmiş 3 birime mal oldu).

### F. İnsan düzeltmesi ve panel

19. `review` yeni alanlar alır: `grammar` (İngilizce paket: rank + rule_id +
    trigger + note) ve `grammar_l1`. `review/targets.py`ye kayıtları eklenir;
    grammar **ayrı bir dosyadır**, cloze'da olduğu gibi ATTACH ile aynı
    transaction'a alınır ("sorunlu tek satırda hiçbir satır yazılmaz" sözü
    iki dosyada da geçerli). İnsanın yazdığı `rule_id` de katalog kapısından
    geçer.

20. Panelde: kural sayfası (`polyvo panel` altında) iki görünüm sunar —
    **kurala göre** (bir kuralın geçtiği bütün cümleler) ve **cümleye göre**
    (bir sorunun kuralları, sırayla). Aday kurallar ayrı listede, "sevk
    edilmez" etiketiyle. Salt okunur; `polyvo.panel` importu yok.

---

## Pilot — üç kademe (katalog soğuk başlangıcı bu işin en büyük riski)

Katalog boşken kapalı sözlük dayatmak her paketi adaya çevirir. Bu yüzden
pilot **üç kademelidir** ve kademe atlanamaz:

- **Kademe 0 — elle tohum.** Katalog, koşudan ÖNCE elle ~40-80 kuralla
  doldurulur (A1-B1 ağırlıklı: temel zamanlar, modaller, `be able to`,
  mastar/ulaç, karşılaştırma, sıfat sırası, sık öbek fiiller, sayılabilirlik).
  Bu LLM işi değildir, para harcamaz.
- **Kademe 1 — keşif koşusu (`--propose-only`, `--limit 50`).** Model kural
  seçer **ve** eksik gördüklerini aday olarak bildirir; **hiçbir kural satırı
  yazılmaz**, yalnızca adaylar birikir. Kullanıcı adayları okur, katalogu
  büyütür. Amaç: katalogun gerçek külliyatla kalibre edilmesi.
- **Kademe 2 — gerçek koşu (`--limit 50`).** §9.4 biçiminde rapor: işlenen /
  onaylanan / reddedilen + sebep dökümü + **aday sayısı**.
  - **Sayıya güvenme, örneği oku:** en az 10 cümlenin kuralları elle okunur ve
    üç soru yanıtlanır — (a) rank 1 gerçekten cümlenin taşıyıcı yapısı mı,
    (b) aşikâr kural (kopula, tanımlık, çoğul -s) sızmış mı,
    (c) `trigger` gerçekten o kuralın tetikleyicisi mi (cümlede geçiyor olması
    doğru parça olduğunu kanıtlamaz).
  - Aday oranı yüksek kalıyorsa **katalog** düzeltilir, koşu büyütülmez.
- Çeviriye ancak İngilizce üretim okunduktan sonra geçilir;
  `tr` → `es` → `pt-BR` → `de`.

---

## Kapsam dışı — dokunma

- Cloze'un üretimini değiştirme; `sense_cloze*` tablolarına **yazma**.
  `grammar` cümleleri **okur**.
- `lexicon_card`ın örnek cümleleri üzerinde **koşu yapma** (para). Yalnızca
  seam'in onu da taşıyabildiği testle gösterilir.
- `delivery/`e dokunma; gramerin sevkiyatı çok dilli sevkiyat işinin konusu.
  **`delivery materialize --l1 <tr dışında>` KOŞULMASIN.**
- Gramer **öğretme** içeriği (alıştırma, konu anlatımı, quiz) üretme — bu iş
  yalnızca **etiketleme + kısa not**tır.
- Bağımlılık ayrıştırıcı (parser), POS etiketleyici ya da gömme katmanı kurma;
  ölçemediğin şeyi uyarıya bırak.
- Katalogu LLM'e yazdırma. Katalog **insan ürünüdür**; model yalnızca aday
  önerir.
- `core/jobs/` motorunu değiştirme; `model_quality.json` global kalır.
- Kendi başına büyük paralı koşu başlatma.

---

## Kabul ölçütleri

- `modules/grammar` **bir klasör** olarak girdi. `core/cli/app.py` yalnızca
  seam alanı kadar büyüdü; `core/`, `curriculum/`, `delivery/`, `panel/`
  host'u ve `lexicon_card` başka hiçbir yerde **değişmedi** (`git diff` ile
  göster). Cloze'da değişen tek yer `public.py` + `app.py`nin seam ilanı.
- `modules/grammar` altında **hiçbir** kardeş `modules/*` importu yok ve
  `test_layering` bunu **yakalıyor** (testle göster).
- `APP.sentences` ilan eden **sahte bir app**, `grammar`da tek satır
  değiştirmeden işleniyor (testle göster) — genelliğin kanıtı budur.
- Cümlede **bulunmayan** bir `trigger` içeren cevap **reddediliyor** (testle
  göster).
- Katalogda olmayan `rule_id` **reddediliyor**; aday olarak bildirilen yapı
  `grammar_candidate`a düşüyor ve **kural satırı yazılmıyor** (testle göster).
- `trivial=True` bir kural `rank=1`de geldiğinde **reddediliyor**; `rank=2`de
  geçebiliyor (testle göster).
- CEFR'i bilinmeyen cümle **reddedilmiyor**, uyarı alıyor.
- Sıralamanın doğruluğu **red değil uyarı** olarak duruyor ve gerekçesi
  docstring'de yazılı.
- `merged_into` ile birleştirilen bir kural, **depoda tek satır değişmeden**
  okuma anında hedefine çözülüyor; döngü katalog denetiminde **hata veriyor**
  (testle göster).
- `--propose-only` **hiçbir kural satırı yazmıyor**, yalnızca aday yazıyor.
- `--dry-run` tek kuruş harcamıyor ve **tek satır yazmıyor**.
- İkinci koşu → **0 ödenecek çağrı** (üç `kind` için AYRI AYRI: analiz, not
  çevirisi, katalog çevirisi).
- Cümle değiştiğinde o grup **bayat** oluyor, yeniden işlenebilir sayılıyor ve
  panelde bayat görünüyor (testle göster).
- Beşinci bir dil eklemek **şema değişikliği gerektirmiyor**; katalog çevirisi
  külliyat boyutunda değil **katalog boyutunda** çağrı istiyor (sayıyla
  göster).
- Onaylanmamış cloze paketi `grammar`a **girmiyor**.
- İnsan satırı (tier 0) varken o birim için çağrı **istenmiyor**;
  `review export/import` gramer alanlarını taşıyor ve insanın yazdığı
  `rule_id` katalog kapısından geçiyor.
- Mevcut testlerin hepsi yeşil (`pytest -q` ile teyit et; 2026-09-07
  itibarıyla 371).
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- Türkçe kısa docstring'ler **baştan** yazılmış.
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı — aday
  sayısı, katalogun büyüme miktarı ve elle okunan 10 cümlenin değerlendirmesi
  dahil.

---

## Verilen kararlar (agent bunları yeniden sormaz)

1. **Ayrı app (`modules/grammar`), cloze'un alt paketi değil.** Gerekçe:
   girdisi bir cümledir, cloze'a özel hiçbir şey bilmez.
2. **Cümleler katkı seam'iyle gelir (`APP.sentences`), import'la değil.**
   Kardeş app importu yasak; genellik ancak böyle bedava olur.
3. **Kapalı katalog + açık aday havuzu.** Model id uydurmaz; katalogu insan
   büyütür.
4. **Id biçimi `EN.<ALAN>.<KURAL>`, kalıcı.** Birleştirme `merged_into` ile,
   satırları yeniden yazmadan yapılır.
5. **Cümle başına en çok 3 kural, sıralı.** Genel açıklama katalogda (bir kez),
   cümleye özel not modelden (kısa).
6. **Analiz birimi gruptur** (cloze'da: bir anlamın 3 cümlesi) — grup başına
   tek çağrı.
7. **Aşikârlık kapısı:** `trivial` kural rank 1'de **red**; seviye üstü kural
   **uyarı**.
8. Analiz İngilizce üretilir, notlar sonra çevrilir; `trigger` ve `rule_id`
   çevrilmez.
