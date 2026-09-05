# Polyvo word-databases — yeniden yapılandırma planı

Kaynak repo: `C:\Users\ahmet\Desktop\Projects\python\word-database`
Hedef repo:  `C:\Dev\MyProjects\Polyvo\word-databases`

Bu dosya **donmuş kapsam** belgesidir. Her adım kendi başına bitirilir, kendi kabul
testiyle doğrulanır ve ancak ondan sonra bir sonrakine geçilir. Bir adımı bölmek
serbest, sırayı bozmak değil — sıra bağımlılık sırasıdır.

---

## 0. Neden taşıyoruz

Eski yapı yanlış klasörlendiği için değil, **iki farklı eksen tek çuvala
doldurulduğu** için karmaşık:

| eksen | doğası | anahtar | yeniden üretilebilir mi |
|---|---|---|---|
| veri hattı aşaması (build/enrich/embed) | tam-kopya snapshot, tag'li | `databases/<tag>/NN_x/` | evet — pahalı ama deterministik |
| omurga (universe/items/sets/apply) | ucuz, deterministik izdüşüm | `stable_key` → `workspace/` | evet — bedava |
| üretim işi (lexicon/cloze/paragraph/translate) | kimlik-anahtarlı, tag'siz | `(family, kind, stable_key)` | **hayır — para** |

`src/stages/content/` bugün üçünü birden barındırıyor; ortak makine (`runner.py`,
685 satır) da onun *içinde*, öyle ki "ayrık" olduğu söylenen `src/modules/kernel/`
bile `src.stages.content.runner`'ı import ediyor. Dosyaları taşımak bu bağı aynen
getirir. **Önce eksenler ayrılır, sonra taşınır.**

---

## 1. Mimari — 4 katman, tek yönlü bağımlılık

```
katman 3  delivery    materialize · snapshot · verify · panel host
              ^ sadece okur
katman 2b modules     LLM işleri; her biri bağımsız "app"
              ^
katman 2a curriculum  evren · kimlik · item · set · gruplama — SIFIR LLM
              ^
katman 1  dictionary  build · enrich · embedding — snapshot'lı veri hattı
              ^
katman 0  core        llm · sqlite · paths · config · dil · metin QA · jobs motoru
```

**DEMİR KURAL: alt katman üst katmanı import edemez.** Bu kural bir yorum değil,
bir testtir — Adım 1'de `tests/test_layering.py` olarak yazılır ve her adımda
çalıştırılır. Eski repodaki tek ihlal (`kernel/engine.py` -> `content/runner.py`)
buraya taşınmayacak.

**İKİNCİ KURAL: bir "app" = bir aile, içinde birden çok `kind`.**
`cloze` ile `cloze-translate` ayrı *komut* ve ayrı *cache anahtarı*, ama ayrı
klasör değil — ortak `stable_key`, ortak store satır ailesi, ortak QA. Ayrı
klasör yapılırsa o ortaklık üçüncü kez kopyalanır (eski `translation_sync.py`'nin
1113 satırının sebebi tam olarak bu).

---

## 2. Hedef klasör ağacı

```
word-databases/
├── pyproject.toml            # `polyvo` konsol komutu (manage.py subprocess dispatch'i YOK)
├── polyvo.toml               # TEK konfig: aktif tag, diller, model rank, yollar
├── data/
│   ├── raw/                     indirilen kaynak            (eski: raw_data/)
│   ├── cache/                   GLOBAL, tag'siz, SİLİNEBİLİR AMA PAHALI
│   ├── stores/                  GLOBAL, tag'siz, KUTSAL — kimlik + ödenmiş kararlar
│   ├── human/                   GLOBAL, gitignore, tier=0   (eski: human-data/)
│   ├── builds/<tag>/01_build … 04_content/
│   ├── workspace/<tag>/<l2>/    ucuz izdüşüm — serbestçe silinir
│   └── dist/<tag>/<l2>/         F7 sevkiyat                 (eski: content/)
├── src/polyvo/
│   ├── core/
│   │   ├── config.py  paths.py  sqlite.py
│   │   ├── llm/        base · registry · cache · quality · cli · providers/
│   │   ├── lang/       tr.py …
│   │   ├── text/       qa · mojibake · sentence
│   │   ├── cli/        app keşfi · argparse iskeleti · ortak pencere flag'leri
│   │   └── jobs/       base · plan · engine · store · identity · attempts
│   ├── dictionary/     stages.py · build/ · enrich/ · embedding/
│   ├── curriculum/     universe.py · items.py · sets.py · grouping.py
│   ├── modules/
│   │   ├── lexicon_card/   app · prompt · taxonomy · qa · store · reparse · panel/ · tests/
│   │   ├── cloze/          app · text · translate · prompts/ · panel/ · tests/
│   │   ├── paragraph/      app · text · questions · translate · panel/ · tests/
│   │   └── reading/        app · text · panel/
│   ├── delivery/       materialize.py · snapshot.py · verify/
│   ├── review/         insan düzeltme yolu (CLI export/import + human yedeği)
│   └── panel/          HOST: http · static shell · APP KEŞFİ (sabit sayfa listesi YOK)
└── tests/
```

### Bir app'in anatomisi

```python
# src/polyvo/modules/cloze/app.py
APP = App(
    name="cloze",
    family="cloze",
    jobs=[ClozeText(), ClozeTranslate()],        # her biri bir `kind`
    commands=["run", "translate", "stats"],      # polyvo cloze run --start 0 --end 600
    panel=PanelPage(prefix="/cloze", title="Cloze Denetimi", router=router),
    depends=["curriculum.items"],                # AÇIK bağımlılık, gizli import değil
)
```

Yeni bir iş eklemek = **bir klasör**. Hiçbir mevcut dosya düzenlenmez.
Panel merkezi liste tutmaz; app manifest'lerini gezip prefix->router bağlar
(bugün `reading` panelinin olmamasının sebebi tam olarak o merkezi liste).

---

## 3. Veri politikası — hiçbir şey taşınmıyor

Karar (2026-09-05): **kod da veri de sıfırdan.** `raw/`, `cache/`, `stores/`,
`human/`, `builds/`, `workspace/`, `dist/` — hiçbiri eski repodan gelmiyor.

Gerekçe, ve bu gerekçe planın geri kalanını da değiştiriyor: mevcut verinin
kalitesi düşük, çünkü kaynaklar **dil bilimi için** üretilmiş veriler, öğretim
için değil. Ham kaynak seçimi (hangi liste, hangi filtre) ve `build`/`enrich`
adımları zaten yeniden ele alınacak. Dolayısıyla:

- Eski `cache/llm_cache.sqlite`'i taşımanın anlamı yok: prompt'lar da,
  besledikleri kelime evreni de değişecek. Anahtar `sha256(label + prompt)`
  olduğu için değişen prompt zaten yeni anahtar demek.
- Eski `stores/`'u taşımanın anlamı yok: kimlik `(l2, headword, sense_ordinal)`
  üzerinden kuruluyor ve kelime evreni baştan seçilecek.
- **Bunun bilinen bedeli:** mevcut insan düzeltmeleri (tier=0) ve `item_id` /
  `set_id` sürekliliği sıfırlanır. Flutter'a çıkmış bir sevkiyat varsa yeni
  kimlik uzayı onunla uyuşmaz. Bu kabul edilmiş bir maliyettir, sürpriz değil.

**Sonuç:** yeni repoda hiçbir "eski veriyi tanı/göç ettir" kod yolu yazılmaz.
Legacy yol tespiti, eski dosya adı yedekleri, migration script'leri — hiçbiri
taşınmaz. Sıfırdan başlamanın tek gerçek kazancı budur; geriye uyumluluk kodu
yazarsak o kazancı ilk gün harcamış oluruz.

## 4. Ne kopyalanır, ne yeniden yazılır

**KOPYALA (CTRL+C/V, mantığı yeniden türetme):** bunlar ölçümle kazanılmış veya
harici formata bağlı; yeniden yazmak saf risk.

| dosya | satır | neden |
|---|---|---|
| `src/modules/lexicon/taxonomy.py` | 190 | 137 sabit düğüm + ölçülmüş normalize kuralları (unresolved 499 -> 5) |
| `src/modules/lexicon/prompt.py` | 143 | kart prompt'u — değişirse cache anahtarı kayar = para |
| `src/core/lang_rules/tr.py` | 193 | Türkçe morfoloji + PROMPT_RULES |
| `src/core/text_qa.py` | 306 | WordNet morphy + span bulma; false-positive'leri ölçümle ayıklanmış |
| `src/core/mojibake.py` | 52 | `chr()` ile üretilen sentinel — literal yazarsan hastalığı geri getirirsin |
| `src/core/llm/providers/*` | ~500 | 403/429 tuzakları, Retry-After, quota-vs-RPM ayrımı |
| `src/core/llm/quality.py` + `model_quality.json` | 250 | rank tablosu bir karar, kod değil |
| `src/stages/build/ingestors/*` | ~900 | harici dosya formatlarına bağlı (Kaikki/NGSL/SUBTLEX şeması) |
| `src/stages/build/word_cleaner.py` | 303 | öğrenici-kelime filtresi, elle ayarlanmış |
| `src/stages/build/ranking.py`, `cefr.py` | 400 | sıralama + CEFR eşleme kararları |
| `src/stages/enrich/providers/*` | ~1100 | her biri bir dış kaynağın tuhaflığı |
| `src/core/db/schema.py`, `content_schema.py` | 2000 | DDL — yeniden yazmak = sessiz şema kayması |
| `src/stages/content/stoplist.py`, `wordlists.py` | 294 | listeler |
| `src/core/cefr_profiles.py` | 245 | `target_words` <-> `qa_word_min/max` çiftleri ölçümle hizalanmış (%38 -> %91) |
| `sets_compiler.py` içindeki `pick_companions` / `fallback_companions` / `violates_hard_constraints` | ~400 | yapışkan gruplama %0,7 -> %100'ü bu üç fonksiyona dokunulmadan kazandı |
| `src/modules/reading/grouping.py::_spread_senses` | ~40 | ölçülmüş: çakışma 10/12 -> 6 |
| `tools/test_*.py` (8 dosya) | ~4000 | sözleşme testleri; yeni yollara göre import'ları düzelt, mantığa dokunma |

**YENİDEN YAZ:** `runner.py`, `kernel/*`, `author.py`, `apply.py`,
`translation_sync.py`, `materialize.py`, `review.py`, `manage.py`,
`panel/server.py` + `panel/features/*/service.py`, `stores.py`.
Bunlar taşınacak mimarinin *kendisi* — kopyalarsan eski şekli kopyalamış olursun.

---

## 5. Adımlar

Her adımın sonunda: kabul testi yeşil + eski repo hâlâ çalışır durumda
(9. adıma kadar eski repoya commit yok).

### Adım 1 — `core/` iskeleti

**Üret:** `pyproject.toml` (`polyvo` entry point), `polyvo.toml`, `data/` ağacı,
`core/config.py`, `core/paths.py` (tag çözümleme zinciri aynen korunur:
argüman -> env -> `.active_tag` -> tek aday -> `SystemExit`), `core/sqlite.py`
(pragma'lar + `busy_timeout=30000` + backup-API kopyası + korumalı `row_counts`),
`core/cli/` argparse iskeleti + app keşfi, `tests/test_layering.py`.

**Kopyala:** `core/llm/*` (base, registry, cache, cli, quality, providers),
`core/lang/tr.py`, `core/text/*` (text_qa, mojibake), `model_quality.json`.

**Düzelt:** `manage.py`'nin subprocess dispatch'i gelmez; komutlar app'lerden
toplanan subparser'lar olur. Beş ayrı konfig kaynağı (`.active_tag`,
`model_quality.json`, `source_config.json`, `.env`, sabit yollar) tek
`polyvo.toml` + `.env`'e iner.

**Kabul:** `polyvo --help` çalışır; `test_layering` yeşil; `hash_prompt` altın
hash'i eski repodakiyle **birebir aynı** (cache anahtarı kaymadı kanıtı).

### Adım 2 — `core/jobs/` genel üretim motoru

Eski `stages/content/runner.py` + `modules/kernel/*` tek motorda birleşir.

**Üret:** `base.py` (Job sözleşmesi: `load_units` / `build_prompt` / `run_qa` /
`write`), `plan.py` (PlanReport + cache yoklaması + `confirm_plan`),
`engine.py` (plan -> onay -> döngü -> yaz -> mutabakat, kesinti-güvenli commit),
`store.py` (artifact deposu + **policy'li yazma kapısı**), `identity.py`
(monotonik tahsis, `AUTOINCREMENT` YOK), `attempts.py` (INSERT-ONLY).

**Düzelt — bu adımın asıl işi:** yazma kapısı ve plan mantığı *policy* olur:

```
write_policy: RankPolicy (tier+status+rank)  |  SourceHashPolicy (+ KURAL 4)
plan_policy:  ArtifactPlan (missing/approved/rejected)  |  StorePlan (5 verdict)
```

Eski repoda lexicon "kernel'e uymuyor" diye ayrı yol açmıştı; sonuç iki plan
mantığı, iki yazma kapısı, iki ilerleme yolu oldu. Motor genişletilir, ikinci
yol açılmaz.

**Kopyala:** `plan_item` / `_should_write` / `plan_generation_row` karar
tablolarının *mantığı* (yeniden konumlandırılmış hâliyle), `runner.py`'nin
`--start/--end` kelime-penceresi yardımcıları.

**Kabul:** `tests/test_redo_matrix.py` (1.008 + 9.960 vaka) yeni motora karşı
yeşil; `PlanReport.render` çıktı biçimi korunmuş.

### Adım 3 — `dictionary/`

**Üret:** `stages.py` (aşama kayıt defteri: `stage_dir` / `prepare_stage` /
`write_stage_meta` / `pipeline_status`), `build/command.py`, `enrich/command.py`,
`embedding/{sync,apply}.py` kabukları.

**Kopyala:** tüm `ingestors/`, `extractors/`, `ranking.py`, `cefr.py`,
`word_cleaner.py`, `downloader.py`, `core_concepts.py`, `enrich/providers/*`,
`db/schema.py`, `db/helpers.py`, `embedding/search.py`.

**Not:** build ve enrich **aynı pakette ama ayrı aşama** kalır. Birleştirirsen
"enrich'i tek başına yeniden çalıştır" imkânsızlaşır (enrich `01_build`'i tam
kopyalayıp üstüne yazıyor).

**Kabul:** küçük bir tag (`--limit 500`) uçtan uca build+enrich+embed-apply;
`_stage_meta.json` satır sayıları eski repodaki aynı limitli koşuyla uyuşur.

### Adım 4 — `curriculum/`

**Üret:** `universe.py` (+ universe gate), `items.py` (eski `apply.py`: kimlik
tahsisi + `workspace` izdüşümü; anlam düzeltmesi **UPDATE**'tir, delete+insert
değil), `sets.py`, `grouping.py`.

**Kopyala:** `sets_compiler.py`'nin gruplama çekirdeği (yukarıdaki üç fonksiyon +
`load_locked_groups` yapışkanlık mantığı), `grouping.py::_spread_senses`,
`stoplist.py`, `wordlists.py`.

**Kabul:** `test_item_identity.py`, `test_set_identity.py`,
`test_sets_sticky_grouping.py`, `test_reading_groups.py` — dördü de yeşil.
`workspace/` tamamen silinip yeniden üretildiğinde `item_id`, `set_id`, A–G slot
sırası ve modül türleri **birebir aynı** çıkmalı.

### Adım 5 — `modules/lexicon_card/` (ilk app, sözleşmeyi o belirler)

**Üret:** `app.py` manifest, `store.py` (entry + gloss iki yapıya yazma tek
transaction), `qa.py`, `panel/` (gloss + taxonomy düzenleme, revert).

**Kopyala:** `prompt.py` (BİREBİR — değişirse cache anahtarı kayar),
`taxonomy.py`, `reparse.py`'nin üç sıfır-çağrı onarım modu.

**Düzelt:** tohum kuralı yeni hâliyle gelir — insan tohumu (tier 0) mutlak
kazanır, sözlük tohumu (tier 1/2) yalnızca modelin gloss'u yoksa yazılır.
`tests/test_lexicon_seeding.py` bunu kilitler.

**Kabul:** `polyvo lexicon sync --dry-run --start 0 --end 50` -> cache
kopyalandıysa **paid_calls = 0**. Sıfırdan başlıyorsan plan sayısı eski repodaki
aynı pencereyle aynı olmalı.

### Adım 6 — `modules/cloze/` ve `modules/paragraph/`

Eski `cloze_gen.py` (514) + `paragraph_gen.py` (736) + `translation_sync.py`
(1113) -> beş dosya: `cloze/{text,translate}.py`,
`paragraph/{text,questions,translate}.py`. Ortak QA `core/text/`'ten gelir.

**Kopyala:** prompt metinleri, `cefr_profiles.py`, cloze span bulma
(`find_spans_loose`) kullanımı.

**Düzelt:** çeviri çağrı birimi paragraf, saklama birimi cümle
(`(l1, kind, sha256(L2 metin))`) — bu korunur. Paragraf soruları ayrı `kind`
olur; metin ve soru artık aynı çağrıda üretilmez.

**Kabul:** `test_redo_e2e.py` beş komut × üç mod; her modun alt-sayıları istek
sayısına **tam** toplanır.

### Adım 7 — `modules/reading/`

Zaten motorun şeklinde; en ucuz taşıma. `grouping.py` Adım 4'te taşındığı için
burada sadece `text.py` + `profiles.py` + `app.py` + panel sayfası kalır.

**Kabul:** `paragraph-group --stats` eski repodaki grup sayılarını verir.

### Adım 8 — `delivery/` + `review/`

**Üret:** `materialize.py` (eski 1256 satır; kapı **önce** çalışır, ihlalde
**sıfır dosya** yazıp exit 1 — `--allow-degraded` `_dist_meta.json`'a işaretler),
`snapshot.py`, `verify/` (build gate, dist ön-uçuş, diff-universe, pipeline
sağlık kontrolü), `review/` (export/import + `data/human/` yedeği; import
`source="human"` hardcoded, tier asla yedekten okunmaz).

**Kabul:** `polyvo verify pipeline` dokuz bölüm yeşil; bozuk kaynakla
materialize exit 1 ve **hiç dosya yazmamış**.

### Adım 9 — `panel/`

Host: http + static shell + **app keşfi**. Sayfa/router listesi yoktur;
`APP.panel` olan her modül kendi sayfasını getirir. Veri erişimi app'in kendi
kodundan gelir — panel ikinci bir sorgu katmanı yazmaz (eski
`panel/features/*/service.py`'nin `translation_sync.source_hash`'i import etmek
zorunda kalması bu hatanın itirafıydı).

**Kabul:** `reading` sayfası panel kodunda tek satır düzenleme olmadan görünür.

---

## 6. Yeniden yazarken geri getirilmeyecek bilinen kusurlar

Eski repoda ölçülerek bulunmuş, tekrar etmemesi gereken şekiller:

1. **Uyarı basıp exit 0 dönen kapı, kapı değildir.** Üç ayrı alt sistemde üç kez
   oldu (embed-apply, image ingest, materialize). İhlalde sıfır çıktı + exit 1.
2. **Kimlik üreteci "serbestçe silinebilir" klasörde yaşayamaz.** Tüm id tahsisi
   `data/stores/`'ta, `AUTOINCREMENT` kullanmadan (UPSERT'in UPDATE dalında bile
   sayaç ilerliyor).
3. **Alan değişimi kimlik değişimi değildir.** Anlam düzeltmesi `UPDATE`.
4. **"Bunu daha önce gördüm mü" kontrolü, karar verilen satırı dışlamalı.**
5. **`cur.lastrowid` UPSERT'ten sonra kullanılmaz.** Doğal anahtardan yeniden oku.
6. **Aynı dosyaya yazan iki komut = aynı kilit.** `busy_timeout` tek yerde,
   sıfır değil.
7. **Garanti edilemeyen QA kontrolü reddetmez, uyarır.** (Cloze'un span'i yapısal
   olduğu için bilinçli istisna.)
8. **Kodun test etmediği bir sonucu iddia eden tanı mesajı yazılmaz.** (429 ->
   "bu günlük kota DEĞİL" hardcoded'ı 13 dakikalık boş retry'a mal oldu.)
9. **İki komut birleştirilirken hayatta kalan prompt, ikisinin birleşimi
   değildir.** Alan alan diff'le (kayıp L1 biçim kuralları böyle kaçtı: %5,1
   emir kipi gloss).
10. **`MAX(id)` satır sayısının vekili değildir.**

---

## 7. İlerleme

- [x] Adım 1 — core iskeleti  (2026-09-05, 19 test yeşil)
- [ ] Adım 2 — jobs motoru
- [ ] Adım 3 — dictionary
- [ ] Adım 4 — curriculum
- [ ] Adım 5 — lexicon_card
- [ ] Adım 6 — cloze + paragraph
- [ ] Adım 7 — reading
- [ ] Adım 8 — delivery + review
- [ ] Adım 9 — panel
