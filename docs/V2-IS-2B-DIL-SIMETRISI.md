# İş 2b — dil simetrisi: `cards` L1 üretmeyi BIRAKIR

Bu bir görev tanımıdır, plan değildir. Planı sen yaparsın; aşağıdaki **hedef,
sınır ve kabul ölçütü** pazarlığa açık değildir.

**Ön koşul:** İş 1 (`variant` ekseni) ve İş 2 (`gloss` koşusu) bitmiş — ikisi de
bitti. Bu iş onların bıraktığı asimetriyi kapatır.

Önce oku: `DURUM.md` → `docs/V2-IS-2-COKDILLI-L1.md` → kod.

---

## Görev

Bugün diller eşit değil. `polyvo lexicon-card cards --l1 tr` kartı üretirken
**Türkçe karşılığı da aynı çağrıda** üretip yazıyor; `es`/`pt-BR`/`de` ise ayrı
bir `gloss` koşusundan geçiyor. Kullanıcının kararı: **dört dil de eşit, her
biri kendi katmanında kendi işini yapacak.**

Diller: `tr` · `es` · `pt-BR` · `de` (`polyvo.toml`'da zaten bu sırada).

İstenen: `cards` yalnızca **İngilizce kartı** üretir. L1 karşılığı — Türkçe
dahil — **yalnızca** `gloss` koşusundan gelir.

---

## Bugün ne oluyor (kodda doğrulanmış)

Bunları kendi gözünle teyit et, sonra başla:

1. `modules/lexicon_card/store.py::_write_content` içinde
   `if ctx.l1 and payload.get("gloss_l1"):` → **`cards` koşusu
   `sense_gloss_l1`e yazıyor.** Yani o tablonun bugün İKİ yazıcısı var
   (`LexiconCardStore` ve `gloss/store.py::LexiconGlossStore`).

2. `modules/lexicon_card/qa.py` kart QA'sında:
   ```
   gloss_l1 = _text(parsed.get("gloss_l1"))
   if not gloss_l1: return QaResult(False, "gloss_l1_bos")
   ... l1_form.check(...) -> reject
   ```
   → **L1 karşılığı kötü diye ÖDENMİŞ İngilizce kart reddediliyor.** Bu bir
   simetri sorunu değil, doğrudan para kaybı: `gloss_en`/`register`/örnekler
   kabul edilebilir olduğu halde satır `rejected` yazılıyor ve içeriği
   atılıyor. Depodaki 43 reddedilmiş kartın bir kısmının sebebi bu olabilir —
   **ölç, tahmin etme** (`attempts.reject_reasons`).

3. `modules/lexicon_card/prompt.py` kart prompt'u `gloss_l1` alanını ve
   `rules.PROMPT_RULES`'u (L1 biçim kuralları) taşıyor.

4. `core/jobs/plan/verdict.py::decide` **`prompt_hash`e BAKMIYOR** — yalnızca
   `tier`/`status`/`rank`. Sonuç: kart prompt'unu değiştirip `prompt_version`
   artırmak mevcut onaylı kartları yeniden tetiklemez. **Bu işin risksiz
   olmasının sebebi budur; başlamadan önce bunu doğrula.**

5. `delivery/gate.py` `l1_karsiligi_yok` bayrağını zaten kaldırıyor
   (`if shipment.l1 and not (row.gloss_l1 or "").strip()`). Ayırmadan sonra
   "gloss koşusunu unuttum" hatasını yakalayan ağ budur — yeni bir kontrol
   yazma, olanı kullan.

---

## İstenen davranış

1. **`cards` artık L1 üretmez.** Kart prompt'undan `gloss_l1` alanı ve L1
   biçim kuralları çıkar; kart QA'sından `gloss_l1` kontrolleri çıkar; kart
   deposu `sense_gloss_l1`e **hiç yazmaz**. `sense_gloss_l1`in tek yazıcısı
   `gloss/store.py` olur.

2. **Kart prompt'u değiştiği için `prompt_version` artırılır.** Yeni sürüm
   deneme günlüğünde görünmeli. Mevcut satırlar yeniden üretilmez (madde 4).

3. **Mevcut Türkçe karşılıklar dokunulmaz.** `sense_gloss_l1`deki `tr`
   satırları yerinde kalır; `gloss --l1 tr` onları `load_existing`de görür ve
   `skip_done` der. **Migration YOK, yeniden üretim YOK, yeniden ödeme YOK.**

4. **`cards` komutunun `--l1` bayrağı anlamını kaybeder.** Kart artık dile
   bağlı değil. Bayrağı sessizce kabul edip yok sayma — ya kaldır ya da
   kullanıcıya ne yapması gerektiğini söyle (`gloss --l1 <kod>`). Sessiz
   yok sayma yasak: kullanıcı `cards --l1 de` yazıp "Almanca üretildi"
   sanmamalı.

5. **Dört dil tek bir yolla üretilir.** `tr` için ayrı kod yolu, ayrı bayrak,
   ayrı istisna kalmayacak. Bir dilin eklenmesi = `polyvo.toml`'a kod +
   `core/lang/<kod>.py` + bir koşu. Başka hiçbir dosya değişmemeli.

6. **`l1_form` / `get_rules` kart tarafında artık kullanılmıyorsa import
   bırakma.** Ölü bağ kalmasın; `l1_form` yalnızca `gloss/qa.py`nin çağırdığı
   tek tanım yeri olarak kalır.

7. **Reddedilmiş kartlar yeniden değerlendirilebilir olsun.** Ayırmadan sonra,
   yalnızca L1 yüzünden reddedilmiş kartlar artık geçebilir. Bunu bu işte
   KOŞMA — ama `--redo bad` ile kaç kartın yeniden denemeye aday olduğunu
   `--dry-run` ile **raporla**, kullanıcı kararını versin.

---

## Kapsam dışı — dokunma

- `delivery/`e dokunma (çok dilli sevkiyat = İş 7). `gate.py`deki
  `l1_karsiligi_yok` kontrolü **olduğu gibi kalır**, gevşetilmez.
- `core/jobs/` motorunu değiştirme.
- `sense_gloss_l1` / `sense_gloss_l1_state` şemasını değiştirme.
- `data/stores/` içeriğine dokunma; hiçbir satırı silme, taşıma, migrate etme.
- Cloze, örnek cümle çevirisi, açıklama çevirisi — hepsi ayrı iş.
- Kendi başına gerçek (parali) koşu başlatma. Bu iş **sıfır LLM parası**
  harcar; yalnızca `--dry-run` koşulur.

---

## Kabul ölçütleri

- `cards --tag v7 --limit 1000 --dry-run` → **0 ödenecek çağrı** (957 onaylı
  kart `skip_done`; prompt değişti diye yeniden tetiklenmedi). Bu, işin en
  önemli kanıtı — önce koş, kaydet, sonra karşılaştır.
- `gloss --l1 tr --dry-run` → **0 ödenecek çağrı** (mevcut Türkçe karşılıklar
  tanınıyor, yeniden ödenmiyor).
- `gloss --l1 es --dry-run` → **957 işlenecek** (ayırma es'i bozmadı).
- Yeni bir kelime için `cards` koşusu → `sense_gloss_l1`e **tek satır
  yazmıyor** (testle göster; bugünkü davranışın tersi).
- Kart QA'sı artık `gloss_l1` yüzünden **reddetmiyor**: `gloss_l1`i hiç
  olmayan bir model cevabı, gloss_en/örnekler sağlamsa **kabul ediliyor**
  (testle göster — bu işin varlık sebebi).
- `sense_gloss_l1`e yazan tek sınıf `LexiconGlossStore`; testle çivilenmiş
  (örn. kart deposunun kaynağında o tabloya `INSERT` yok).
- `cards --l1 de` yazan kullanıcı **yanlış yönlendirilmiyor** (bayrak yok ya
  da açık uyarı var).
- Mevcut 216 test yeşil; `test_layering` yeşil. L1 kontrollerini kart
  tarafından çıkarırken silinen testlerin karşılığı `gloss` tarafında
  **var olduğundan emin ol** — kontrol taşınmalı, kaybolmamalı.
- Testler gerçek `data/`ye yazmıyor
  (`monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`).
- `--redo bad --dry-run` ile yeniden denemeye aday reddedilmiş kart sayısı
  raporlandı (koşulmadı).
- `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm** yazıldı (tahmin
  değil), 43 reddedilmiş kartın sebep dökümü dahil.
