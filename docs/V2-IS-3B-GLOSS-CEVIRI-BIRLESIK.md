# İş 3b — `gloss` ile `translate`'i tek çağrıda birleştir

Bu dosya bir **görev tanımıdır**. Okuma sırası: `DURUM.md` →
`docs/MIGRATION-PLAN.md` §9.8 / §9.11 → bu dosya → kod
(`modules/lexicon_card/gloss/`, `modules/lexicon_card/translate/`).
Belirsizlik varsa kullanıcıya sor; varsayım yapıp ilerleme.

---

## 1. Neden

Bugün bir anlamın ana dil verisi **iki ayrı çağrıyla** üretiliyor:

| komut | ne üretir | tablo |
|---|---|---|
| `lexicon-card gloss --l1 X` | kelimenin karşılığı (`bank` → `banka`) + isteğe bağlı kısa not | `sense_gloss_l1`, `sense_gloss_l1_note`, `sense_gloss_l1_state` |
| `lexicon-card translate --l1 X` | tanım + kullanım notu + 2 örnek cümlenin çevirisi | `sense_translation`, `sense_translation_examples` |

İki çağrı da aynı girdiyi (kartın `gloss_en`'i, notu, örnekleri) okuyor ve
aynı dile yazıyor. Ayrı olmalarının sebebi tarihsel: `gloss` İş 2'de,
`translate` İş 3'te yazıldı.

Ayrı çağrının iki bedeli var:
1. **Para.** Depoda 8.934 onaylı kart var, dört dilde de ~8.900 anlam eksik.
   Tek çağrı ~35.000 çağrı tasarruf eder.
2. **Tutarsızlık.** Karşılık ile çeviri farklı çağrılardan geliyor. Gloss
   "kıyı" derken örnek cümlede "yaka" geçebilir. `translate/prompt.py`
   "aynı terimi kullan" diyor, ama gloss'u görmüyor.

## 2. Hedef

`lexicon-card translate --l1 X` anlam başına ve dil başına **tek çağrıda**
hem karşılığı (`gloss_l1`, `gloss_note`) hem çeviriyi (`definition`,
`usage_note`, `examples`) üretsin. `gloss` komutu kalksın.

**Karmaşıklık artmamalı, azalmalı.** Sonuçta iki paket (`gloss/` +
`translate/`) yerine tek paket olmalı. Yeni soyutlama, yeni seam ya da motor
değişikliği gerekmez.

## 3. Sözleşme — pazarlığa açık değil

1. **Şema değişmez.** Beş tablo aynen kalır, isimleri ve sütunları dahil.
   Bu sayede `delivery/collect.py`, `review/`, `lexicon_card/panel/` ve
   `public.py` **tek satır değişmez**. Değişirse bu bir tasarım hatasıdır,
   dur ve sor.
2. **Mevcut satırlar yeniden ödenmez ve ezilmez.** Bugün depoda duran
   `tr` 982 gloss, 4×50 çeviri ve varsa insan satırları (tier 0) korunur.
   Birimin iki parçası da onaylıysa çağrı yapılmaz. Bir parçası
   onaylıysa (ör. gloss var, çeviri yok) çağrı yapılır, ama **onaylı ya da
   insan parçası üzerine yazılmaz**. Bu karar yazma kapısında
   (`core/jobs/store/policy.py::should_write`) verilir, ikinci bir kural
   kümesi yazılmaz. Mevcut onaylı gloss prompt'a **sabit terim** olarak
   verilir: "bu kelime için bu karşılığı kullan".
3. **QA kopyalanmaz, birleştirilir.** Bugünkü `gloss/qa.py` ve
   `translate/qa.py`'deki kapılar olduğu gibi taşınır. Hiçbir kapı
   gevşetilmez ya da sıkılaştırılmaz. İlk red kazanır, uyarılar
   hepsinden toplanır (`cloze/qa/__init__.py` deseni).
4. **Tek karar, hepsi ya da hiç.** Paketin herhangi bir parçası reddedilirse
   hiçbir içerik yazılmaz, yalnızca durum satırları yazılır. Bir paket tek
   bir durum taşır, "yarım onaylı paket" yoktur.
5. **Yeni kapı önerirsen reddetme, uyar** (§6.7): ölçülemeyen şey reddetmez.
   Önerilebilecek tek yeni kontrol, gloss teriminin örnek cümlelerde geçip
   geçmediği. Çekim yüzünden garanti edilemez, o yüzden **uyarıdır**.
6. **Motor değişmez.** `core/jobs/` kapsam dışı.

## 4. Önerilen yapı

```
modules/lexicon_card/translate/
  units.py      # bugünkü translate/units.py + mevcut onaylı gloss (varsa)
  prompt.py     # tek prompt: karşılık + çeviri, tek JSON
  qa/
    __init__.py # iki kontrolü sırayla çalıştırır
    gloss.py    # bugünkü gloss/qa.py (taşınır, değişmez)
    entry.py    # bugünkü translate/qa.py (taşınır, değişmez)
  store.py      # beş tablonun TEK yazıcısı, tek transaction
  job.py
```

- `gloss/` paketi ve `commands/gloss_command.py` **silinir**. Ölü kod
  bırakılmaz. `lexicon-card gloss` artık `invalid choice` hatası verir
  (sessiz yok sayma yok, İş 2b'deki `cards --l1` kaldırılması gibi).
- Beklenen JSON:
  ```json
  {"gloss_l1": "...", "gloss_note": "",
   "definition": "...", "usage_note": "", "examples": ["...", "..."]}
  ```
- `kind` yeni bir ad alır (ör. `"l1_entry"`), `prompt_version = "v1"`.
  `max_tokens` iki eski işin toplamını karşılayacak kadar olmalı.
- Dosya adları öneridir. Tek sorumluluk ve küçük dosya kuralı geçerli.

## 5. Kapsam dışı

`cards`, `note`, cloze, grammar, `delivery`, `review`, panel, şema,
`core/jobs/`. Mevcut satırları birleştirmek ya da taşımak (migration) da
kapsam dışı: eski satırlar olduğu yerde durur, yeni kod onları okur.

## 6. Kabul ölçütleri

**Testler** (`tests/test_lexicon_gloss.py` ile `tests/test_lexicon_translate.py`
tek dosyada birleşebilir; testlerin **sözleri** korunur, silinmez):

- Tek birim için **tek çağrı** yapılır ve beş tablonun hepsi dolar.
- İkinci koşu **0 ödenen çağrı**.
- Dil başına izolasyon: `--l1 es` koşusu `tr` satırlarına dokunmaz.
- Gloss'u onaylı ama çevirisi eksik birim çağrılır, gloss **değişmez**.
- İnsan satırı (tier 0) hiçbir durumda ezilmez.
- Gloss kısmı reddedilince çeviri de yazılmaz, tersi de aynı.
- Eski QA testlerindeki her red ve uyarı sebebi yeni yolda da aynı sebeple
  çıkar. Özellikle `hotel`→`hotel` uyarıdır, `to`→`a` (es) onaylanır.
- `sense_gloss_l1`in tek yazıcısı yeni store'dur. Mevcut kaynak denetim
  testi (`test_sense_gloss_l1in_tek_yazicisi_gloss_deposudur`) yeni yola
  güncellenir, kural gevşetilmez.
- `lexicon-card gloss` → exit 2.
- `test_layering`, AST docstring denetimi (0 eksik) ve bütün test paketi
  yeşil.

**Gerçek depoda ölçüm** (sıfır para, hepsi `--dry-run`):

- `translate --l1 tr --dry-run` → işlenecek birim ≈ 8.934 − (iki parçası da
  onaylı olanlar). Sayı raporlanır.
- `translate --l1 es --limit 50 --dry-run` → **0 çağrı** (ilk 50'nin iki
  parçası da dolu).
- `git diff --stat` ile `delivery/`, `review/`, `panel/`, `schema.py` ve
  `core/`'un değişmediği gösterilir.

**Pilot** (kullanıcı koşar, para harcar): `--l1 tr --limit 50`. Onay oranı
eski iki işin oranıyla karşılaştırılır, en az 10 ham cevap okunur. Soru:
gloss terimi örneklerde tutarlı mı? Oran düşerse prompt düzeltilir, koşu
büyütülmez.

## 7. Bitince

- `DURUM.md` ve `docs/MIGRATION-PLAN.md` §9'a gerçek ölçüm yazılır.
- `docs/CLI_KOMUTLARI.md`'de 5. ve 6. adım tek adıma iner.
- Her dosyada Türkçe kısa docstring **baştan** yazılır.
