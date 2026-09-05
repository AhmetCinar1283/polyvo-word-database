# Polyvo — word-databases

Acik lisansli Ingilizce kelime verisinden dil ogrenme icerigi ureten hat:
sozluk insasi -> anlamsal katman -> mufredat (kelime evreni, ogretim setleri)
-> LLM uretimi (anlam karti, cloze, paragraf, sorular, ceviri) -> sevkiyat.

Bu depo, onceki `word-database` projesinin **yeniden yapilandirilmis** halidir.
Tasima plani ve donmus kapsam: [`docs/MIGRATION-PLAN.md`](docs/MIGRATION-PLAN.md).

## Kurulum

```bash
py -3.12 -m venv venv
venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env        # anahtarlari doldurun
polyvo init                   # data/ altindaki global dizinleri olusturur
polyvo where                  # cozulen yollari ve aktif tag'i gosterir
```

## Mimari — 4 katman, tek yonlu bagimlilik

```
katman 3  delivery    materialize · snapshot · verify · panel host
              ^ sadece okur
katman 2b modules     LLM isleri; her biri bagimsiz "app"
              ^
katman 2a curriculum  evren · kimlik · item · set · gruplama — SIFIR LLM
              ^
katman 1  dictionary  build · enrich · embedding — snapshot'li veri hatti
              ^
katman 0  core        llm · sqlite · paths · config · dil · metin QA · jobs motoru
```

**Alt katman ust katmani import edemez.** Bu bir yorum degil, bir testtir:
`tests/test_layering.py`. Ayni test iki app'in birbirini import etmesini de
engeller — ortak ihtiyac varsa asagi, `core/`'a iner.

## Iki sinif veri, ve neden ayri duruyorlar

| dizin | anahtari | yeniden uretilebilir mi |
|---|---|---|
| `data/raw/` `data/cache/` | kaynak dosya · `sha256(model+prompt)` | evet — para/zaman odeyerek |
| `data/stores/` `data/human/` | semantik kimlik (kelime, synset, stable_key) | **hayir** — kimlik + insan kararlari |
| `data/builds/<tag>/` `data/workspace/<tag>/` `data/dist/<tag>/` | bir build'in izdusumu | evet — bedava |

Ilk iki grup TAG'DEN BAGIMSIZ; tag'e gore bolunselerdi her yeni veri basligi
her embedding/LLM kararini yeniden odetirdi. Ucuncu grup TAG'E GORE COGUL;
tek yuvali olsaydi ikinci bir veri basligi birincisinin ciktisini sessizce
ezerdi.

## Komutlar

```bash
polyvo apps        # yuklu app'ler ve komutlari (merkezi liste yoktur, kesfedilir)
polyvo where       # yollar + aktif tag
polyvo init        # global veri dizinleri
```

App'ler katmanlar tasindikca burada kendiliginden gorunur — yeni bir is
eklemek bir klasor eklemektir, mevcut hicbir dosya duzenlenmez.

## Test

```bash
venv\Scripts\python.exe -m pytest -q
```
