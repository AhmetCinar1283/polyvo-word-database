# v2 brief — çok dilli L1 · cloze · panelden düzeltme

Bu dosya bir **plan değil, bir görev tanımıdır**: v2'yi yapacak agent'a
verilecek metin. Sıra, dosya adı ve imza kararlarını agent kendi verir; burada
yazan **hedef, sınır ve kabul ölçütüdür**.

Okuma sırası: `DURUM.md` → `docs/MIGRATION-PLAN.md` (§1 mimari, §5 şema, §6
disiplin, §9 ölçümler) → bu dosya → kod.

---

## 0. Görev

v1 bitti: 5.000 kelimelik evren, 291 ödenmiş EN kart + TR gloss, sevkiyat
(`core.db` · `en.db` · `i18n_tr.db`), insan düzeltme yolu (JSONL export/import)
ve salt okunur panel. v2'de üç yetenek isteniyor:

- **A — çok dilli L1.** Aynı ödenmiş EN kartın üstüne ikinci, üçüncü ana dil
  (es, de, …). **EN kart yeniden ödenmeyecek**; yalnızca eksik dilin karşılığı
  üretilecek.
- **B — cloze.** Her anlam için boşluk doldurma sorusu, L2'de ve istenen L1
  dillerinde. **Kademeli**: tek seferde bütün depoya değil, ölçülerek büyüyen
  koşularla.
- **C — panelden insan düzeltmesi.** Bugün panel salt okunur, düzeltme JSONL
  dosyasıyla yapılıyor. Panelden de düzeltilebilmeli — ama **ikinci bir yazma
  yolu açılmadan**.

---

## 1. Bugünkü kodun bu işi doğrudan yapamamasının SOMUT sebepleri

Bunlar tahmin değil, kodda doğrulandı. Agent işe başlamadan her birini kendi
gözüyle teyit etmeli.

**(1) İkinci L1 koşusu tamamen atlanır.**
`modules/lexicon_card/store.py::load_existing` yalnızca `sense_cards`a bakar ve
`stable_key -> Existing` döner. `core/jobs/plan/verdict.py::decide` `approved`
gördüğü satıra `skip_done` der. Sonuç: `lexicon-card cards --l1 es` **291
kartın hepsini atlar, sıfır İspanyolca gloss üretir**. Depo şeması hazır
(`sense_gloss_l1` birincil anahtarı `(sense_id, l1)`), tıkanan yer plan
aşamasıdır.

**(2) `variant` ekseni ilan edilmiş ama tüketilmiyor.**
`core/jobs/base.py::JobContext.variant` var, `core/jobs/attempts.py` ve
`core/jobs/schema.py` onu deneme günlüğüne yazıyor — ama **hiçbir iş depo
anahtarına katmıyor**. Hem "aynı anlam, farklı dil" hem "aynı anlam, farklı
soru türü" tam olarak bu eksendir. v2'nin temel işi budur; A ve B'nin ikisi de
buna dayanır.

**(3) `delivery` şeması sabit, modüllere kapalı.**
`delivery/schema.py` içinde `CORE_DDL`/`L2_DDL` sabit metin; `delivery/collect.py`
doğrudan `modules.lexicon_card.schema`'yı import ediyor. Cloze'u sevk etmek bu
iki dosyayı elle düzenletir — bu, planın kendi koyduğu sınavı ("yeni modül
mimariye *bir klasör* olarak girer, mevcut hiçbir dosyayı düzenletmez",
MIGRATION-PLAN §7) düşürür. **`APP.panel` gibi bir `APP.dist` katkı seam'i
gerekiyor**: her app sevkiyata kendi tablosunu, kendi satırlarını ve kendi kapı
kuralını getirir; `delivery` neyin geldiğini bilmez.

**(4) `review` tek modüle sabitlenmiş.**
`review/export.py` ve `review/apply.py` doğrudan `lexicon_card.schema`'yı
import ediyor, `record.EDITABLE_FIELDS` sabit bir liste. Cloze düzeltmesi bu
haliyle imkânsız. Genelleşmeli: **her app kendi "düzeltilebilir alan"
sözleşmesini getirsin**, `review` onu keşiften alsın.

**(5) Panel katmanı düzeltme yazamaz — ve katman kuralı bunu yasaklar.**
Sayfa router'ı `modules/` içinde (katman 3), `review` katman 4. Modül review'i
import EDEMEZ. Çözüm katmanı esnetmek değil: **düzeltme sayfası `review/panel/`
altında yaşar** (katman 4; modules'ü ve review'i import edebilir), modül sayfası
ona link verir. `panel/` host'u yine hiçbir şey bilmez.

**(6) `_dist_meta.json` tek L1 tanır.**
`delivery/materialize.py` bir koşuda `filenames(l2, l1)` kadarını yazıyor.
İkinci dil için ikinci koşu meta'yı ezer; `verify --l1 tr` artık o dosyayı
manifestte bulamaz. Çok dilli sevkiyat **tek koşuda bütün L1'leri** almalı.

---

## 2. İş kalemleri

Her kalemde: *amaç · sözleşme · kabul*. Dosya adları öneridir, agent kendi
kararını verir; **sözleşme ve kabul ölçütü pazarlığa açık değildir**.

İlk ikisi ayrı dosyada, agent'a doğrudan verilecek biçimde yazıldı:
`docs/V2-IS-1-VARIANT.md` ve `docs/V2-IS-2-COKDILLI-L1.md`. Buradaki özetle
o dosyalar çelişirse **o dosyalar geçerlidir**.

### İş 1 — `variant` eksenini gerçekten tüketilir hale getir

*Amaç:* bir depo satırının kimliği `stable_key` değil `(stable_key, variant)`
olabilsin. `variant` boş dizgi olduğunda bugünkü davranış **bit bit aynı**
kalmalı (geriye dönük uyum).

*Sözleşme:* `ArtifactStore.load_existing(ctx)` zaten `ctx` alıyor — anahtar
üretimi oraya taşınır. Motorun kendisi (`core/jobs/engine/`), yazma kapısı
(`store/policy.py`) ve redo matrisi (`plan/verdict.py`) **değişmez**; onlar
zaten anahtarın ne olduğunu bilmiyorlar.

*Kabul:* mevcut 178 test tek satır değişmeden geçer; `variant` verilmiş iki
koşu birbirinin satırını ezmez; deneme günlüğünde iki koşu ayrı görünür.

### İş 2 — çok dilli L1 (yetenek A)

*Amaç:* `cards --l1 es` ödenmiş EN kartlara dokunmadan yalnızca eksik
İspanyolca karşılığı üretsin.

*Sözleşme:* L1 gloss'u kartın bir parçası değil, **kendi satır ailesi** olur
(`variant = l1`). Kartın kendisi (gloss_en, örnekler) tekrar üretilmez ve
tekrar ödenmez. Prompt L1'e özel olabilir; `core/lang/` altındaki dil kuralları
(bugün `tr.py`) yeni dil için genişletilir, `qa.py`'nin dile özel kontrolü
(`l1_ceviri_yapilmamis` gibi) o dilin kuralından beslenir.

*Kabul:* 291 kartlı depoda `--l1 es --dry-run` **291 işlenecek / 0 kart yeniden
üretilecek** raporlar; gerçek koşudan sonra `--l1 tr --dry-run` hâlâ **0 ödenecek
çağrı** der (tr'ye zarar verilmedi); ikinci `--l1 es` koşusu **0 ödenecek çağrı**.

### İş 3 — `delivery`'ye modül katkısı seam'i

*Amaç:* `delivery` hangi modüllerin var olduğunu bilmesin.

*Sözleşme:* `APP.dist` (ya da eşdeğeri) bir modülün getirdiği: hangi dosyaya
yazacağı, DDL'i, satırları ve **kendi sevk kapısı kuralları**. `delivery/gate.py`
kendi genel kurallarını korur (olgu ≠ ifade ayrımı, `shippable` kontrolü)
ve modülün kurallarını da toplar; **ihlalde yine sıfır dosya**.

*Kabul:* `lexicon_card` bu seam'e taşındıktan sonra üretilen `core.db`/`en.db`/
`i18n_tr.db` **bayt bayt bugünküyle aynı** (sha256 karşılaştırmalı test); sahte
bir test modülü eklemek `delivery/` altında hiçbir dosyayı düzenletmez.

### İş 4 — `modules/cloze` (yetenek B)

*Amaç:* onaylı her anlam için cloze sorusu.

*Girdi bağımlılığı:* cloze yalnızca **`status='approved'` lexicon kartı olan**
anlamlar için üretilir — girdisi kartın gloss'u ve örnek cümleleridir. Kartsız
anlam cloze'a girmez.

*Sözleşme:* `modules/lexicon_card/`'ın dosya düzeninin aynısı (`units · seed ·
prompt · qa · store · schema · job · commands · app · panel`). Motor
kopyalanmaz. `variant` cloze'un dilini/türünü taşır. Kimlik `curriculum`'dan
gelir, cloze yeni `item_id` üretmez.

*Kademelilik — kullanıcının açık isteği:* "bir anda olmasın, model performansı
düşmesin". Bunun uygulaması şudur ve **denetlenecektir**:

- **Tek prompt, tek iş.** "Kart + cloze + üç dil"i tek promptta istemek hem
  kaliteyi hem ölçümü bozar. Her `kind` ayrı iş, ayrı prompt, ayrı QA.
- **Önce pilot, sonra büyüme.** İlk koşu `--limit 50`, QA reddetme oranı
  MIGRATION-PLAN §9.4 biçiminde raporlanır (işlenen / onaylanan / reddedilen +
  sebep dökümü). Oran kabul edilebilir değilse **prompt/QA düzeltilir, koşu
  büyütülmez**.
- Araçlar zaten var: `--dry-run`, `--limit`, `--max-new`, `--pace-delay`.
  Yenisi yazılmayacak.
- Model `lexicon_card` gibi tek modele **sabitlenir**; iki modelle yarım dolmuş
  bir depo reddetme oranını ölçülemez hale getirir.

*Açık karar (agent değil, kullanıcı verir):* anlam başına kaç soru; çeldirici
(distractor) üretilecek mi — eski repoda `gatekeeper_options` vardı ama v1'e
taşınmadı; cümle L2'de, seçenekler L2'de, açıklama L1'de mi.

*Kabul:* ikinci koşuda `paid_calls = 0` (artımlılık kanıtı — her yeni `kind`
için yeniden kanıtlanır); `--dry-run` tek kuruş harcamaz ve tek satır yazmaz;
QA en az 5 ayrı bozuk cevabı sebebiyle reddeder; reddedilen satır içerik
yazmaz, yalnızca `status='rejected'` + `reject_reason` ile durur.

### İş 5 — `review`i modülden bağımsızlaştır

*Amaç:* insan düzeltmesi cloze'a ve yeni dillere de çalışsın.

*Sözleşme:* düzeltilebilir alan listesi ve satır okuma/yazma app'ten gelir
(keşifle), `review` onu taşır. **Şu üç kural aynen korunur ve testleri
silinmez:** `tier=0`/`source="human"` `apply.py`'nin sabitidir, dosyadan
okunmaz · sorunlu tek satırda hiçbir satır yazılmaz · yazılan her düzeltme
`data/human/` yedeğine gider ve geri oynatılabilir. Yazma kapısı yine tek
yerdedir (`core/jobs/store/policy.py`); ikinci bir kural kümesi yazılmaz.

*Kabul:* mevcut `tests/test_review.py` sözleri bozulmadan geçer; cloze satırı
da aynı yoldan düzeltilebilir; `restore` yedeği büyütmez.

### İş 6 — panelden düzeltme (yetenek C)

*Amaç:* kullanıcı bir kartı/cloze'u panelde düzeltebilsin.

*Sözleşme:* düzeltme sayfası **`review/panel/`** altında yaşar (katman 4).
Yazma isteği **`review.apply`'a gider** — panel kendi SQL'ini yazmaz, ikinci
yazma yolu açılmaz. Modül sayfaları salt okunur kalır ve düzeltme sayfasına
link verir. `panel/` host'u değişmez; sayfa yine `APP.panel`den gelir.

*Kabul:* panelden yapılan düzeltme depoda `tier=0`/`source='human'` olur ve
`data/human/` yedeğine düşer (JSONL yoluyla **aynı** sonuç); sorunlu girdi
hiçbir satır yazmaz; panel hâlâ dışarıya kapalı (`127.0.0.1`) ve depodan gelen
metin HTML olarak yorumlanmaz.

### İş 7 — çok dilli sevkiyat

*Amaç:* `i18n_tr.db` + `i18n_es.db` + cloze dosyaları tek tutarlı sevkiyat.

*Sözleşme:* `materialize` bir koşuda **bütün L1'leri** alır; `_dist_meta.json`
üretilen her dosyayı listeler. Sevkiyat dosyaları **zaman damgası taşımaz**
(determinizm), lisans atıfı verinin yanında gider.

*Kabul:* `verify` çok dilli sevkiyatta yeşil; aynı girdi iki koşuda aynı
sha256; bir L1'in eksik olması diğerini sevk etmekten alıkoymaz ama
`_dist_meta.json`'da **açıkça görünür**.

---

## 3. Değişmeyecek kurallar

Agent bunları bir tercih değil, **sınır** olarak almalı. Hepsi bugün testle
korunuyor; testi değiştirerek kuralı esnetmek yasaktır.

1. **4 katman, tek yönlü bağımlılık.** `core:0 → dictionary:1 → curriculum:2 →
   modules:3 → delivery:4 / review:4 → panel:5`. `tests/test_layering.py`
   hem beyanı hem gerçek import grafiğini denetler. İki app birbirini import
   edemez.
2. **Yazma kapısı tek yerdedir** (`core/jobs/store/policy.py`). İkinci bir
   "yazayım mı" kural kümesi yazılmaz.
3. **Ödenmiş karar yeniden ödenmez.** Yeni bir yetenek, mevcut satırı yeniden
   üretmenin gerekçesi değildir.
4. **`shippable=False` içerik `data/dist/`e giremez.** Olgu (frekans, CEFR,
   IPA) ≠ ifade (tanım, örnek, soru metni): ifade yalnızca `llm`/`human` ya da
   `shippable=True` kaynaktan sevk edilir.
5. **Kapı önce çalışır; ihlalde sıfır dosya, exit 1.** "Uyarı basıp exit 0
   dönen kapı, kapı değildir."
6. **Testler gerçek `data/`ye asla yazmaz.** Desen:
   `monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))`.
7. **Türkçe kısa docstring baştan**, her modül ve fonksiyonda; sonradan
   eklenmez. Tek sorumluluk, küçük dosya.
8. **Gizli anahtar yalnızca `.env`de.** `polyvo.toml`a, `.env.example`e ve
   repoya girmez.
9. **Para yalnızca `modules/` katmanında harcanır.** `curriculum`, `delivery`,
   `review`, `panel` sıfır LLM çağrısıdır.
10. Her adım bitince `DURUM.md` ve `MIGRATION-PLAN.md` §9'a **gerçek ölçüm**
    yazılır (tahmin değil).

---

## 4. Kararlar — VERİLDİ (2026-09-06)

Aşağıdakiler kullanıcı tarafından kararlaştırıldı, agent bunları yeniden
sormayacak ve değiştirmeyecek.

**L1 dilleri:** `tr` · `es` · `pt-BR` · `de` — **dördü eşit**, hiçbiri
ayrıcalıklı değil (İş 2b bunu sağladı: `cards` artık L1 üretmez). Sıra:
`tr` → `es` → `pt-BR` → `de`, her dil ayrı koşu.

**Çeviri biçimi — GÜNCELLENDİ (2026-09-06).** Her alan için **tek, doğal**
çeviri. Cümlelerde ikinci bir "birebir çeviri" alanı **YOK**: cümlelerin
çoğunda iki çeviri aynı çıkar, kopya üretir ve insan denetim yükünü ikiye
katlar. Kültürel/kullanım açıklaması **kelimeye** aittir — anlam başına bir
kez `usage_note` olarak yazılır ve o da çevrilir; her cümlede tekrar
edilmez. Kelime karşılığında (`gloss_l1`) temiz bir karşılık yoksa kısa bir
not yazılabilir; QA kapısı: not karşılığın kopyası olamaz.

**Çevrilecekler:** `gloss_en` (tanım), `usage_note`, örnek cümleler, cloze
cümleleri. Cloze **şıkları çevrilmez** — bu bir İngilizce alıştırmasıdır.

**Cloze (İş 4) — anlam başına 3 soru, ÜÇÜ DE ÇOKTAN SEÇMELİ.**
GÜNCELLENDİ (2026-09-06): önceki "kolay/orta çeldiricisiz" kararı
**geçersizdir**. Her soru 4 şıklıdır: 1 doğru cevap + **3 çeldirici**.
(Çeldiricisiz sorulması istenirse uygulama zaten şıkları göstermeden sorabilir.)

| soru | cümle uzunluğu | çeldirici yakınlığı |
|---|---|---|
| kolay | kısa | uzak — belirgin biçimde başka anlam alanı |
| orta | orta | ilgili alan ama cümleye açıkça uymuyor |
| zor | uzun | **yakın anlamlı** — anlamı yakın, kullanımı yanlış |

Zorluk **şık sayısından değil çeldiricinin yakınlığından** gelir: seçenek
sunmak soruyu kolaylaştırır (tanıma, hatırlamadan kolaydır), bu yüzden zor
soru ancak çeldiriciler yakın anlamlıysa gerçekten zordur. Diğer şıkların
cümleye **uymadığından emin olunmalı**. Üç soru da **o anlamın CEFR
seviyesinin içinde** kalır — A1 bir anlamın "zor"u A1 kalır.

Bu bir üslup tercihi değil, QA'nın ölçeceği bir sözleşmedir: seviye/uzunluk
kontrol edilebilir olmalı. Anlamsal yakınlık ölçülemez (gömme katmanı yok) →
**uyarı, red değil**.

**Model kalite sırası:** `model_quality.json` **global kalır**; `kind` bazlı
sıralama yapılmayacak.

**Panelden düzeltme yetkisi:** localhost yeterli, kimlik doğrulama eklenmeyecek.

## 5. İlk teslimat — ikiye bölündü

Kullanıcı ilk dilimi iki ayrı göreve böldü; her biri kendi dosyasında, agent'a
doğrudan verilecek biçimde yazıldı:

1. **`docs/V2-IS-1-VARIANT.md`** — varyant ekseni. İçerik üretmez, LLM çağrısı
   yapmaz; boş varyantta davranış bit bit aynı kalır.
2. **`docs/V2-IS-2-COKDILLI-L1.md`** — ikinci dil (`es`), İş 1'in üstüne.
   Ardından kullanıcı **50 kelimelik gerçek pilotu** koşar ve reddetme oranını
   görür; oran iyiyse büyür, kötüyse prompt/QA düzeltilir.

Cloze (İş 4) bu ikisi ve pilot ölçümü bitmeden başlamaz.
