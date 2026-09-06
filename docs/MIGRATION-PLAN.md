# Polyvo word-databases — yeniden yapılandırma planı (v2)

Kaynak repo: `C:\Users\ahmet\Desktop\Projects\python\word-database`
Hedef repo:  `C:\Dev\MyProjects\Polyvo\word-databases`

Bu dosya **donmuş kapsam** belgesidir. Her adım kendi başına bitirilir, kendi kabul
testiyle doğrulanır ve ancak ondan sonra bir sonrakine geçilir. Bir adımı bölmek
serbest, sırayı bozmak değil — sıra bağımlılık sırasıdır.

> v1 planı `docs/MIGRATION-PLAN.v1.md` olarak duruyor. Aşağıdaki §0.1'de listelenen
> dört karar kapsamı daralttığı için v1'in Adım 4/6/7'si düştü. Mimari (4 katman,
> tek yönlü bağımlılık, app manifesti) v1'den **aynen** korunur; değişen şey ne
> üretileceğidir, nasıl üretileceği değil.

---

## 0. Neden taşıyoruz

Eski yapı yanlış klasörlendiği için değil, **iki farklı eksen tek çuvala
doldurulduğu** için karmaşık:

| eksen | doğası | anahtar | yeniden üretilebilir mi |
|---|---|---|---|
| veri hattı aşaması (build/enrich) | tam-kopya snapshot, tag'li | `data/builds/<tag>/NN_x/` | evet — pahalı ama deterministik |
| omurga (universe/items) | ucuz, deterministik izdüşüm | `stable_key` → `workspace/` | evet — bedava |
| üretim işi (lexicon kartı) | kimlik-anahtarlı, tag'siz | `(family, kind, stable_key)` | **hayır — para** |

`src/stages/content/` bugün üçünü birden barındırıyor; ortak makine (`runner.py`,
685 satır) da onun *içinde*, öyle ki "ayrık" olduğu söylenen `src/modules/kernel/`
bile `src.stages.content.runner`'ı import ediyor. Dosyaları taşımak bu bağı aynen
getirir. **Önce eksenler ayrılır, sonra taşınır.**

### 0.1 Kapsam kararları (2026-09-05, ikinci tur)

Dört karar alındı; planın geri kalanı bunların sonucudur.

| # | karar | sonucu |
|---|---|---|
| K1 | **Öğrenme birimi = lemma + POS.** Anlamlar JSON değil ayrı tablo (`senses`), her birinin kendi kalıcı `sense_id`'si var. | Uygulama isterse kelime başına tek FSRS kartı, isterse anlam başına kullanır. Fikir değişirse **şema değişmez.** |
| K2 | **V1 evreni: 300 kelimelik pilot.** Ölçek prompt ve QA oturduktan sonra açılır. | Prompt değişimi cache anahtarını kaydırır; 5.000'i erken üretmek parayı iki kez ödemektir. |
| K3 | **L1 (TR) kartın parçası, ayrı dosyada.** Aynı LLM çağrısında üretilir, `i18n_tr.db`'ye ayrı yazılır. | Ayrı çeviri app'i yok. Yeni dil = yeni dosya, şema değişikliği yok. |
| K4 | **`content/en` ham KANIT olarak taşınır, kimlik olarak asla.** | v1 planı §3'ün "hiçbir şey taşınmıyor" hükmüne tek istisna. Ayrıntı: §3. |

### 0.1.1 Build kararları (2026-09-05, üçüncü tur)

Kaynak dosyaları indirilip ölçüldükten sonra alınan üç karar.

| # | karar | gerekçe |
|---|---|---|
| K5 | **Çok kelimeli girdiler evrene girer** (`according to`, `bank account`, `bulk up` — CEFR-J'de 144, Octanove'da 10). Kaynağın POS'u **korunur**, üzerine `is_multiword` bayrağı eklenir. | Kalıplar öğrenciyi tek kelimelerden daha çok zorlar. POS'u `phrase` ile ezmek bilgi kaybı olurdu: `according to` gerçekten bir edat. IPA ve çekim alanları NULL kalır — şema zaten izin veriyor. |
| K6 | **CEFR çakışmasında düşük seviye kazanır.** 116 vaka ölçüldü (`abundance` B1 vs C2, `abolish` B2 vs C2). | Bir kelimeyi olduğundan kolay saymak, zor saymaktan az zararlı: öğrenci erken karşılaşır, en kötü ihtimalle tekrar eder. Ters durumda kelime hiç karşısına çıkmaz. |
| K7 | **POS'suz liste girdisi tek başına öğe üretemez.** `candidates.pos` NULL olabilir; ayrı bir çözümleme adımı POS atar. Çözülemeyenler `unresolved` tablosuna yazılır ve **raporlanır**, sessizce düşürülmez. | Ölçüldü: NGSL/NAWL/TSL/BSL/New Dolch POS taşımıyor. 5.715 lemmanın 4.387'sini CEFR-J/Octanove kapsıyor, 1.328'ini kapsamıyor; bunların 946'sı `legacy_dist`'te var, **382'sinin hiçbir POS kaynağı yok**. K1 kimliği `(l2, headword, pos)` olduğu için POS'suz aday öğe olamaz — ama sessizce kaybolması da kabul edilemez (§6.1). |

**K7'nin sonucu:** OEWN (CC BY 4.0) pilotta da gerekli, yalnızca POS ve anlam
sayısı için. Alternatif, 382 kelimeyi tier 3'te kabul edip evren dışında
bırakmaktır; karar Adım 3'ün raporuna bakılarak verilir.

Ayrıca **düşen kapsam** (kullanıcı kararı): 7'li set gruplama, paragraf üretimi,
okuma modülü, cloze. V1 tek bir şey üretir: **yüksek kaliteli İngilizce öğretim
sözlüğü.** Diğerleri sonradan *birer klasör* olarak eklenir — bu zaten mimarinin
varlık sebebi.

### 0.2 Ürün bağlamının bu repoya dayattığı dört şey

Polyvo ekosistem vizyonundan (Chrome eklentisi + Flutter + Next.js + D1) bu
repoya düşen dört kısıt:

1. **Bu repo çalışma zamanı değil, ön-ödenmiş önbellektir.** En sık N kelimenin
   cevabını önceden ve daha iyi bir modelle üretir; uzun kuyruğu uygulama anlık
   halleder. Bu yüzden **DB'nin ürettiği kayıt ile uygulamanın anlık ürettiği
   kayıt aynı biçimde olmalıdır** — yoksa iki ayrı kart tipi doğar ve ikisi de
   yarım kalır.
2. **FSRS kimliği kutsallaştırır.** Kullanıcı tekrar geçmişi `item_id`'ye bağlanır.
   Yayınlanmış bir kimliğin anlamı değişemez; §6'nın 2. ve 3. maddesi bu yüzden
   tavsiye değil, zorunluluktur.
3. **Otantik içerik bağlamı bu reponun işi DEĞİL.** Kullanıcı Netflix'te bir
   kelimeye tıkladığında cümle, kare ve ses onundur. Bu repo **lemma düzeyi
   bilgi** üretir; öğretici örnek cümle hariç bağlam üretmez.
4. **Gruplama şemaya girmez.** "Belki 7'li setler yaparım belki yapmam" →
   kelimeye seviye ve sıra verilir; gruplama uygulamanın *sorgusu* olur, DB'nin
   *kimliği* değil.

### 0.3 Mevcut `content/en` neden yeniden kullanılamaz (ölçüm, 2026-09-05)

| bulgu | kanıt |
|---|---|
| Anlam envanteri dilbilimsel | 13.500 lemma → 15.674 öğe. `know#1` (WordNet) ve `know#2` (Wiktionary) ikisi de verb, aynı anlam, iki kart. `think#1` = *isim* "an instance of deliberate thinking" — A1 kelimesinin en nadir anlamı. |
| Gloss'lar sözlük tanımı | ortalama 59, maks. 457 karakter; 1.061 kart 120 karakterden uzun. `liver` → 60 kelimelik tıp metni. |
| Örnekler korpus döküntüsü | `know#2`: "Did he hell. They never bloody did." + mojibake. `think#2`'de aynı cümle iki kez. 315 kart örneksiz. |
| Eşanlamlılar synset ilişkisi | `baffle` → `gravel, beat, beating, get`. |
| L1 eksik ve yanlış | %39'u (6.131) TR gloss'suz. `good#1` → "daha iyi", `constable` → "sınır ötesi polis", `interstate` → "uluslararası otoyol". |
| CEFR eğitim eğrisi değil | %62'si B2+C1. `colby` (peynir) B2, `liver` C1. |
| POS dağılımı kaynak yanlılığı | 15.674'ün 10.539'u isim (%67). Bu dilin değil, Wiktionary/WordNet'in dağılımı. |
| Sevkiyat zaten yarım | `_dist_meta.json`: `paragraphs=0, sentences=0, questions=0, set_modules=0`; 8.414 öğe cloze'suz. |

**Çıkarım (K4'ün gerekçesi):** kaynaklar aday ve kanıt olarak iyi, son ürün alanı
olarak kötü. Öğrenciye görünen hiçbir alan kaynaktan doğrudan kopyalanmaz.

---

## 1. Mimari — 4 katman, tek yönlü bağımlılık

```
katman 3  delivery    materialize · snapshot · verify · panel host
              ^ sadece okur
katman 2b modules     LLM işleri; her biri bağımsız "app"
              ^
katman 2a curriculum  evren · kimlik — SIFIR LLM
              ^
katman 1  dictionary  build · enrich — snapshot'lı veri hattı
              ^
katman 0  core        llm · sqlite · paths · config · dil · metin QA · jobs motoru
```

**DEMİR KURAL: alt katman üst katmanı import edemez.** Bu kural bir yorum değil,
bir testtir — `tests/test_layering.py` her adımda çalıştırılır.

**İKİNCİ KURAL: bir "app" = bir aile, içinde birden çok `kind`.** Ortak
`stable_key`, ortak store satır ailesi, ortak QA. `lexicon_card` app'i EN gloss'u,
örnekleri ve TR karşılığı aynı ailede tutar (K3).

---

## 2. Sıfırdan üretme vs artımlı iyileştirme

Bu ayrım planın çekirdeğidir; iki katmanda cevap **farklıdır**:

| katman | içerik | maliyet | davranış |
|---|---|---|---|
| **ucuz** | kelime evreni, frekans, POS, IPA, CEFR etiketi, kanıt metinleri | bedava, deterministik | **her koşuda sıfırdan.** Yeniden üretmek tutarlılığı garanti eder; elle yamamak sessiz sapma üretir |
| **pahalı** | LLM'in yazdığı gloss, TR karşılık, örnek cümle + insan düzeltmeleri | **para ve zaman** | **asla sıfırdan.** Kimlik anahtarlı, artımlı; yalnızca eksik olan doldurulur |

`bank` kelimesinin TR karşılığı bir kez yazılır, `data/stores/` içinde kimliğiyle
oturur ve bir daha ödenmez — kaynak listesi değişse de, evren büyüse de.
"Bunu daha önce yazdım mı" kontrolü **motorun içinde tek bir kapıdır**, her
modülde yeniden yazılmaz (§6.4).

---

## 3. Veri politikası

Kod sıfırdan. Veri için tek kural: **kanıt taşınır, kimlik taşınmaz.**

**TAŞINIR (K4):** `content/en` üçlüsü `data/raw/legacy_dist/` altına konur ve
`dictionary/build/ingestors/legacy_dist.py` tarafından okunur. Alınanlar:
headword, POS, frekans sırası, IPA (14.632 satır), CEFR *ipucu*, ve LLM'e
verilecek **kanıt** (sözlük tanımı, korpus örneği, synset eşanlamlıları).
Kazanç: Kaikki'nin 10+ GB dump'ını indirip ayrıştırmadan hat uçtan uca çalışır.

**TAŞINMAZ:** `item_id`, `stable_key`, `sets`, `set_items`, `cloze`,
`gatekeeper_options`, `item_embeddings`, eski `cache/llm_cache.sqlite`, eski
`stores/`. Kimlik uzayı **sıfırdan** kurulur.

**Bilinen bedel:** mevcut insan düzeltmeleri (tier=0) ve `item_id`/`set_id`
sürekliliği sıfırlanır. Flutter'a çıkmış bir sevkiyat varsa yeni kimlik uzayı
onunla uyuşmaz. Kabul edilmiş maliyettir.

**Sonuç:** yeni repoda hiçbir "eski veriyi tanı/göç ettir" kod yolu yazılmaz.
`legacy_dist.py` bir *ingestor*'dur — diğer kaynaklarla aynı arayüzü kullanır,
ayrıcalığı yoktur ve kaynak listesi olgunlaştığında **silinebilir**.

---

## 4. Hedef klasör ağacı

```
word-databases/
├── pyproject.toml            # `polyvo` konsol komutu
├── polyvo.toml               # TEK konfig
├── data/
│   ├── raw/legacy_dist/         content/en'in kopyası — KANIT (K4)
│   ├── cache/                   GLOBAL, tag'siz, SİLİNEBİLİR AMA PAHALI
│   ├── stores/                  GLOBAL, tag'siz, KUTSAL — kimlik + ödenmiş kararlar
│   ├── human/                   GLOBAL, gitignore, tier=0
│   ├── builds/<tag>/01_lexicon/ aday + kanıt havuzu (ucuz, yeniden üretilir)
│   ├── workspace/<tag>/<l2>/    evren seçimi + izdüşüm — serbestçe silinir
│   └── dist/<tag>/<l2>/         sevkiyat: core.db · en.db · i18n_tr.db
├── src/polyvo/
│   ├── core/       config · paths · sqlite · llm/ · lang/ · text/ · cli/ · jobs/
│   ├── dictionary/ stages.py · build/ingestors/ · enrich/
│   ├── curriculum/ universe.py · items.py          # sets.py / grouping.py YOK
│   ├── modules/lexicon_card/  app · prompt · qa · store · panel/ · tests/
│   ├── delivery/   materialize.py · snapshot.py · verify/
│   ├── review/     insan düzeltme yolu
│   └── panel/      HOST: http · static shell · APP KEŞFİ
└── tests/
```

---

## 5. Şema taslağı (K1 + K3)

### 5.1 `data/stores/identity.sqlite` — KUTSAL

```sql
items    (item_id INTEGER PRIMARY KEY,      -- AUTOINCREMENT YOK; monotonik tahsis
          l2, headword, pos, created_at,    -- UNIQUE (l2, headword, pos)
          stable_key)                       -- "en:bank:noun"
senses   (sense_id INTEGER PRIMARY KEY, item_id, sense_ordinal, is_primary,
          created_at)                       -- UNIQUE (item_id, sense_ordinal)
counters (name TEXT PRIMARY KEY, next_id INTEGER)
```

Anlam düzeltmesi **UPDATE**'tir; delete+insert değil (§6.3).

### 5.2 `data/stores/lexicon.sqlite` — ödenmiş kararlar

```sql
sense_cards    (sense_id PK, gloss_en, register, usage_note,
                tier, source, model, prompt_hash, updated_at)
sense_gloss_l1 (sense_id, l1, gloss, tier, source, model, PRIMARY KEY(sense_id,l1))
sense_examples (sense_id, seq, text, tier, source, PRIMARY KEY(sense_id,seq))
item_phonetics (item_id, variant, ipa, source, PRIMARY KEY(item_id,variant))
item_forms     (item_id, form_type, value, PRIMARY KEY(item_id,form_type))
item_level     (item_id, cefr, freq_rank, source)
```

`tier`: 0 = insan, 1/2 = sözlük tohumu, 3 = model. **İnsan mutlak kazanır.**

### 5.3 `data/builds/<tag>/01_lexicon/lexicon.sqlite` — ucuz, yeniden üretilir

```sql
candidates (headword, pos, freq_rank, freq_per_million, cefr_hint, source)
evidence   (headword, pos, kind, payload_json, source)
           -- kind: definition | example | synonym | antonym | ipa | form
```

### 5.4 `data/dist/<tag>/<l2>/` — sevkiyat

Üç dosya düzeni **korunur** (`core.db` / `en.db` / `i18n_tr.db`): Flutter yerel
SQLite ve Cloudflare D1 ile uyumlu, dil eklemek dosya ekler.

---

## 6. Geri getirilmeyecek bilinen kusurlar

Eski repoda ölçülerek bulunmuş, tekrar etmemesi gereken şekiller:

1. **Uyarı basıp exit 0 dönen kapı, kapı değildir.** İhlalde sıfır çıktı + exit 1.
2. **Kimlik üreteci "serbestçe silinebilir" klasörde yaşayamaz.** Tüm id tahsisi
   `data/stores/`'ta, `AUTOINCREMENT` kullanmadan.
3. **Alan değişimi kimlik değişimi değildir.** Anlam düzeltmesi `UPDATE`.
4. **"Bunu daha önce gördüm mü" kontrolü, karar verilen satırı dışlamalı.**
5. **`cur.lastrowid` UPSERT'ten sonra kullanılmaz.** Doğal anahtardan yeniden oku.
6. **Aynı dosyaya yazan iki komut = aynı kilit.** `busy_timeout` tek yerde.
7. **Garanti edilemeyen QA kontrolü reddetmez, uyarır.**
8. **Kodun test etmediği bir sonucu iddia eden tanı mesajı yazılmaz.**
9. **İki komut birleştirilirken hayatta kalan prompt, ikisinin birleşimi
   değildir.** Alan alan diff'le.
10. **`MAX(id)` satır sayısının vekili değildir.**

---

## 7. Adımlar

> **Sıra düzeltmesi (2026-09-05).** Adım numaraları katman numaralarıdır,
> yürütme sırası değil. Ölçüldü: `dictionary/build`'in `core/jobs`'a **hiçbir
> bağımlılığı yok** — build sıfır LLM çağrısı yapar, kimlik tahsis etmez,
> yalnızca `core/{config,paths,sqlite}` kullanır. Dolayısıyla yürütme sırası:
>
> **1 → 3 → 2 → 4 → 5 → 6 → 7**
>
> Gerekçe sadece "yapılabilir" değil: motorun sözleşmesi *gerçek* bir birime
> karşı tasarlanmalı, hayal edilene karşı değil. Eski repoda `runner.py`'nin 685
> satıra çıkmasının sebebi soyut bir motoru sonradan gerçeğe uydurmaktı.
> Bağımlılık kuralı korunuyor: `core/jobs/identity.py` Adım 4'ten **önce**
> yazılır, bu yüzden 2 hâlâ 4'ün önünde.

### Adım 1 — `core/` iskeleti  ✅ (2026-09-05, 19 test yeşil)

`pyproject.toml`, `polyvo.toml`, `core/{config,paths,sqlite,env}`, `core/llm/*`,
`core/lang/tr`, `core/text/*`, `core/cli/*` (app keşfi), `tests/test_layering.py`.

### Adım 2 — `core/jobs/` genel üretim motoru

**Üret:** `base.py` (Job sözleşmesi: `load_units`/`build_prompt`/`run_qa`/`write`),
`plan.py` (PlanReport + cache yoklaması + `confirm_plan`), `engine.py`
(plan → onay → döngü → yaz → mutabakat, kesinti-güvenli commit), `store.py`
(artifact deposu + **policy'li yazma kapısı**), `identity.py` (monotonik tahsis),
`attempts.py` (INSERT-ONLY).

Yazma kapısı ve plan mantığı *policy*'dir; ikinci bir yol açılmaz.
§2'nin "artımlı" kuralı **burada** somutlaşır: cache yoklaması ve tier
karşılaştırması motorun içinde, modülde değil.

**Kabul:** redo matrisi testi yeşil; `PlanReport.render` çıktı biçimi tanımlı;
`--dry-run`'da `paid_calls = 0`.

### Adım 3 — `dictionary/`

**Üret:** `stages.py` (aşama kayıt defteri), `build/command.py`,
`build/ingestors/legacy_dist.py` (K4), `build/{ranking,cefr,word_cleaner}.py`.

**Kabul:** `polyvo dictionary build --limit 300` → `01_lexicon/lexicon.sqlite`
dolu; `_stage_meta.json` satır sayıları raporlu; POS dağılımı ve CEFR dağılımı
komut çıktısında görünür (§0.3'teki iki eğrilik ölçülebilir olsun diye).

### Adım 4 — `curriculum/`

**Üret:** `universe.py` (evren seçimi + gate), `items.py` (kimlik tahsisi +
`workspace` izdüşümü). **`sets.py` ve `grouping.py` YOK.**

**Kabul:** `workspace/` tamamen silinip yeniden üretildiğinde `item_id` ve
`sense_id` **birebir aynı** çıkar (`tests/test_item_identity.py`).

### Adım 5 — `modules/lexicon_card/` (ilk ve tek app; sözleşmeyi o belirler)

**Üret:** `app.py` manifest, `prompt.py`, `store.py` (EN kart + TR gloss tek
transaction), `qa.py`, `panel/`.

Tohum kuralı: insan tohumu (tier 0) mutlak kazanır, sözlük tohumu (tier 1/2)
yalnızca modelin alanı yoksa yazılır.

**Kabul:** 300 kelimelik pilot uçtan uca; ikinci koşuda `paid_calls = 0`
(artımlılık kanıtı); `qa.py` reddetme oranı raporlanır.

### Adım 6 — `delivery/`

**Üret:** `materialize.py` (kapı **önce** çalışır, ihlalde **sıfır dosya** yazıp
exit 1), `snapshot.py`, `verify/`.

**Kabul:** `polyvo verify pipeline` yeşil; bozuk kaynakla materialize exit 1 ve
**hiç dosya yazmamış**.

### Adım 7 — `review/` + `panel/`

İnsan düzeltme yolu (export/import + `data/human/` yedeği; import
`source="human"` hardcoded, tier asla yedekten okunmaz) ve panel host'u
(sayfa listesi yok; `APP.panel` olan her modül kendi sayfasını getirir).

### Ertelendi (v2 kapsamı)

`modules/cloze`, `modules/paragraph`, `modules/reading`, `curriculum/sets`,
embedding katmanı. Her biri mimariye *bir klasör* olarak girer; bu plandaki
hiçbir dosyanın düzenlenmesini gerektirmemelidir — mimarinin sınavı budur.

---

## 8. Sonraki karar turu: açık kaynak seçimi

Adım 3'ten önce karara bağlanacak. Aday havuzu ve her birinden **ne alınacağı**
ayrı bir belgede (`docs/SOURCES.md`) lisans doğrulamasıyla birlikte yazılır.
Şu an hiçbiri taahhüt edilmemiştir; `legacy_dist` ingestor'ı bu kararı
**bloke etmemek** için vardır.

---

## 9. İlerleme

Yürütme sırası: **1 → 3 → 2 → 4 → 5 → 6 → 7** (bkz. §7 sıra düzeltmesi)

- [x] Adım 1 — core iskeleti  (2026-09-05, 19 test yeşil)
- [x] Adım 3 — dictionary (kaynak indirme + build)  (2026-09-05, 59 test yeşil)
- [x] Adım 2 — jobs motoru  (2026-09-05, 105 test yeşil)
- [x] Adım 4 — curriculum (evren + kimlik)  (2026-09-05, 115 test yeşil)
- [x] Adım 5 — lexicon_card **sistemi hazır** (2026-09-06, 131 test yeşil)
      ← pilot koşusu kullanıcıda, bkz. §9.4
- [x] Adım 6 — delivery  (2026-09-06, 143 test yeşil; 291 öğelik pilot sevkiyat, `verify` 16/16)
- [x] Adım 7 — review + panel  (2026-09-06, 178 test yeşil; insan yolu gerçek depo kopyasında uçtan uca koştu, panel gerçek depoyu servis etti)

### 9.0 Adım adım ne çıkar, ne kadara

Sıra yürütme sırasıdır (§7). "LLM parası" sütunu o adımın **kendi** harcaması;
önceki adımlarınki dahil değil.

| sıra | adım | ne çıkar | LLM parası |
|---|---|---|---|
| 1 | `core/` iskeleti | config · paths · sqlite · llm · cli keşfi | **yok** |
| 2 | `dictionary/build` | `01_lexicon/lexicon.sqlite` — aday + kanıt havuzu | **yok** (deterministik) |
| 3 | `core/jobs` | üretim motoru + yazma kapısı + kimlik tahsisi | **yok** (sahte sağlayıcıyla test) |
| 4 | `curriculum/` | evren seçimi + `item_id`/`sense_id` kimlik uzayı | **yok** |
| 5 | `modules/lexicon_card` | EN kart + TR gloss + örnek | **İLK HARCAMA** — 300 kelimelik pilot |
| 6 | `delivery/` | `core.db` · `en.db` · `i18n_tr.db` sevkiyatı | **yok** |
| 7 | `review/` + `panel/` | insan düzeltme yolu + panel host | **yok** |

Para yalnızca 5'te harcanır ve orada da **bir kez**: motorun yazma kapısı
ödenmiş bir kararı yeniden ödetmez (§2, §9.2).

### 9.1 Adım 3 ölçümü (2026-09-05)

`polyvo dictionary build --tag v7 --tier 3` çıktısı:

| Ölçü | Değer |
|---|---|
| benzersiz başlık | **9.881** |
| aday satırı (headword+pos) | 11.009 |
| tier 1 / 2 / 3 (benzersiz) | 2.929 / 4.016 / 2.982 |
| kanıt satırı | 57.454 (evren dışı 155.412 atıldı) |
| POS: kanıttan çözülen | 876 (K7, `legacy_dist`) |
| POS'suz kalan | 364 — **atılmadı**, `unresolved`'da |
| eleme | 3 kısaltma, 3 kelime dışı (`'s`,`'m`,`'re`), 1 rakamlı |
| determinizm | iki koşu **bayt bayt aynı** (sha256 eşit) |

SOURCES.md §2.1'deki 9.981 tahmini ile fark (**-100**) tamamen eleme ve
yazım varyantı birleştirmesinden gelir; her satırın sebebi `unresolved`
tablosunda.

**K7 kararı kapandı:** OEWN'e pilot için gerek yok. POS'suz kalan 364 başlık
(%3,7) tier 3'te bekler; Adım 5'te LLM zaten POS'u üretecek, bu 364 için
`pos_source='model'` olur.

### 9.2 Adım 2 ölçümü (2026-09-05)

`src/polyvo/core/jobs/` — 19 dosya (3'ü paket docstring'i), en uzunu 118 satır:

| dosya | tek sorumluluğu |
|---|---|
| `base.py` | Job sözleşmesi (`load_units`/`build_prompt`/`run_qa`) |
| `schema.py` | motorun sahip olduğu iki depo dosyası + DDL |
| `identity.py` | monotonik kimlik tahsisi (`AUTOINCREMENT` yok) |
| `attempts.py` | INSERT-ONLY deneme günlüğü |
| `store/policy.py` | **yazma kapısı** — saf kural, DB'siz |
| `store/base.py` | kapıyı atlanamaz kılan taban sınıf |
| `plan/verdict.py` | **redo matrisi** — saf karar |
| `plan/planner.py` | verdikt + önbellek yoklaması → plan |
| `plan/report.py` · `render.py` · `confirm.py` | sayaç · biçim · onay |
| `engine/budget.py` · `progress.py` · `attempt.py` · `loop.py` · `reconcile.py` | bütçe · ilerleme · deneme · döngü · mutabakat |
| `engine/run.py` | 8 adımlık ince orkestratör |
| `cli_args.py` | `--redo/--dry-run/--yes/--max-new/--pace-delay` |

**Kabul koşulları — hepsi test edilmiş (`tests/test_jobs_policy.py`,
`tests/test_jobs_engine.py`, 46 yeni test):**

| koşul | durum |
|---|---|
| redo matrisi (3 mod × 5 durum) | ✅ tamamı düz yazılmış, döngüyle üretilmemiş |
| `PlanReport` çıktı biçimi tanımlı | ✅ `format_plan` saf fonksiyon, satır listesi döner |
| `--dry-run`'da harcama | ✅ **0** — sahte sağlayıcı hiç çağrı almıyor |
| ikinci koşuda `paid_calls` | ✅ **0** (artımlılık) |
| depo silinip önbellek kalırsa | ✅ `paid_calls = 0`, `cached_calls = 3` |
| bütçe tavanı | ✅ birimi yarım bırakmaz, kalanlara dokunmaz |
| kesinti | ✅ özet basılır, sonra istisna yukarı fırlar |

**Plandan sapan üç tasarım kararı (gerekçeleriyle):**

1. **`store.py` somut bir tablo değil, ABC + policy.** §5.2 modül deposunun
   şeklini (`sense_cards`, `sense_gloss_l1`, …) zaten sabitliyor; core'da
   ikinci bir genel `artifact` tablosu olsaydı aynı veri iki yerde dururdu.
   Core'un sahip olduğu şey **kapı**, içerik değil. Kapı `save()` içinde,
   `_write_row` private — "ikinci bir yol açılmaz" bu demek.

2. **Ödenecek çağrı sayısı tek sayı değil, ARALIK.** `max_attempts > 1` olan
   bir işte tek sayı vermek koşu sonunda **her zaman** yanlış bir "plandan
   saptı" uyarısı üretirdi (§6.8). `paid_calls`..`paid_calls_max`.

3. **Yazma kapısı `bool` değil `WriteDecision(write, reason)` döner.** Rapor
   satırını sebebi üreten yer yazar; çağıran taraf tahmin etmez (§6.8).

**Bilinen ve kabul edilmiş boşluk:** `--redo` verdikti "dene" derken yazma
kapısı "yazamazsın" diyebilir (modeli bilinmeyen, reddedilmiş bir satır).
Çağrı ödenir ama QA yine reddederse satır yazılmaz. Bu bilerek böyle:
"bilmiyorum" bir yükseltmeyi engellememeli, ama bilinmeyen bir modeli de
ezmemeli. Sonuç `blocked` sayacında **sebebiyle** raporlanır, sessizce
kaybolmaz.

### 9.3 Adım 4 ölçümü (2026-09-05)

`src/polyvo/curriculum/` — 6 dosya (+ `commands/`), en uzunu ~110 satır:

| dosya | tek sorumluluğu |
|---|---|
| `universe.py` | evren seçimi (saf, DB'siz) + **kapı** (`gate`) |
| `items.py` | kimlik tahsisi (`core/jobs/identity.py` üstünde) + workspace izdüşümü |
| `schema.py` | `identity.sqlite`'a `items`/`senses` ekler + `universe.sqlite` DDL'i + `source_config.json` yazıcısı |
| `app.py` · `commands/select_command.py` | CLI manifesti + `polyvo curriculum select` orkestrasyonu |

**Kabul koşulu (`tests/test_item_identity.py`, 10 yeni test) — geçti:**
`workspace/` silinip yeniden üretildiğinde `item_id`/`sense_id` birebir aynı
çıkıyor; ayrıca daha sert bir sürüm de yeşil: `data/stores/identity.sqlite`
**de** silinip tam sıfırdan yeniden üretilse bile aynı sonuç çıkıyor, çünkü
`universe.select_universe` adayları HER ZAMAN aynı sırada (freq_rank →
alfabetik) döner ve tahsis o sıraya göre yapılır.

**Kapı (`universe.gate`) neyi test ediyor:** seçilen evren boşsa ya da içinde
yinelenen `(headword, pos)` varsa `UniverseError` — çağıran (`select_command`)
bunu yakalamaz, hiçbir dosya yazılmadan exit 1 döner (§6 kural 1).

**Plandan sapmayan ama not edilmesi gereken karar:** `item_id`/`sense_id`
tahsisi `core/jobs/identity.py`'nin **aynısını** kullanıyor (`allocate_one`,
`counters` tablosu) — Adım 2'de bu dosyanın Adım 4'ten önce yazılmasının
sebebi tam olarak buydu (§7 sıra düzeltmesi notu). İkinci bir kimlik üreteci
yazılmadı.

**Bu adımda henüz olmayan (bilerek):** anlam bölme (`sense_ordinal` hep 1) —
LLM işidir, v2 kapsamında (`modules/lexicon_card` sonrası).


### 9.4 Adım 5 ölçümü (2026-09-06) — pilot koşuldu

Sistem sahte sağlayıcıyla (ağsız) ölçüldü, ardından **300 kelimelik gerçek
pilot kullanıcı tarafından koşuldu**. Sonuçlar bu bölümün sonunda.

**Dosya sorumlulukları (`src/polyvo/modules/lexicon_card/`, 653 satır, 12 dosya):**

| dosya | tek sorumluluk |
|---|---|
| `units.py` | `workspace/<tag>/<l2>/universe.sqlite` → `Unit` listesi (`item_id` sırasında) |
| `seed.py` | `builds/.../lexicon.sqlite`'ın `evidence`'ını birimlere bağlar |
| `prompt.py` | modelden istenen şey — JSON iskeleti + L1 biçim kuralları |
| `qa.py` | cevabın içerik kapısı; kabul edilen yükü üretir |
| `store.py` | `lexicon.sqlite`'a yazma (`ArtifactStore` alt sınıfı) |
| `schema.py` | `data/stores/lexicon.sqlite` DDL'i |
| `job.py` | `Job` sözleşmesinin 3 metodunu yukarıdakilere bağlar |
| `commands/cards_command.py` | bayrak → `engine.run` (iş yapmaz) |
| `app.py` · `panel/` | manifest + panel sayfası (router Adım 7'de) |

**§5.2 şemasından iki ek — ikisi de motorun sözleşmesi gereği:**
`sense_cards.stable_key` (`load_existing` TEK sorgu olsun diye) ve
`sense_cards.status`/`reject_reason` (redo matrisi "kötü satır"ı ancak
`status` ile tanır — statüsü olmayan depoda onarım imkânsızdır).

**Tohum kuralının uygulanışı (lisans kapısıyla birlikte):** `shippable=False`
kaynaklardan gelen tanım/örnek/eşanlamlı **yalnızca prompt bağlamına** girer,
depoya asla yazılmaz. Depoya yazılabilen tek tohum IPA'dır (`ipa_dict`, MIT,
`shippable=True`) ve o da yalnızca modelin alanı yoksa (`store._write_seed`).
İnsan tohumunu (tier 0) zaten yazma kapısının kendisi korur.

**Kabul kriterleri (`tests/test_lexicon_card.py`, 16 yeni test) — geçti:**

* kart bütün parçalarıyla (EN kart + L1 gloss + 2 örnek + seviye) tek
  transaction'da yazılıyor;
* **ikinci koşuda `paid_calls = 0`** ve sağlayıcıya tek çağrı gitmiyor
  (artımlılık kanıtı — Adım 5'in asıl kabulü);
* `--dry-run` tek kuruş harcamıyor ve **hiçbir satır yazmıyor**;
* QA 7 ayrı bozuk cevabı sebebiyle reddediyor; reddedilen satır içerik
  yazmıyor, yalnızca `status='rejected'` + `reject_reason` ile duruyor
  (`--redo bad` onu böyle bulur);
* insan satırı (tier 0) varken plan çağrı bile istemiyor.

**Model:** pilot bilerek tek modele sabit — `cloudflare:@cf/qwen/qwen3-30b-a3b-fp8`
(rank 40, `model_quality.json`). İki farklı modelle yarım dolmuş bir depo,
QA reddetme oranını ölçülemez hale getirirdi. `--provider/--model` ile
değiştirilebilir ama varsayılan budur.

**Gerçek pilot ölçümü (300 kelime, `cloudflare:@cf/qwen/qwen3-30b-a3b-fp8`):**

| ölçü | değer |
|---|---|
| işlenen kelime | 300 |
| onaylanan | **281** (%93,7) |
| reddedilen | 19 (%6,3) |

Red sebepleri: `gloss_en_kelimenin_kendisini_iceriyor` ×10 (çoğu işlev
sözcüğü — *a, to, for, that, or, with*), `l1_ceviri_yapilmamis` ×4,
`looks_conjugated` ×3, `ornek_cumle_cok_kisa` ×2. Yani red oranının büyük
kısmı sistemik bir prompt/QA kusuru değil, işlev sözcüklerinin doğası.

**Onarım koşusu (redo matrisi ilk kez gerçek parayla sınandı):**
`--redo bad --model @cf/meta/llama-3.3-70b-instruct-fp8-fast` (rank 20 < 40)
yalnızca reddedilen 19 satırı yeniden işledi, onaylı 281 satıra **hiç
dokunmadı**. Sonuç: 10 onay, 9 hâlâ red. Depodaki son durum **291 onaylı**.

### 9.5 Adım 6 ölçümü (2026-09-06) — sevkiyat

**Dosya sorumlulukları (`src/polyvo/delivery/`):**

| dosya | tek sorumluluk |
|---|---|
| `collect.py` | evren + ödenmiş depo + kimlik → `Row` listesi (`item_id` sırasında); karar vermez |
| `gate.py` | SEVK KAPISI — bu içerik öğrenciye gidebilir mi |
| `materialize.py` | topla → **kapı** → `.staging/`'e yaz → `os.replace` ile yerine taşı |
| `snapshot.py` | `_dist_meta.json` — satır sayıları + her dosyanın sha256'sı |
| `verify/checks.py` | üretilmiş sevkiyata **dışarıdan** bakan uçtan uca kontroller |
| `schema.py` | `core.db` / `<l2>.db` / `i18n_<l1>.db` DDL'i + dosya adları |
| `commands/` · `app.py` | bayrak → fonksiyon (iş yapmaz) + manifest |

**Kapının dayandığı ayrım** `dictionary/sources.py`'de yazılıdır: **olgu**
(frekans, CEFR, IPA) her zaman sevk edilebilir; **ifade** (tanım, örnek
cümle, açıklama) yalnızca `shippable=True` bir kaynaktan ya da bizim
ürettiğimizden (`llm`/`human`) gelebilir. Bu yüzden `dictionary_seed`
kaynaklı IPA kapıdan geçer, aynı kaynaktan gelecek bir **metin** geçmez.

**Kapı kuralları:** sevk edilemez kaynaktan metin · onaylanmamış satır ·
boş gloss/headword/örnek · L1 karşılığı eksik · `item_id`/`sense_id`
tekrarı · hiç satır yok. Hepsi tek seferde toplanır, tek raporda basılır.

**§5.4'ten sapma yok, iki not:** dosya düzeni korundu; `<l2>.db` adı artık
sabit `en.db` değil L2'den türer (dil eklemek dosya ekler). Sevkiyat
dosyaları **zaman damgası taşımaz** — aynı girdi aynı baytları üretsin diye
üretim zamanı yalnızca `_dist_meta.json`'a yazılır.

**Kabul kriterleri (`tests/test_delivery.py`, 12 test) — geçti:**

* kapı ihlalinde `materialize` **hiç dosya yazmıyor** ve `data/dist/<tag>/`
  dizini bile oluşmuyor;
* dist'te **duran** bir sevkiyat varken ikinci koşu ihlal ederse eski
  dosyalar **bayt bayt aynı** kalıyor, `.staging/` geride kalmıyor;
* aynı girdi iki koşuda aynı sha256'yı üretiyor (determinizm);
* `verify` elle değiştirilmiş bir dist dosyasını sha256'dan yakalıyor;
* yalnızca `status='approved'` satırlar sevk ediliyor.

**Gerçek pilot sevkiyatı (`v7/en`, 291 öğe, sıfır LLM çağrısı):**

| dosya | bayt | sha256 |
|---|---|---|
| `core.db` | 49.152 | `d4168fd14ca0ea6f…` |
| `en.db` | 73.728 | `1ffbf475f2cd5b67…` |
| `i18n_tr.db` | 24.576 | `0c4ef4ccc0e92720…` |

Atlanan: kartı olmayan 4.700 (evren 5.000, pilot 300 kelimelik), onaylanmamış 9.
IPA kapsaması 290/291, CEFR 244/291. `polyvo delivery verify` **16/16 yeşil**.

**Komut adı:** §7 bu komutu `polyvo verify pipeline` diye anıyordu; app/komut
düzenine (`polyvo <app> <komut>`) uyum için adı `polyvo delivery verify`,
işi aynı.


### 9.6 Adım 7 ölçümü (2026-09-06) — insan yolu + panel

**Dosya sorumlulukları (`src/polyvo/review/`, katman 4):**

| dosya | tek sorumluluk |
|---|---|
| `record.py` | düzeltmenin BİÇİMİ — hangi alan okunur, hangisi okunmaz |
| `export.py` | ödenmiş depodan düzeltilebilir satırları çıkarır (JSONL) |
| `apply.py` | tek yazma yeri: doğrula → yazma kapısı → **tek transaction** |
| `backup.py` | `data/human/corrections.jsonl` — insan emeğinin taşınabilir yedeği |
| `commands/` · `app.py` | bayrak → fonksiyon (iş yapmaz) + manifest |

**`source="human"` hardcoded, tier asla yedekten okunmaz (§7'nin şartı):**
`tier`/`source`/`status`/`model` alanları dosyada bulunabilir (export bağlam
olarak yazar) ama **okunmaz**; `apply.py` onları sabit yazar. Aksi halde
düz bir metin dosyası kendini "insan kararı" ilan edip yazma kapısını
kandırırdı. Kapının kendisi yeniden yazılmadı: `apply.py` de
`core/jobs/store/policy.py`'yi çağırır — ikinci bir kural kümesi yok.

**Üç biçim kuralı, üçü de test edilmiş:**
*bulunmayan alan dokunulmaz* (yalnız gloss'u düzeltmek örnekleri silmez) ·
*`null` yalnızca boşaltılabilir alanda geçerli* (glosssuz kart sevk edilemez) ·
*bilinmeyen alan satırı düşürür* (`gloss_tr` yazım hatası "hiçbir şey olmadı"
ile sonuçlanmaz). Export, içeriği olmayan alanı hiç yazmaz — çıkan dosya
düzeltilmeden geri okunabilmelidir.

**Kimlik ÜRETİLMEZ:** depoda karşılığı olmayan `stable_key` düzeltilemez;
tüm koşu durur (`--skip-unknown` ile atlanır). `curriculum` dışında ikinci
bir kimlik üreteci yoktur.

**Panel host'u (`src/polyvo/panel/`, katman 5) — sayfa listesi YOK:**

| dosya | tek sorumluluk |
|---|---|
| `pages.py` | app keşfinden sayfaları toplar; önek çakışması **hata**dır |
| `dispatch.py` | yol → sayfa eşlemesi (SAF fonksiyon, soket yok) |
| `shell.py` | kabuk + gezinme çubuğu — nav sayfalardan türer |
| `http.py` · `server.py` | `dispatch`i `http.server`a bağlar; varsayılan `127.0.0.1` |

Sayfa sözleşmesi **ördek tiplemesidir**: modül panel katmanını import etmez
(demir kural), yalnızca `router(path, query) -> (status, tip, gövde)` döner.
"text/html" dönen gövde bir parçadır, kabuğu host giydirir; JSON/CSV olduğu
gibi geçer. `modules/lexicon_card/panel/` bu koşuda router'ını getirdi
(`queries.py` depoyu okur, `views.py` HTML üretir) — host'ta tek satır
değişmedi.

**Panel SALT OKUNURDUR.** `do_POST` 405 döner; düzeltmenin tek yolu
`review` app'idir. İkinci bir yazma yolu açmamak bilinçli karardır.
Ek dış bağımlılık yok: `http.server` stdlib.

**Kabul kriterleri (`tests/test_review.py` 17 + `tests/test_panel.py` 18) — geçti:**

* dosyadaki `tier`/`source` okunmuyor, satır tier 0 / `human` yazılıyor;
* sorunlu tek satır varsa **hiçbir satır yazılmıyor** (depo aynen duruyor,
  yedek dosyası bile oluşmuyor);
* depo silinip yeniden kurulduğunda yedekten **geri yükleniyor**, `l1`
  yedekten adres olarak okunuyor; `restore` yedeği büyütmüyor;
* `APP.panel`i olmayan app panelde görünmüyor, aynı öneki iki app isteyemiyor;
* router'ı olmayan sayfa 501, **patlayan router 500** — ikisi de paneli
  düşürmüyor, kök sayfa çalışmaya devam ediyor;
* depodan gelen metin HTML olarak yorumlanmıyor (XSS kapısı);
* statik dosyada dizin dışına çıkış (`../`) engelleniyor.

**Gerçek koşu (sıfır LLM çağrısı):** `polyvo review export --tag v7 --l2 en
--l1 tr --status rejected` pilotun **9 reddedilen satırını** sebepleriyle
çıkardı (`data/workspace/v7/en/review-export.jsonl`). Ardından **gerçek
depo kopyası** üzerinde uçtan uca: `en:that:adv` düzeltildi → tier 0/`human`,
L1 + 2 örnek yazıldı; depo silinip sıfırlandı → `restore` yedekten aynı
satırı geri getirdi. Panel gerçek soketle ayağa kalkıp `/lexicon-card`
sayfasında **291 approved · 9 rejected** özetini ve kart ayrıntısını
(`repertoire` → gloss + `/ˈɹɛpɝtˌwɑɹ/` + "yapabilme yeteneği") servis etti.

**v1 tamamlandı.** Ertelenenler (v2): `modules/cloze`, `modules/paragraph`,
`modules/reading`, `curriculum/sets`, embedding katmanı, panelden düzeltme.
