# İş 3 — çeviri katmanı: tanım, kullanım notu, örnek cümleler (4 dil)

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul:** İş 1 (varyant ekseni), İş 2 (`gloss` koşusu), İş 2b (dil
simetrisi) bitti; yanlış-red düzeltmesi (`l1_form.FormResult`) yapıldı.

Önce oku: `DURUM.md` → `docs/V2-IS-2-COKDILLI-L1.md` → `docs/V2-IS-2B-DIL-SIMETRISI.md` → kod.

---

## Görev

Bugün öğrenciye ana dilinde giden tek şey **kelimenin karşılığı**
(`sense_gloss_l1`). Tanım, kullanım notu ve örnek cümleler yalnızca
İngilizce. İstenen: bunların da dört dile çevrilmesi.

Diller: `tr` · `es` · `pt-BR` · `de` — **dördü eşit**, her biri kendi koşusu.

Bir de kullanılmayan bir alanı canlandırmak: `usage_note`.

---

## Bugün ne oluyor (ölçüldü, 2026-09-06)

Gerçek `v7` deposunda:

| şey | durum |
|---|---|
| `sense_cards` | 957 approved / 43 rejected |
| `sense_examples` | 1914 cümle (anlam başına 2) |
| `sense_gloss_l1` | `tr` 957 · `es` 50 (pilot) |
| **`usage_note` dolu** | **957 kartın 4'ünde** |
| `item_level.cefr` | 1000 kelimenin 840'ında var, **160'ında YOK** |

`usage_note`un boş olması hata değil, **eksik prompt**:
`modules/lexicon_card/prompt.py` şema iskeletinde
`"usage_note": "<optional short note, or empty string>"` diyor ama
`Rules:` bölümünde `usage_note` için **tek satır kural yok**. Modele ne zaman
dolduracağı söylenmiyor, o da doldurmuyor.

---

## İstenen davranış

### A. `usage_note` gerçek bir alan olur

1. **`usage_note` kendi `kind`ı olur, kartın parçası olmaktan çıkar.**
   Gerekçe İş 2b'nin dersidir: `sense_cards`ın tek yazıcısı `LexiconCardStore`
   kalmalı. Not kendi tablosunda, kendi koşusunda, kendi QA'sında durur.
   Kart prompt'undan `usage_note` **tamamen çıkar** (bir alanın tek üreticisi
   olur).

2. **Not KOŞULLUDUR, her anlamda dolmaz.** Modele "istersen doldur" demek
   ölçüldü ve sonucu 957'de 4. Bunun yerine doldurma sebebi **sayılabilir**
   olmalı; en az şunlar: deyimsel kullanım, birebir çevirisi yanlış anlam
   veren ifade, ana dilde tam karşılığı olmayan kültürel kavram, sık yapılan
   kullanım hatası. Sebep yoksa model **boş bırakır ve bu bir red değildir.**

3. **QA kapısı:** not varsa `gloss_en`in kopyası ya da yeniden ifadesi
   olamaz (garanti edilebilir, reddeder). Notun "gerçekten gerekli olup
   olmadığı" garanti edilemez → **uyarır, reddetmez** (§6.7).

4. Mevcut 957 onaylı kart için bu koşu çalıştırılabilir olmalı; kartlar
   **yeniden üretilmez ve yeniden ödenmez** (`verdict.decide` `prompt_hash`e
   bakmıyor, bunu doğrula).

### B. Çeviri koşusu

5. **Çevrilecekler:** `gloss_en` (tanım), `usage_note` (varsa), örnek
   cümleler. `gloss_l1` (kelime karşılığı) **bu işin kapsamında değil** —
   zaten kendi `kind`ında üretiliyor, `tr` için 957, `es` için 50 satır
   ödendi; yeniden ödettirme.

6. **Anlam başına dil başına TEK çağrı.** Bir anlamın tanımı, notu ve iki
   örneği aynı istekte çevrilir. İki gerekçe: (a) model anlamın tamamını
   görünce terimi tutarlı çevirir — tanımda "kıyı", örnekte "yaka" olmaz;
   (b) 4 ayrı çağrı yerine 1 çağrı.

7. **Bu paketin hepsi-ya-hiç reddedilmesi MEŞRUDUR** ve İş 2b'nin düzelttiği
   hatayla karıştırılmamalıdır. Oradaki hata, ödenmiş bir **İngilizce** kartı
   **başka bir dilin** kalitesi yüzünden çöpe atmaktı. Burada paketin tamamı
   aynı işin, aynı dilin ürünü — eksik alan bir biçim hatasıdır, yeniden
   denenir. Kart tarafına **hiçbir koşulda** dokunulmaz.

8. **Çeviri doğaldır, birebir değildir.** Kullanıcı kararı: her alan için
   **tek** çeviri. Cümlelerde ikinci bir "birebir çeviri" alanı **YOK** —
   cümlelerin çoğunda iki çeviri aynı çıkar, kopya üretir ve insan denetim
   yükünü ikiye katlar. Kültürel açıklama **kelimeye** aittir (`usage_note`,
   anlam başına bir kez), cümleye değil.

9. **Kelime karşılığının notu (küçük istisna).** `gloss_l1` için ana dilde
   temiz bir karşılık yoksa **kısa** bir not yazılabilir. Bu, her satırda
   dolan bir alan değildir; QA kapısı: not varsa karşılığın kendisiyle
   neredeyse aynı olamaz (ölçülebilir).

10. **Şema dille büyümez.** Beşinci bir dil eklemek `polyvo.toml`'a bir kod,
    `core/lang/<kod>.py`'ye bir dosya ve bir koşu olmalı — **tablo, sütun ya
    da kod değişikliği gerektirmemeli.** Dil başına tablo/sütun açan tasarım
    reddedilir.

11. **Her tablonun TEK yazıcısı olur.** İş 2b'de düzeltilen hata tekrar
    edilmez; iki farklı `kind` aynı tabloya yazmaz.

12. **`review` yeni alanları da düzeltebilmeli.** `review export --l1 de`
    çevrilmiş tanımı/notu/örnekleri çıkarıp geri yazabilmeli, yazılan satır
    `tier=0`/`source='human'` olmalı. Panelde kart ayrıntısında görünmeli.

---

## Kapsam dışı — dokunma

- `delivery/`e dokunma (çok dilli sevkiyat = İş 7). **`delivery materialize
  --l1 <tr disinda>` KOŞULMASIN** — `_dist_meta.json` tek L1 tanır, ikinci
  dil ilk dilin manifest kaydını ezer ve `verify --l1 tr` düşer.
- Cloze (İş 4) bu işte yok.
- `sense_cards` / `sense_gloss_l1` / `sense_examples` şemalarını değiştirme.
- İngilizce örnek cümleleri yeniden üretme; `gloss_en`i yeniden üretme.
- `core/jobs/` motorunu değiştirme.
- Kendi başına büyük parali koşu başlatma.

---

## Pilot — kademelilik

- Önce her yeni `kind` için `--limit 50 --dry-run`: kaç birim işlenecek, kaç
  çağrı ödenecek — **para harcamadan** doğrulanır.
- Gerçek koşu tek modele sabit (`model_quality.json` global kalıyor).
- Koşudan sonra QA reddetme oranı MIGRATION-PLAN §9.4 biçiminde raporlanır:
  işlenen / onaylanan / reddedilen + **sebep dökümü**
  (`attempts.reject_reasons`). **Ayrıca red sebeplerinin gerçekten hata olup
  olmadığı örneklenerek kontrol edilir** — `job_attempts.raw_response`
  okunur. Sebep: `es` pilotunda reddedilen 3 birimin **üçü de doğru cevaptı**
  (`to`→"a", `non`→"no"); orana bakıp geçmek bunu kaçırıyordu.
- Oran kötüyse prompt/QA düzeltilir, **koşu büyütülmez**.
- Diller sırayla: `tr` → `es` → `pt-BR` → `de`. Bir sonrakine ancak öncekinin
  oranı görüldükten sonra geçilir.

---

## Kabul ölçütleri

- `usage_note` koşusu `--dry-run` → 957 onaylı kart işlenecek, **0 kart
  yeniden üretimi**.
- `usage_note` koşusundan sonra `cards --dry-run` → **0 ödenecek çağrı**
  (kart yeniden tetiklenmedi).
- Notu boş bırakan cevap **reddedilmiyor** (not koşulludur; testle göster).
- Notu `gloss_en`in kopyası olan cevap **reddediliyor** (testle göster).
- `sense_cards`a yazan tek sınıf `LexiconCardStore`; `usage_note` ve çeviri
  koşuları o tabloya **INSERT/UPDATE yapmıyor** (testle çivile).
- Çeviri koşusu `--l1 tr --dry-run` → 957 işlenecek, **0 `gloss_l1` çağrısı**
  (kelime karşılığı yeniden ödenmiyor).
- İkinci `--l1 tr` koşusu → **0 ödenecek çağrı** (artımlılık; her yeni `kind`
  için ayrı kanıtlanır).
- `--dry-run` tek kuruş harcamıyor ve **tek satır yazmıyor**.
- Bir dilin çevirisi başka bir dilin satırını **etkilemiyor**
  (`--l1 de` koşusundan sonra `--l1 tr --dry-run` → 0 çağrı).
- Beşinci bir dil (örn. `fr`) eklemek **şema değişikliği gerektirmiyor** —
  testle göster (uydurma bir kodla tablo/sütun eklemeden koşu planlanabiliyor).
- Kartsız / onaylanmamış anlam çeviri koşusuna **girmiyor**.
- İnsan satırı (tier 0) varken o alan için çağrı **istenmiyor**.
- `review export/import --l1 de` yeni alanları taşıyor, yazılan satır
  `tier=0`/`human`.
- Mevcut 235 test yeşil; `test_layering` yeşil.
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- Türkçe kısa docstring'ler baştan yazılmış (sonradan eklenmiş değil).
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı.
