# Durum

Compact/yeni oturum sonrası önce bunu, sonra `docs/MIGRATION-PLAN.md` §9'u oku.
Her adım bitince bu dosya güncellenir — kalıcı olmayan "sohbet hafızası" değil,
buradaki bilgi.

## Şu an neredeyiz

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
