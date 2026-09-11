# Durum

Compact/yeni oturum sonrası önce bunu, sonra `docs/MIGRATION-PLAN.md` §9'u oku.
Her adım bitince bu dosya güncellenir — kalıcı olmayan "sohbet hafızası" değil,
buradaki bilgi.

## Şu an neredeyiz

**v2 İş 3b (`gloss`+`translate` birleştirme) KOD BİTTİ (2026-09-11).**
`lexicon-card gloss` komutu kalktı; `lexicon-card translate --l1 <kod>`
artık anlam başına dil başına **tek çağrıda** hem karşılığı (`gloss_l1`,
`gloss_note`) hem çeviriyi (`definition`, `usage_note`, `examples`) üretiyor.
Şema, `core/jobs/`, `delivery/`, `review/`, `panel/`, `public.py` **tek satır
değişmedi** (hash karşılaştırmasıyla doğrulandı) — yalnızca `schema.py` ve
`lexicon_card/store.py`'de iki yorum satırı güncellendi (eski `gloss/store.py`
referansı). Detay: plan §9.13.

**Ölçüldü (`--dry-run`, sıfır çağrı):** `translate --l1 tr --dry-run` →
8.884 işlenecek, 50 atlanan (önceki gerçek `tr` koşusundan kalan).
`translate --l1 es --limit 50 --dry-run` → **0 ödenecek çağrı** (ilk 50'nin
iki parçası da dolu). `lexicon-card gloss --l1 tr` → `invalid choice`,
exit 2.

**Sırada (kullanıcı):** `translate --l1 tr --limit 50 --yes` pilotu (para
harcar) — eski iki işin onay oranıyla karşılaştırılacak, en az 10 ham cevap
okunacak. Sonra `es`/`pt-BR`/`de` için büyütme kararı.

**v2 İş 3 gerçek koşusu YAPILDI + YANLIŞ RED DÜZELTİLDİ (2026-09-07).**
50 kelime × 4 dil koşuldu: tr 50/50, es 48/50, pt-BR 45/50, de 44/50. 13
reddedilen birimin ham cevabı okundu — **on üçünün de çevirisi DOĞRUYDU**;
sebep kalite değil, dil işaretçi kapısıydı (`a`/`in`/`no` her Romen/Germen
cümlesinde geçtiği için kapının "İngilizce kanıtı" yarısı her metinde
ateşleniyordu; L1 yarısı ise `IGNORECASE` kapalı ve dardı). Düzeltildi:
`ENGLISH_AMBIGUOUS` + genişletilmiş `LANG_MARKERS` + "model çevirmedi"
kararının kaynak metinle karşılaştırmaya taşınması. Ölçüm: 13 birimde 0
yanlış red, 561 onaylı metinde 0 regresyon, gerçek İngilizce tespiti %98,5.
**371 test yeşil.** Detay: plan §9.11b.

**SIRADA (kullanıcı):** `lexicon-card translate --l1 <es|pt-BR|de> --redo bad`
— 13 satır `llm_cache`den geleceği için **sıfır ödenen çağrı** (doğrulandı).
Sonra `tr`→`es`→`pt-BR`→`de` koşularını 50'den yukarı büyütme kararı.

**v2 İş 3 (çeviri katmanı) KOD BİTTİ (2026-09-06).**
`lexicon-card note` (kullanım notu, koşullu) ve `lexicon-card translate --l1
<kod>` (tanım+not+örnek, tek çağrıda) yeni komutları eklendi. **274 test
yeşil** (235'ten +39). Detay ve gerçek `v7` `--dry-run` ölçümleri: plan §9.11.
Sırada: kullanıcı `tr`→`es`→`pt-BR`→`de` sırasıyla `--limit 50 --dry-run` ile
başlayıp gerçek koşuyu çalıştıracak.

**Adım 7 (`review/` + `panel/`) BİTTİ — v1 KAPSAMI TAMAM.**
Yedi adımın hepsi yeşil, **178 test**. Elde duran: `data/dist/v7/en/` altında
291 öğelik sevkiyat (`verify` 16/16), insan düzeltme yolu (export → düzelt →
import → `data/human/` yedeği) ve `APP.panel`i olan her modülün sayfasını
getiren panel host'u.

Yürütme sırası: **1 → 3 → 2 → 4 → 5 → 6 → 7** (bkz. plan §7).
Bitenler: 1 (core), 3 (dictionary/build), 2 (jobs motoru), 4 (curriculum),
5 (lexicon_card + 300 kelimelik gerçek pilot), 6 (delivery), 7 (review+panel).

Sırada v1'de bir şey YOK. Elde hazır duran iki iş: pilotun **9 reddedilen
satırı** (`data/workspace/v7/en/review-export.jsonl` içinde, düzeltilmeyi
bekliyor) ve pilotu 300'den yukarı büyütmek (para harcar).

## Pilot ölçümü (gerçek para harcandı, plan §9.4)

300 kelime, `cloudflare:@cf/qwen/qwen3-30b-a3b-fp8`: **281 onay (%93,7)**,
19 red. Red sebeplerinin çoğu işlev sözcüğü (*a, to, for*) → gloss kelimenin
kendisini içeriyor. Ardından `--redo bad --model @cf/meta/llama-3.3-70b-instruct-fp8-fast`
(rank 20 < 40) **yalnızca o 19 satırı** yeniden işledi, 281'e dokunmadı:
10 onay, 9 hâlâ red. Depodaki son durum **291 onaylı**.

## Sevkiyatı üretme/doğrulama (sıfır LLM çağrısı)

```
polyvo delivery materialize --tag v7 --l2 en --l1 tr
polyvo delivery verify      --tag v7 --l2 en --l1 tr
```

`--l1 yok` verilirse `i18n_*.db` üretilmez. Kapı ihlalinde komut **hiçbir
dosya yazmadan** exit 1 döner; dist'te duran eski sevkiyat bozulmaz.

## Kesin unutulmaması gerekenler

- **Docstring kuralı aktif ve UYGULANDI.** Her dosyada Türkçe modül
  docstring'i, her fonksiyon/sınıfta kısa Türkçe docstring var (Protocol
  stub'ları hariç — onlarda satır-sonu yorum var). AST denetimi: 0 eksik.
  Yeni yazılan her dosyada bu BAŞTAN yapılmalı, sona bırakılmamalı.
- **Tek sorumluluk / küçük dosya kuralı aktif.** `core/jobs/` 19 dosya (en
  uzunu 118 satır), `curriculum/` 6 dosya (en uzunu ~110 satır). Bir dosya
  3+ iş yapmaya başlarsa böl.
- **Subagent kullanılmıyor.** Adımlar sıralı ve birbirine bağımlı (K1-K7
  gibi kararlar sonrakini şekillendiriyor); hepsi bu oturumda, tek başıma.
- Kullanıcı kodu şu an OKUMUYOR, hepsi bitince tek seferde bakacak — bu
  yüzden docstring/yapı netliği bu aşamada telafi edilemez, baştan doğru
  olmalı.
- **Testte gerçek `data/` dizinine ASLA yazılmaz.** İzolasyon deseni:
  `monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))` — tüm
  yol fonksiyonları `data_root()` üzerinden türediği için tek satır yeter
  (bkz. `tests/test_item_identity.py`).
- `docs/MIGRATION-PLAN.md` gerçek kaynak: §9 ilerleme, §9.0 adım/LLM parası
  tablosu, §9.1/§9.2/§9.3 ölçümler. Konuşma geçmişi değil, ORAYA yazılan kalıcı.

## Adım 4 (curriculum) — kısa özet

`src/polyvo/curriculum/`: `universe.py` (saf evren seçimi + **kapı** — boş/
yinelenen evrende `UniverseError`, hiçbir dosya yazılmaz) · `items.py`
(`core/jobs/identity.py` üstünde `item_id`/`sense_id` tahsisi, `(l2,headword,
pos)` zaten varsa YENİDEN TAHSİS ETMEZ — idempotentlik buradan gelir) ·
`schema.py` (`identity.sqlite`'a `items`/`senses` ekler, `workspace/<tag>/
<l2>/universe.sqlite` DDL'i, `source_config.json` kilit yazıcısı) ·
`app.py`+`commands/select_command.py` (`polyvo curriculum select`).
Kabul testi (`tests/test_item_identity.py`) hem workspace-silinir hem
identity.sqlite-de-silinir senaryosunu kapsıyor — ikisi de aynı kimliği
üretiyor (determinist sıralama sayesinde). Detaylı gerekçe: plan §9.3.

## İnsan düzeltme yolu (sıfır LLM çağrısı)

```
polyvo review export --tag v7 --l2 en --l1 tr --status rejected
#   -> data/workspace/v7/en/review-export.jsonl (düzenle: DOKUNMAYACAĞIN alanı SİL)
polyvo review import --file data/workspace/v7/en/review-export.jsonl --l1 tr
polyvo review restore          # data/human/ yedeğini depoya geri oynatır
```

Yazılan her satır **tier 0 / `source='human'`** olur; dosyada `tier`/`source`
yazsa bile OKUNMAZ. Sorunlu tek satır varsa komut **hiçbir satır yazmadan**
exit 1 döner. Depo silinip yeniden kurulsa da `restore` yedekten geri getirir.

## Panel (salt okunur)

```
polyvo panel serve --list      # sayfaları listeler, sunucu açmaz
polyvo panel serve             # http://127.0.0.1:8765/
```

Panel bir sayfa listesi TUTMAZ: `APP.panel`i olan her modül kendi sayfasını
getirir. Panelden yazma yoktur (`POST` 405) — düzeltmenin tek yolu `review`.
Ek bağımlılık yok, `http.server` stdlib.

## v2 hedefleri (henüz YAPILMADI)

Çok dilli L1, `modules/cloze` ve panelden insan düzeltmesi için görev tanımı:
`docs/V2-BRIEF.md` (kodda doğrulanmış 6 engel + 7 iş kalemi + verilen kararlar).
İlk dilim ikiye bölündü, ikisi de agent'a doğrudan verilecek biçimde yazıldı:

| dosya | ne | LLM parası | durum |
|---|---|---|---|
| `docs/V2-IS-1-VARIANT.md` | varyant ekseni; boş varyantta davranış bit bit aynı | yok | **BİTTİ** |
| `docs/V2-IS-2-COKDILLI-L1.md` | ikinci dil (`es`), sonra 50 kelimelik pilot | **evet** (pilot) | **BİTTİ** (pilot koşuldu) |
| `docs/V2-IS-2B-DIL-SIMETRISI.md` | `cards` L1 üretmeyi bırakır; 4 dil (`tr`/`es`/`pt-BR`/`de`) eşitlenir | yok | **BİTTİ** |
| `docs/V2-IS-3-CEVIRI.md` | tanım + kullanım notu + örnek cümle çevirisi, 4 dil; `usage_note` canlandırılır | **evet** | **KOD BİTTİ (2026-09-06), gerçek koşu kullanıcıda** |
| `docs/V2-IS-3B-GLOSS-CEVIRI-BIRLESIK.md` | `gloss`+`translate`'i tek çağrıda birleştir, `gloss` komutu kalkar | yok (pilot hariç) | **KOD BİTTİ (2026-09-11), pilot kullanıcıda** |
| `docs/V2-IS-4-CLOZE.md` | `modules/cloze`: anlam başına 3 çoktan seçmeli soru + çevirisi | **evet** | yazıldı, **sırada** |
| `docs/V2-IS-5-IPUCU-ACIKLAMA.md` | `cloze/rationale/`: soru başına ipucu + şık başına açıklama, çevirileriyle | **evet** | yazıldı (2026-09-07) |
| `docs/V2-IS-6-GRAMER.md` | `modules/grammar`: cümlenin göze çarpan gramer kuralları (kapalı katalog, `EN.<ALAN>.<KURAL>` id) — soru tipinden bağımsız | **evet** | yazıldı (2026-09-07) |

Dosya numaraları **teslimat sırasıdır**; `docs/V2-BRIEF.md` §2'deki "İş 5/6/7"
(review'i modülden bağımsızlaştırma · panelden düzeltme · çok dilli sevkiyat)
artık **İş 7 · İş 8 · İş 9**'dur.

En kritik bulgu: `JobContext.variant` ilan edilmiş ama tüketilmiyor; ikinci L1
koşusu bugün `skip_done` ile **tamamen atlanıyor** (`--l1 es` sıfır satır
üretir). İkinci tuzak: `pt-BR` tireli olduğu için `core/lang/get_rules` modülü
bulamaz ve dil **sessizce kuralsız** çalışır.

**İş 1 BİTTİ (2026-09-06).** Tek üretim yeri `core/jobs/keys.py`
(`compose_key`, `with_variant`) — motorun kendisi (`planner.py`, `loop.py`,
`policy.should_write`, `verdict.decide`, `lexicon_card/store.py`,
`curriculum/`) hiç değişmedi (diff'te görünmüyor), planlanan uyarı doğru
çıktı. Değişen iki dosya: `lexicon_card/job.py::load_units` (varyant
uygulanıyor, bugün `ctx.variant` hiç dolmadığı için no-op) ve
`engine/attempt.py` (deneme günlüğüne artık ham `stable_key` gidiyor,
`unit.data['stable_key']` üzerinden). Ölçüm: 178 eski test tek satır
değişmeden yeşil + 8 yeni test (`tests/test_jobs_keys.py`) = 186 test;
`polyvo lexicon-card cards --tag v7 --limit 1000 --dry-run --no-interactive`
çıktısı işten önce/sonra **birebir aynı**.

**İş 2 KODU BİTTİ, PİLOT SIRADA (2026-09-06).** Yeni `kind`:
`polyvo lexicon-card gloss --l1 <kod>` (`modules/lexicon_card/gloss/`,
`family="lexicon"` `kind="gloss_l1"`). Kart (`sense_cards`/`sense_examples`/
`item_phonetics`) **hiç yazılmaz** — yalnızca `sense_gloss_l1` + yeni kardeş
tablo `sense_gloss_l1_state` (tek tablo, `l1` sütunlu — dil başına ayrı
tablo YOK; `sense_gloss_l1`in şeması kilitli olduğu için "kötü satır"ı bu
kardeş tablo tanır, gerçek gloss varsa o her zaman kazanır). Prompt
(`gloss/prompt.py`) ödenmiş kartın `gloss_en`/örneklerini **bağlam** olarak
taşır — bu işin en büyük kalite riski buydu, testle çivilendi.

`pt-BR` tuzağı kapatıldı: `get_rules` modül adını normalize eder
(`pt-BR`→`pt_br`) ve artık yalnızca ARANAN modül yoksa sessiz düşer —
gerçekten bozuk bir dil modülü artık yutulmaz. Yeni kural modülleri
`es.py`/`pt_br.py`/`de.py`, her biri gerçek bir `check_form` kontrolü
taşıyor. `polyvo.toml`'a `l1 = ["tr", "es", "pt-BR", "de"]` eklendi.

**`tr` de eklendi (plan bunu istemiyordu, kullanıcı sonradan istedi).**
`tr.py` zaten vardı (v1'den) — yeni dosya gerekmedi, `gloss` işi baştan dil-
agnostik: `--l1 tr` **aynı koddan** geçiyor. `test_lang_rules.py`nin
parametrize listelerine `tr` eklendi; `test_lexicon_gloss.py`ye kartın
BAŞKA dille (`es`) üretildiği, `tr`nin hâlâ eksik olduğu senaryo eklendi —
`gloss --l1 tr` boşluğu aynı QA'yla dolduruyor, ikinci koşuda
`paid_calls = 0`. Gerçek `v7` üzerinde `gloss --l1 tr --dry-run` → **957
atlandı, 0 çağrı** (kart üretimiyle aynı anda zaten dolmuş).

Gerçek `v7` deposunda `sense_cards`: **957 approved / 43 rejected** (291
rakamı ilk küçük pilottan kalma, depo o zamandan beri büyüdü).
`gloss --l1 es --dry-run` → **957 işlenecek, 0 dış çağrı**; `cards --l1 tr
--limit 1000 --dry-run` → **0 ödenecek çağrı** (TR'ye zarar verilmedi).
Ölçüm: 186 eski test + 34 yeni (`test_lexicon_gloss.py` 20,
`test_lang_rules.py` 12, `test_review.py`'ye eklenen 2) = **220 test yeşil**;
AST docstring denetimi 0 eksik. Detay: plan §9.8.

**⚠️ Kapsam dışı bırakılan:** cümle çeşitliliği ("I eat cake" tekdüzeliği) —
kullanıcı kararıyla bu işte YAPILMADI, İş 4 (cloze) civarında ele alınacak.

**`es` pilotu KOŞULDU (2026-09-06): 50 birim, 47 onay / 3 red.** Redlerin
model cevapları okununca oran aslında **%100** çıktı — `to`→"a", `non`→"no"
üçü de doğru İspanyolcaydı, `l1_form`un dil işaretçi kapısı yanlış reddetti.
Tek kelimelik işlev sözcüğünde o sinyalin ayırt etme gücü sıfır. Yeniden
deneme aynı doğru cevabı üretip aynı duvara çarptığı için **50 birim 53
çağrıya mal oldu, 3 fazlanın hepsi kayıp.**

**Düzeltildi — aynı sınıftan ÜÇ hata (§6.7 ihlali: garanti edilemeyen
kontrol reddediyordu).** (1) Dil işaretçi kapısı artık yalnızca 3+ kelimelik
cevapta reddeder, kısada uyarır. (2) `tr.py::looks_conjugated` uyarıya
düşürüldü — ölçüldü: `kutu`/`kedi`/`garanti`/`kahvaltı` gibi sıradan isimler
`-dı/-ti/-tu` ile bittiği için 18 cevabın 16'sı yanlış alarmdı. (3)
`gloss_l1_kart_kopyasi`nın "kelimenin kendisi" kolu uyarıya düşürüldü —
`hotel`→"hotel" doğru cevaptır ve **pt-BR/de koşularını vuracaktı**. Fiil
mastarı kapısı ve kart tanımını kopyalama kapısı **reddetmeye devam ediyor**
(ikisi de ölçüldü, doğru çalışıyor). Yeni arayüz üyesi:
`core/lang/<kod>.SOFT_FORM_CODES`.

**Replay ölçümü (sıfır çağrı):** günlükteki L1 kaynaklı reddedilmiş
denemelerin `es`'te 6/6'sı, `tr`'de 64'ün 52'si yeni kapıdan geçiyor; kalan
12'nin hepsi gerçek hata (model fiile isim döndürmüş). **235 test yeşil.**
Detay: plan §9.10.

**⚠️ Pilotun 3 reddedilen satırı hâlâ kurtarılamadı.** `verdict.decide`in
rank kapısı "aynı model aynı cevabı üretir" varsayar; burada değişen model
değil KAPI olduğu için varsayım geçmiyor, o 3 satır `skip_outranked` duruyor.
Üç promptun üçü de `llm_cache`'te — `sense_gloss_l1_state`teki o 3 satır
silinirse yeniden koşu **sıfır kuruşa** onaylar. Motor kapsam dışı, satır
silme kullanıcı kararı.

**⚠️ Sırada — kullanıcı koşacak:** `gloss --l1 es --yes` (kalan 907),
ardından `pt-BR` ve `de`. Reddetme oranı §9.4 biçiminde raporlanacak.
Oran kötüyse prompt/QA düzeltilip koşu büyütülmeyecek. **`delivery
materialize --l1 es` İş 7 bitene kadar KOŞULMASIN** — `_dist_meta.json` tek
L1 tanır, ikinci dil ilk dilin manifest kaydını ezer, `verify --l1 tr` düşer.

**İş 2b BİTTİ (2026-09-06).** Asimetri kapandı: `cards` artık **yalnızca
İngilizce kart** üretir, ana dil karşılığı — Türkçe dahil — **yalnızca**
`gloss` koşusundan gelir. `sense_gloss_l1`in tek yazıcısı `gloss/store.py`;
bu kural kaynak denetimi testiyle çivilendi
(`test_sense_gloss_l1in_tek_yazicisi_gloss_deposudur`). `tr` için ayrı kod
yolu / ayrı bayrak / ayrı istisna kalmadı — yeni dil eklemek = `polyvo.toml`
+ `core/lang/<kod>.py` + bir koşu.

**Ölçülen para kaybı (işin sebebi).** 43 reddedilmiş kartın sebep dökümü:
`gloss_en_kelimenin_kendisini_iceriyor` 19 · **`looks_conjugated` 14** ·
**`l1_ceviri_yapilmamis` 4** · **`verb_missing_infinitive` 3** ·
`ornek_cumle_cok_kisa` 3. Yani **43 reddin 21'i (%49) yalnızca Türkçe
karşılık yüzünden çöpe atılmış, ödenmiş İngilizce kart.**

**Ölçüm (sıfır LLM parası, hepsi `--dry-run`):** `cards --tag v7 --limit 1000
--dry-run` çıktısı işten önce/sonra **birebir aynı** (0 ödenecek çağrı; prompt
v2'ye çıktı ama `verdict.decide` `prompt_hash`e bakmadığı için hiçbir satır
yeniden tetiklenmedi) · `gloss --l1 tr --dry-run` → **0 ödenecek çağrı** ·
`gloss --l1 es --dry-run` → **957 işlenecek**. Depo sayımları değişmedi:
957/43 kart, 957 `tr` gloss, `prompt_hash` hâlâ 1000 satırda `v1`.
**222 test yeşil** (220 + 4 yeni − 2 taşınan). Detay: plan §9.9.

`cards`ın `--l1` bayrağı **kaldırıldı** (kullanıcı kararı): `cards --l1 de` →
`error: unrecognized arguments`, exit 2. Sessiz yok sayma yok.

**⚠️ Elde duran, kullanıcı kararı bekleyen:** ayırmadan sonra yalnızca L1
yüzünden reddedilmiş kartlar artık geçebilir. `--redo bad --dry-run` aday
sayısı rank kapısına bağlı: varsayılan qwen (rank 40) ile **0**,
`llama-3.3-70b` (rank 20) ile **34**, `gemini-2.5-pro` (rank 10) ile **43**.
Koşulmadı — para harcar, karar kullanıcının.

**İş 2b BİTTİ + `es` pilotu koşuldu (2026-09-06).** `cards` artık yalnızca
İngilizce kart üretir; `sense_gloss_l1`in tek yazıcısı `gloss/store.py`.
Pilot: 50 birim, 47 onay / 3 red — **ama üç red de YANLIŞ REDDİ**
(`to`→"a", `non`→"no" doğru İspanyolcaydı). Sebep: dil-işaretçi kapısı tek
kelimelik işlev sözcüğünde ayırt edemiyor, `a`/`no` hem İngilizce hem
İspanyolca. Üç birim için 6 çağrı ödendi, hepsi kayıp — yeniden deneme aynı
doğru cevabı üretip aynı duvara çarpıyor. Düzeltildi: `l1_form.check` artık
`FormResult(reject, warnings)` döndürüyor, dil kapısı yalnızca uzun cevapta
reddediyor (`MIN_WORDS_FOR_LANG_GATE`). **Ders: orana bakmak yetmiyor,
`job_attempts.raw_response` örneklenerek okunmalı.** 235 test yeşil.

**Depo ölçümü (2026-09-06):** `sense_cards` 957 approved / 43 rejected ·
`sense_examples` 1914 · `sense_gloss_l1` tr 957, es 50 · `item_level.cefr`
840/1000 dolu (160'ında YOK — cloze'un CEFR kapısı bunu red sebebi
saymamalı) · **`usage_note` 957 kartın yalnızca 4'ünde dolu** (sebep: kart
prompt'unda `usage_note` için kural satırı yok, alan "isteğe bağlı" diye
geçiyor — İş 3 bunu düzeltir).

## İş 3 (çeviri katmanı) — kısa özet

`src/polyvo/modules/lexicon_card/` iki yeni alt paket aldı, ikisi de `gloss/`
deseninin ikizi: `note/` (`units`/`prompt`/`qa`/`store`/`job`, `kind=
"usage_note"`, dile bağlı DEĞİL) ve `translate/` (aynı beşli, `kind=
"translation"`, `variant=l1`). Ortak baglam sorgusu `card_context.py`de,
"model çevirmeyip İngilizce mi döndürdü" sinyali `l1_language.py`de tek
yerde toplandı (`l1_form.py` ve `translate/qa.py` aynı fonksiyonu, FARKLI
eşikle çağırır). 4 yeni tablo (`sense_usage_note`, `sense_translation`,
`sense_translation_examples`, `sense_gloss_l1_note`) — dil bir SÜTUN,
mevcut hiçbir tablo/şema değişmedi.

`usage_note` karttan çıktı (`prompt_version` v2→v3): kart artık bu alanı
İSTEMİYOR, tek üreticisi `note/store.py`. `gloss`e küçük bir istisna eklendi
(`gloss_note`, madde 9): ana dilde temiz karşılık yoksa kısa not, tek
ölçülebilir kapı "not karşılığın kendisiyle neredeyse aynıysa red" (`gloss`
`prompt_version` v1→v2). `review/targets.py` yeni: hangi düzeltilebilir
alanın hangi tabloya gittiğinin TEK haritası; `apply.py` bunu okur, kendi
tablo bilgisi taşımaz. Detay ve gerçek `v7` ölçümleri: plan §9.11.

**Kullanıcı kararları:** komut adları `note`/`translate`; `sense_cards.
usage_note`taki eski 4 satır migrate EDİLMEDİ, yeni koşuda sıfırdan üretilir.

## v2'ye ertelenenler

`modules/cloze`, `modules/paragraph`, `modules/reading`, `curriculum/sets`,
embedding katmanı, panelden düzeltme (plan §7 "Ertelendi"). Her biri mimariye
*bir klasör* olarak girmeli, mevcut hiçbir dosyayı düzenletmemeli.

## Adım 6 (delivery) — kısa özet

`src/polyvo/delivery/`: `collect.py` (evren + ödenmiş depo + kimlik → satırlar,
karar vermez) · `gate.py` (**sevk kapısı**: olgu ≠ ifade — IPA/CEFR/frekans
her zaman gider, metin yalnızca `llm`/`human`/`shippable=True` kaynaktan) ·
`materialize.py` (topla → kapı → `.staging/`'e yaz → `os.replace`) ·
`snapshot.py` (`_dist_meta.json`: satır sayıları + sha256) · `verify/checks.py`
(üretilmiş dosyalara dışarıdan bakan 16 kontrol) · `schema.py` + `commands/` +
`app.py`. Sevkiyat dosyaları **zaman damgası taşımaz** → aynı girdi aynı
baytları üretir. Detay: plan §9.5.

## Adım 7 (review + panel) — kısa özet

`src/polyvo/review/` (katman 4): `record.py` (düzeltmenin biçimi — hangi alan
okunur, hangisi OKUNMAZ) · `export.py` (depodan JSONL çıkarır; içeriği olmayan
alanı hiç yazmaz, "bulunmayan alan dokunulmaz" kuralı yüzünden) · `apply.py`
(tek yazma yeri: doğrula → `core/jobs/store/policy.py` kapısı → tek
transaction; `tier=0`/`source='human'` BURADA sabittir) · `backup.py`
(`data/human/corrections.jsonl`, ekleme kipinde). Kimlik üretmez: depoda
karşılığı olmayan `stable_key` düzeltilemez.

`src/polyvo/panel/` (katman 5): `pages.py` (app keşfinden sayfalar, önek
çakışması hata) · `dispatch.py` (SAF yol eşlemesi, soket yok — testler burayı
çağırır) · `shell.py` (kabuk; nav sayfalardan türer) · `http.py`/`server.py`.
Sayfa sözleşmesi ördek tiplemesi: modül panel'i import ETMEZ, sadece
`router(path, query) -> (status, tip, gövde)` döner. `modules/lexicon_card/
panel/` router'ını bu adımda getirdi (`queries.py` + `views.py`); host'ta tek
satır değişmedi. Router'ı olmayan sayfa 501, patlayan router 500 — panel
düşmez. Detay: plan §9.6.

## Yorum/docstring sadeleştirme geçişi (2026-09-06)

Kullanıcı isteği: her dosya/fonksiyon ÇOK KISA açıklasın, eski uzun
gerekçe/tarih paragrafları silinsin. Tüm `src/polyvo/` tarandı, modül
docstring'leri ve uzun fonksiyon docstring'leri tek-iki cümleye indirildi
(numaralı kurallar/tablolar — redo matrisi, yazma kapısı kuralları gibi —
korundu, onlar bilgi kaybı olur). Ayrıca **`core/cli/args.py` silindi**:
hiç kullanılmayan ölü kod (Adım 1'den kalma, gerçek komutlar kendi
`add_args`'ını tanımlıyor). AST denetimi hâlâ 0 eksik, 115 test yeşil.

## Açık uçlar

- Lawyer'a sorulacak 2 madde hâlâ açık (`docs/SOURCES.md` §5): NGSL CC BY-SA
  kelime listesine bulaşıyor mu; CC BY-SA kanıtla üretilen LLM çıktısı türev
  eser mi. Ticari lansmandan önce.

## Adım 5 (lexicon_card) — kısa özet

`src/polyvo/modules/lexicon_card/` (12 dosya, 653 satır): `units.py` (evren →
`Unit`) · `seed.py` (kanıtı birime bağlar; `shippable=False` metin YALNIZCA
prompt'a, asla depoya) · `prompt.py` · `qa.py` (içerik kapısı) · `store.py`
(`ArtifactStore` alt sınıfı, kartın tüm parçaları tek transaction) ·
`schema.py` (`data/stores/lexicon.sqlite`) · `job.py` (`Job`'ın 3 metodu) ·
`commands/cards_command.py` · `app.py` + `panel/`.

Motorun kendisi (plan, onay, bütçe, deneme günlüğü, yazma kapısı) hiç
kopyalanmadı — Adım 2'nin `core/jobs`'ı olduğu gibi kullanıldı; bu adımda
`core/jobs/cli_args.py` ve `core/llm/cli.py` ilk kez gerçek bir tüketici
buldu. `--pace-delay` iki yerde tanımlıydı, motor lehine tekilleştirildi.
Detay + kabul ölçümleri: plan §9.4.

## İş 4 (cloze) — kısa özet

`src/polyvo/modules/cloze/` (31 dosya): `units.py` (yalnızca
`lexicon_card.public` üstünden okur) · `difficulty.py` (prompt ile QA'nın TEK
ortak kaynağı: kolay/orta/zor bandı) · `scene.py` (deterministik sahne
kısıtı — saatten/rastgeleden türemez) · `cefr.py` (evren CEFR sözlüğü) ·
`prompt.py` (anlam başına TEK çağrı, üç soru) · `qa/` (5 dosya: biçim,
boşluk, çeldirici, seviye, tekdüzelik) · `store.py` · `job.py` ·
`translate/` (ayrı koşu, `variant=l1`) · `commands/` · `panel/` · `app.py`.

Depo: `data/stores/cloze.sqlite`, 5 tablo. Şıklar İngilizce ve çevrilmez →
beşinci dil = yeni satır, şema değişmez.

**Mimarinin sınavı geçildi:** yeni içerik türü **bir klasör** olarak girdi.
`core/`, `curriculum/`, `delivery/`, `panel/` host'u ve `lexicon_card`ın
üretim dosyaları tek satır değişmedi. Dokunulan mevcut yer yalnızca insan
düzeltme yolu (`review/`, kabul ölçütü) ve yeni `lexicon_card/public.py`
okuma yüzeyi. `test_layering` artık modül sınırını gerçekten ölçüyor:
modüller-arası import yalnızca `public` yüzeyinden, `lexicon_card → cloze`
her koşulda yasak.

**Ölçülmeyen şey uyarıdır, red değil:** gömme katmanı olmadığı için
"çeldirici gerçekten uymuyor mu" sorusu mekanik olarak yanıtlanamaz; bu
kontrol her onaylı pakete `celdiricinin_uymadigi_dogrulanamadi` uyarısı
yazar. 338 test yeşil, AST docstring denetimi 0 eksik. Gerçek koşu
yapılmadı (para). Detay + ölçümler: plan §9.12.
