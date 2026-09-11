# İş 1 — `variant` ekseni

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

Önce oku: `DURUM.md` → `docs/MIGRATION-PLAN.md` (§1 mimari, §6 disiplin) →
`docs/V2-BRIEF.md` (bu işin neden var olduğu) → kod.

---

## Görev

Bugün bir depo satırının kimliği `stable_key`'dir ("en:bank:noun"). Yakında
gelecek iki iş **aynı anlam için birden çok satır** üretecek:

- aynı kelimenin İspanyolca **ve** Almanca karşılığı (İş 2),
- aynı anlamın kolay/orta/zor cloze sorusu (v2, sonra).

Bu iş o ekseni açar. **Tek başına hiçbir içerik üretmez, hiçbir LLM çağrısı
yapmaz, kullanıcıya görünen hiçbir şey değiştirmez.** Ürünü: bir anahtar
sözleşmesi, testleri ve "boş `variant` ile davranış bit bit aynı" kanıtı.

---

## Kodda doğrulanmış durum

Bunları kendi gözünle teyit et, sonra başla:

- `core/jobs/base.py::JobContext.variant` **var** (varsayılan `""`), ve
  `core/jobs/schema.py`'deki `job_attempts` tablosunda `variant` sütunu var.
- `core/jobs/engine/attempt.py` `ctx.variant`'ı deneme günlüğüne geçiriyor.
- **Hiçbir iş ya da depo `variant`'ı anahtar olarak kullanmıyor.** İlan edilmiş
  ama tüketilmemiş bir eksen.
- Anahtar eşleşmesi **tam iki yerde** oluyor: `plan/planner.py`'de
  `existing.get(unit.key)` ve `engine/loop.py`'de `existing.get(unit.key)`.
- `ArtifactStore.load_existing(ctx)` zaten `ctx` alıyor — yani varyantı biliyor.
- `store/policy.py::should_write` ve `plan/verdict.py::decide` anahtarı **hiç
  görmüyor**; yalnızca `Existing` alanlarına bakıyorlar.

Bunun pratik sonucu: **motorun kendisi büyük ihtimalle hiç değişmeyecek.** İş,
anahtarın nasıl üretildiğine dair bir sözleşme koymak ve onu testle çivilemek.
Eğer motoru değiştirmek zorunda kaldığını düşünüyorsan, önce dur ve nedenini
yaz — büyük olasılıkla yanlış yere variant sokuyorsundur.

---

## İstenen

1. **Bileşik anahtar sözleşmesi.** `Unit.key` varyanta duyarlı anahtar olur;
   ham `stable_key` ayrıca `Unit.data` içinde taşınır. `load_existing` **aynı
   anahtar uzayını** döndürür. Anahtar biçimi **tek bir yerde** üretilir (örn.
   `core/jobs/keys.py`); hiçbir modül kendi ayırıcısını uydurmaz.

2. **Boş varyant = bugünkü anahtar.** `key(stable_key, "")` sonucu `stable_key`
   ile **birebir aynı** dizgi olmalı. Mevcut satırlar için migration YOK.

3. **Motorun imzaları değişmez.** `planner`, `loop`, `policy.should_write`,
   `verdict.decide` fonksiyonlarına `variant` parametresi **eklenmeyecek**.
   Gerekçe: yazma kapısı ve redo matrisi bilerek anahtar-agnostik; oraya varyant
   sokmak ikinci bir kural kümesi doğurur ve MIGRATION-PLAN §2'nin "tek kapı"
   sözünü bozar.

4. **Deneme günlüğü anlamını kaybetmeyecek.** Bugün `attempts.record`'a
   `stable_key=unit.key` geçiliyor. `unit.key` bileşik hale gelince o sütun
   sessizce anlam değiştirir ve günlük depoyla eşleşmez. Günlüğe **ham
   `stable_key`** gitmeli, varyant kendi sütununda durmalı.

5. **Rapor varyantı göstersin.** Plan çıktısındaki okunur ad (`Unit.name`)
   hangi varyant olduğunu söylesin; iki varyantın planı ekranda ayırt edilebilsin.

6. **Sözleşme yazılı olsun.** `core/jobs/base.py` (ya da `keys.py`) docstring'i
   varyantın ne olduğunu ve ne OLMADIĞINI söylesin: varyant motor tarafında bir
   **anahtar**tır, her depoda bir sütun olmak zorunda değildir.

---

## Kabul ölçütleri

- Mevcut **178 test tek satır değişmeden** geçer (`test_layering` dahil).
- `polyvo lexicon-card cards --tag v7 --limit 1000 --dry-run --no-interactive`
  çıktısı bu işten önce ve sonra **kelimesi kelimesine aynı**. (Önce koş, kaydet,
  sonra karşılaştır.)
- Yeni test: aynı `stable_key` + iki farklı varyant → **iki ayrı satır**,
  birbirini ezmiyor, her biri kendi kapı kararını alıyor.
- Yeni test: boş varyantta üretilen anahtar ham `stable_key`'e eşit.
- Yeni test: `job_attempts` satırında `stable_key` **ham**, `variant` dolu.
- Türkçe kısa docstring'ler baştan yazılmış (sonradan eklenmiş değil).

## Yapma

- `policy.py` / `verdict.py`'ye varyant parametresi ekleme.
- Depolara zorunlu bir `variant` metin sütunu ekleme. `sense_gloss_l1`'in doğal
  anahtarı zaten `(sense_id, l1)`; varyant orada bir sütun olarak tekrar
  edilmemeli.
- Mevcut satırları migrate etme, `data/stores/` içeriğine dokunma.
- Bu işte yeni bir kullanıcı komutu ya da yeni içerik üretme.
