# İş 2 — çok dilli L1 (İspanyolca · Brezilya Portekizcesi · Almanca)

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul: İş 1 (`variant` ekseni) bitmiş olmalı.** Bu iş onun ilk gerçek
tüketicisidir.

Önce oku: `DURUM.md` → `docs/MIGRATION-PLAN.md` (§2 ucuz/pahalı ayrımı, §5.2
şema, §9.4 pilot ölçümü) → `docs/V2-BRIEF.md` → `docs/V2-IS-1-VARIANT.md` → kod.

---

## Görev

Depoda **291 ödenmiş EN kart + TR karşılığı** var. İstenen: aynı kartların
üstüne ikinci, üçüncü, dördüncü ana dil eklemek — **kartı yeniden ödemeden**.

Diller ve sıra: **1) İspanyolca (`es`) · 2) Brezilya Portekizcesi (`pt-BR`) ·
3) Almanca (`de`).** Her dil **ayrı koşu**; tek koşuda birden çok dil istenmez.

---

## Bugün ne oluyor (doğrulanmış)

`polyvo lexicon-card cards --l1 es` bugün **sıfır İspanyolca karşılık üretir.**
Sebep: `modules/lexicon_card/store.py::load_existing` yalnızca `sense_cards`a
bakıyor, `core/jobs/plan/verdict.py::decide` `approved` gördüğü satıra
`skip_done` diyor. Kartın TR karşılığı var diye o anlam "tamam" sayılıyor.

Depo şeması engel değil: `sense_gloss_l1`'in birincil anahtarı zaten
`(sense_id, l1)` — çoklu dile hazır. Tıkanan yer **plan aşaması**.

---

## İstenen davranış

1. **L1 karşılığı kartın parçası değil, kendi satır ailesidir.** Anahtarı İş
   1'in varyant ekseni taşır (varyant = L1 kodu). Bir dilin eksik olması kartı
   "eksik" yapmaz; kart bir daha üretilmez ve **bir daha ödenmez**.

2. **Yalnızca eksik dili üreten bir koşu olacak.** Doğal biçimi aynı app içinde
   ikinci bir `kind`'dır (`family="lexicon"`, kart işinin yanında); komut adını
   sen seçersin. Bu koşu:
   - girdi olarak **ödenmiş EN kartı** (gloss_en + örnek cümleler) alır ve
     bunu prompt'a **bağlam** olarak koyar. Sebep: model kelimeyi değil
     **o anlamı** çevirmeli — `bank` için hangi anlam olduğunu yalnızca
     `gloss_en` söyler. Bağlamsız çeviri bu işin en büyük kalite riskidir.
   - `status='approved'` kartı **olmayan** anlamı atlar (çevrilecek anlam yok).
   - o dilin karşılığı zaten varsa **çağrı yapmaz** (yazma kapısı + redo matrisi
     zaten bunu söylüyor; ikinci bir kontrol yazma).

3. **Mevcut `cards` komutunun davranışı korunur.** Yeni bir kelime için kart +
   o koşunun L1'i **tek çağrıda** üretilmeye devam eder. Yeni iş yalnızca
   **eksik dilleri** doldurur. İki yol aynı tabloya yazar; ikisi de aynı yazma
   kapısından geçer, ikinci bir kapı yazılmaz.

4. **Prompt kart prompt'undan ayrı ve küçük olacak.** Mevcut `prompt.py` EN kart
   + register + kullanım notu + iki örnek + L1 karşılığı istiyor; sadece bir
   karşılık için o prompt'u göndermek hem pahalı hem kaliteyi düşürür. Yeni
   prompt tek işe odaklı olmalı. Prompt sürümü (`prompt_version`) baştan doğru
   verilmeli — deneme günlüğü hangi metinden üretildiğini böyle söylüyor.

5. **Her dil için `core/lang/<kod>.py` kural modülü yazılacak.** Bu kayıt zaten
   var ve eklentiye açık (`core/lang/__init__.py::get_rules`, kuralsız dil no-op
   varsayılana düşer). `tr.py` örnek alınacak. En az şunlar:
   - `LANGUAGE_NAME`
   - `PROMPT_RULES` — modele sözlük biçimi kuralları (fiil mastarı vb.)
   - `REVIEW_RULES` — insan denetimi için aynı kuralın Türkçe anlatımı
   - `check_form(pos, text)` — **ölçülebilir** biçim kapısı. Diller için doğal
     karşılıklar: `es`/`pt-BR` fiil mastarı `-ar/-er/-ir`; `de` fiil mastarı
     `-en/-n` ve **isimler büyük harfle başlar** (kolay ve güvenilir bir kontrol).
     Kesin kuralı sen belirle, ama her dil için **en az bir gerçek kontrol**
     olacak ve testi yazılacak.
   - Emin olmadığın bir kuralı kapı yapma: `tr.py`'nin dediği gibi, garanti
     edilemeyen kontrol reddetmez, uyarır.

6. **`pt-BR` tuzağı — sessiz düşüşe izin verilmeyecek.** `get_rules` kural
   modülünü `importlib.import_module(f"polyvo.core.lang.{lang}")` ile arıyor.
   `pt-BR` geçerli bir Python modül adı değil: `ModuleNotFoundError` yenir ve
   dil **sessizce kuralsız** çalışır — yani hiçbir QA kontrolü olmadan, hata
   vermeden. Beklenen: veri ve konfigde standart kod (`pt-BR`) kalır, `get_rules`
   modül adını **normalize eder** (tire → alt çizgi, küçük harf). Ayrıca
   `core/paths.py::LANGUAGE_NAMES`'e yeni kodlar eklenir, yoksa raporlarda dil
   adı yerine kod görünür.

7. **`polyvo.toml`** `project.l1` zaten bir liste; yeni diller oraya eklenir.
   `config.default_l1()` listenin ilkini döndürüyor — bu davranış değişmemeli.

8. **İnsan düzeltme yolu yeni dilde de çalışmalı.** `review export --l1 es` /
   `review import --l1 es` yeni dilin karşılığını çıkarıp geri yazabilmeli
   (kod değişikliği gerekmiyor olabilir — **testle göster**). Panelde kart
   ayrıntısı zaten tüm L1 satırlarını listeliyor; yeni dil orada görünmeli.

---

## Kapsam dışı — dokunma

- **`delivery/`e dokunma.** Çok dilli sevkiyat ayrı bir iştir (V2-BRIEF İş 7).
  **Uyarı:** bu iş bitene kadar `delivery materialize --l1 es` koşulmamalı —
  `_dist_meta.json` tek L1 tanıdığı için ikinci dil koşusu ilk dilin manifest
  kaydını ezer ve `verify --l1 tr` artık geçmez.
- `sense_gloss_l1` şemasını değiştirme; `(sense_id, l1)` zaten doğru anahtar.
- Kartı (gloss_en, register, örnekler) yeniden üretme.
- Tek promptta birden çok dil isteme.
- `core/jobs/` motorunu değiştirme.

---

## Pilot — kademelilik (kullanıcının açık isteği)

Kullanıcı 50 kelimelik bir test koşacak. Sen bunu mümkün kılacaksın, kendin
büyük koşu başlatmayacaksın.

- Önce `--limit 50 --dry-run`: **50 işlenecek / 0 kart yeniden üretimi**
  raporlanmalı. Para harcanmadan bu doğrulanır.
- Gerçek koşu tek modele **sabit** (bugünkü pilot modeli;
  `model_quality.json` global kalıyor, kind bazlı sıralama yapılmayacak).
  İki modelle yarım dolmuş bir depo reddetme oranını ölçülemez hale getirir.
- Koşudan sonra **QA reddetme oranı** MIGRATION-PLAN §9.4 biçiminde raporlanır:
  işlenen / onaylanan / reddedilen + **sebep dökümü**
  (`attempts.reject_reasons` bunu zaten veriyor).
- Oran kabul edilebilir değilse **prompt/QA düzeltilir, koşu büyütülmez.**
- Sonraki dile (`pt-BR`) ancak öncekinin oranı görüldükten sonra geçilir.

---

## Kabul ölçütleri

- 291 kartlı depoda `--l1 es --dry-run` → **291 işlenecek, 0 kart yeniden
  üretimi, 0 EN kart çağrısı.**
- `es` koşusundan sonra `--l1 tr --dry-run` → **0 ödenecek çağrı** (Türkçeye
  zarar verilmedi).
- İkinci `--l1 es` koşusu → **0 ödenecek çağrı** (artımlılık kanıtı; her yeni
  `kind` için yeniden kanıtlanır).
- `--dry-run` tek kuruş harcamıyor ve **tek satır yazmıyor**.
- Kartı olmayan / onaylı olmayan anlam çeviri koşusuna **girmiyor**.
- Reddedilen satır içerik yazmıyor; `status='rejected'` + `reject_reason` ile
  duruyor (`--redo bad` onu böyle buluyor).
- İnsan satırı (tier 0) varken o dil için çağrı **istenmiyor**.
- `pt-BR` kodu kural modülünü **buluyor** (sessiz düşüş yok) ve bunun testi var.
- Her yeni dil için `check_form` en az bir gerçek hatayı yakalıyor + testi var.
- `review export/import --l1 es` çalışıyor, yazılan satır `tier=0`/`human`.
- Mevcut 178 test + İş 1'in testleri yeşil; `test_layering` yeşil.
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı (tahmin değil).
