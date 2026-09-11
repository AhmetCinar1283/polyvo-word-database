# Polyvo CLI komutları

Komutlar **çalıştırılma sırasıyla** yazıldı. `$` işareti komutun LLM parası
harcadığını gösterir.

```
polyvo apps           # bütün app'ler ve komutları
polyvo where          # çözülen yollar + aktif tag
polyvo <app> <komut> --help
```

---

## Para harcayan komutların ortak bayrakları

`$` işaretli her komut aşağıdakilerin hepsini alır:

| bayrak | ne yapar |
|---|---|
| `--tag T` | hangi veri başlığında çalışılacağı (ör. `v7`); verilmezse `polyvo.toml` |
| `--l2 KOD` | hedef dil (varsayılan `polyvo.toml` → `en`) |
| `--limit N` | yalnızca ilk N birimi işle — **pilot** için |
| `--dry-run` | hiçbir çağrı yapmadan kaç çağrı / ne kadar tutacağını söyle ve çık |
| `--yes` | "ödeyeyim mi?" sorusunu atla |
| `--max-new N` | en fazla N **yeni** (ödenen) çağrı yap, sonra dur |
| `--pace-delay SN` | her çağrıdan sonra SN saniye bekle (hız limiti) |
| `--redo none` | varsayılan: dolu satırı atla, yalnızca eksikleri üret |
| `--redo bad` | eksikleri üret **ve** reddedilmiş satırları yeniden dene |
| `--redo only-bad` | yalnızca reddedilmiş satırları yeniden dene |
| `--force self` | **rank kapısını** gevşet: aynı seviyedeki modelin reddettiği satırı da yeniden dene ("elimdeki en iyisi bu, yine de dene") |
| `--force all` | rank kapısını tamamen aç: daha önce **daha iyi** bir modelin reddettiği satırı da dene (en gevşek, en pahalı) |
| `--provider` / `--model` | sağlayıcı ve model (verilmezse sorar) |
| `--base-url` · `--api-key` · `--max-retries N` | sağlayıcı ayarları (anahtar normalde `.env`'den) |
| `--no-interactive` | hiçbir şey sorma, varsayılanı kullan |

**Kullanım kalıbı** (her `$` komut için aynı):

```
polyvo <app> <komut> --tag v7 --dry-run            # 1. ne kadar tutar?
polyvo <app> <komut> --tag v7 --limit 50 --yes     # 2. pilot — sonucu gözle oku
polyvo <app> <komut> --tag v7 --yes                # 3. hepsi
```

Bilmen gerekenler:
- **İkinci koşu bedava.** Onaylı satır bir daha üretilmez. Yarıda kesilen bir
  koşuyu aynı komutla sürdürebilirsin.
- **Reddedilen satır kendiliğinden yeniden denenmez — rank kapısı yüzünden.**
  Aynı ya da zayıf modelle reddedilmiş satır `--redo bad` versen bile
  atlanır (`skip_outranked`): aynı model + aynı prompt = önbellekten aynı
  cevap gelir, para boşa gider — **QA kuralları sonradan gevşetilse bile**
  bu geçerlidir. İki çıkışı var:
  - Daha iyi bir modelle dene: `--redo bad --model ...` (rank kapısı
    kendiliğinden açılır, `--force` gerekmez).
  - Aynı modelle bilerek zorla: `--force self` (yalnızca kendi seviyesini
    açar) ya da `--force all` (daha önce daha iyi bir modelin bile
    reddettiği satırı dener — en gevşek, en pahalı).
- **`--force` iki aşamalı çalışır.** (1) Onay isteminden ÖNCE, önbellekteki
  eski cevap bugünkü QA'dan **bedava** geçirilir; geçenler çağrı yapılmadan
  düzeltilir ve kalıcıdır — onay isteminde "H" desen bile (`--dry-run`'da
  yalnızca raporlanır, yazılmaz). (2) Hâlâ reddedilen satırlar onaylarsan
  MODELE gider, önbellek bilerek ATLANIR (aynı model olsa bile taze cevap
  alınır) ve o çağrı **ödenir**. Yani `QA'yı düzelttikten sonra --redo bad
  --force self` çoğu zaman hiç ödeme yapmadan (yalnızca 1. aşamayla) satırı
  kurtarır.
- **Onaylı satıra ve insan düzeltmesine hiçbir bayrak (ne `--redo` ne
  `--force`) dokunmaz.** İkisi de yalnızca "bu satır DENENİR mi" sorusunu
  genişletir, "YAZILIR mı" sorusuna karışmaz — o karar ayrı bir kapıdadır.

---

## 0. Kurulum (bir kez)

- `.env` → sağlayıcı API anahtarı (repoya girmez).
- `polyvo.toml` → `l2 = "en"`, `l1 = ["tr","es","pt-BR","de"]`, `target_size`.

## 1. Sözlük — `dictionary` (ücretsiz)

```
polyvo dictionary download
polyvo dictionary build --tag v7
```

- **download**: ham sözlük kaynaklarını `data/raw/`'a indirir. `--force` ile
  mevcut dosyalar yeniden indirilir.
- **build**: aday kelime havuzunu ve CEFR sözlüğünü kurar
  (`data/builds/<tag>/01_lexicon/`). Bayraklar: `--tag`, `--tier N`
  (evren merdiveninde kaçıncı basamağa kadar).

## 2. Kelime evreni — `curriculum select` (ücretsiz)

```
polyvo curriculum select --tag v7 --target-size 9000
```

Hangi kelimelerin/anlamların işleneceğini seçer ve her birine **kalıcı
kimlik** (`sense_id`) verir. Bu kimlik bir daha değişmez. Bayraklar: `--tag`,
`--l2`, `--target-size N`.

## 3. İngilizce kart — `lexicon-card cards` $

Her anlam için İngilizce tanım (`gloss_en`), register ve 2 örnek cümle üretir.
Ana dil üretmez, `--l1` almaz.
Bayraklar: ortak bayraklar.

## 4. Kullanım notu — `lexicon-card note` $

Kelimenin nasıl kullanıldığına dair kısa İngilizce not. Söylenecek bir şey
yoksa boş kalır, bu bir hata sayılmaz. Ana dil üretmez.
Bayraklar: ortak bayraklar.

## 5. Ana dil karşılığı + çevirisi — `lexicon-card translate --l1 KOD` $

Anlam başına dil başına **tek çağrıda** hem kelimenin ana dildeki
**karşılığını** (flashcard'ın arka yüzündeki kısa cevap, `bank` → `banka`,
temiz karşılık yoksa kısa not) hem kartın **metin çevirisini** üretir
(İngilizce tanım, kullanım notu, 2 örnek cümle). Karşılık ve çeviri aynı
çağrıdan geldiği için terim tutarlıdır. Depoda o dilde zaten bir karşılık
varsa model onu sabit terim olarak kullanır, üzerine yazmaz. Dil başına ayrı
koşulur: `tr`, sonra `es`, `pt-BR`, `de`.
Bayraklar: ortak bayraklar + `--l1`.

## 6. Cloze soruları — `cloze generate` $

Onaylı kartı olan her anlam için 3 boşluk doldurma sorusu (kolay, orta, zor)
üretir, her soruda 4 şık vardır.
Bayraklar: ortak bayraklar.

> Pilotta en az 10 cevabı oku: cümle mantıklı mı, yanlış şıklar gerçekten
> cümleye uymuyor mu? Bunu QA ölçemiyor, yalnızca uyarı yazıyor.
> Görmek için: `polyvo panel serve` → `/cloze`.

## 7. Cloze çevirisi — `cloze translate --l1 KOD` $

Onaylı cloze cümlelerini ana dile çevirir. Şıklar çevrilmez; bu bir
İngilizce alıştırması. Bayraklar: ortak bayraklar + `--l1`.

## 8. Cloze ipucu + açıklama — `cloze rationale` $

Onaylı her soru için bir ipucu ve her şık için neden doğru/yanlış olduğunu
anlatan kısa bir açıklama üretir (İngilizce). Bayraklar: ortak bayraklar.

## 9. İpucu çevirisi — `cloze rationale-translate --l1 KOD` $

8. adımın çıktısını ana dile çevirir. Bayraklar: ortak bayraklar + `--l1`.

## 10. Gramer analizi — `grammar analyze` $

Onaylı cloze cümlelerinin her birinde en göze çarpan gramer kurallarını bulur
(en çok 3 kural, sıralı). Kurallar sabit bir katalogdan seçilir
(`EN.TENSE.PAST_SIMPLE` gibi).
Bayraklar: ortak bayraklar + `--propose-only`.

```
polyvo grammar analyze --tag v7 --limit 50 --propose-only --yes   # önce: yalnızca katalog adayı topla
polyvo grammar analyze --tag v7 --limit 50 --yes                  # sonra: pilot
```

`--propose-only` kural yazmaz, yalnızca katalogda karşılığı olmayan yapıları
aday olarak listeler. Aday çoksa önce katalogu büyüt
(`modules/grammar/catalog/rules.py`), sonra koşuyu büyüt.

## 11. Gramer çevirisi — `grammar translate` / `grammar catalog-translate` $

- **translate --l1 KOD**: her cümleye yazılmış kural notlarını çevirir.
- **catalog-translate --l1 KOD**: katalogdaki her kuralın adını ve kısa
  açıklamasını çevirir. Tag'e bağlı değil; dil başına yaklaşık 80 çağrı.

Kural kimliği (`rule_id`) ve cümledeki tetikleyici kelimeler (`trigger`)
çevrilmez. Bayraklar: ortak bayraklar + `--l1`.

## İnsan düzeltmesi — `review` (ücretsiz, her adımdan sonra)

```
polyvo review export --tag v7 --status rejected --out duzeltme.jsonl
#   dosyayı aç, düzelt; DOKUNMAK İSTEMEDİĞİN ALANI SİL
polyvo review import --file duzeltme.jsonl
polyvo review restore
```

- **export**: depodaki satırları JSONL dosyasına yazar. Bayraklar: `--tag`,
  `--l2`, `--l1` (`yok` → ana dil alanları çıkmaz), `--status
  {approved,rejected,all}`, `--limit N`, `--out DOSYA`.
- **import**: düzeltilmiş dosyayı depoya yazar. Yazılan satır "insan kararı"
  olur ve hiçbir model bir daha üzerine yazamaz. Tek bir satır bozuksa hiçbir
  satır yazılmaz. Bayraklar: `--file` (zorunlu), `--l1`, `--skip-unknown`
  (depoda olmayan anahtarları atla), `--no-backup` (yedek alma; önerilmez).
- **restore**: `data/human/` altındaki düzeltme yedeğini depoya geri yazar.
  Depoyu silip yeniden kurduğunda kullanılır. Bayrak: `--l1`.

> ⚠️ Dosyayı düzeltmeden import etme. `--status rejected` dosyasında içerik
> olmadığı için import hiçbir şey yazmaz. Ama `approved`/`all` dosyasını
> olduğu gibi import edersen **her satır insan kararı olur** ve modeller o
> satırı bir daha üretemez. Yalnızca düzelttiğin satırları bırak.

## Sevkiyat — `delivery` (ücretsiz)

```
polyvo delivery materialize --tag v7 --l1 tr
polyvo delivery verify      --tag v7 --l1 tr
```

- **materialize**: uygulamanın kullanacağı veritabanı dosyalarını üretir
  (`data/dist/<tag>/en/`: `core.db`, `en.db`, `i18n_tr.db`). Bir kural
  ihlali varsa hiçbir dosya yazılmaz.
- **verify**: üretilen dosyaları dışarıdan kontrol eder.
- Bayraklar (ikisinde de): `--tag`, `--l2`, `--l1` (`yok` → dil dosyası yok).

> ⚠️ Şimdilik yalnızca `--l1 tr` kullan: ikinci dil ilkinin kaydını ezer.
> ⚠️ Cloze ve grammar henüz sevkiyata girmiyor.

## Panel — `panel serve` (ücretsiz, salt okunur)

```
polyvo panel serve --list     # sayfaları listele
polyvo panel serve            # http://127.0.0.1:8765/
```

Kartları, cloze sorularını ve gramer kurallarını tarayıcıda gösterir
(`/lexicon-card`, `/cloze`, `/grammar`). Panelden düzeltme yapılamaz, onun
yolu `review`.
Bayraklar: `--host`, `--port`, `--list`.

---

## Sıra ve bağımlılık

```
1  dictionary download → build
2  curriculum select
3  lexicon-card cards                  $
4  lexicon-card note                   $   ┐ 3'ten sonra, birbirinden bağımsız
5  lexicon-card translate  --l1 × 4    $   ┘
6  cloze generate                      $   3'ten sonra
7  cloze translate         --l1 × 4    $   6'dan sonra
8  cloze rationale                     $   6'dan sonra
9  cloze rationale-translate --l1 × 4  $   8'den sonra
10 grammar analyze                     $   6'dan sonra
11 grammar translate / catalog-translate --l1 × 4   $   10'dan sonra
   review export/import                    istediğin her adımdan sonra
   delivery materialize + verify           en son
   panel serve                             istediğin zaman
```
