# Açık kaynak seçimi ve lisans analizi

Durum: **öneri — onay bekliyor.** Onaylanınca Adım 3'ün (`dictionary/`) girdisi olur.
Tarih: 2026-09-05.

> **Uyarı:** aşağıdaki lisans okumaları mühendislik düzeyindedir, hukuki görüş
> değildir. Ticari lansmandan önce §5'teki iki maddenin bir avukata sorulması
> gerekir; geri kalanı için risk düşük ve kaynaklar zaten açıkça izin veriyor.

---

## 1. "Kelimeler herkesin" — nerede doğru, nerede değil

Bu soru kaynak seçimini belirlediği için önce cevaplanmalı.

**Doğru olan kısım.** Tek bir kelime telif konusu değildir. `abandon` kimsenin
malı değil; anlamı da bir olgudur. ABD'de bu *Feist v. Rural Telephone* (1991)
ile net: olgular telifli olamaz, "hiçbir biçim ne kadar özgün olursa olsun
olguları özgün yapmaz." Bir kelimenin frekansı, POS'u, IPA'sı da aynı şekilde
olgudur.

**Doğru olmayan kısım — ve ticari ürün için kritik olan bu.** Bir *liste*,
tek tek kelimelerden farklı bir şeydir ve iki ayrı hukuki katman onu koruyabilir:

1. **Seçim ve düzenlemede telif (Feist'in ikinci yarısı).** Alfabetik sıralama
   korunmaz — yaratıcılık yok. Ama "hangi 3.000 kelime ve hangi seviyede"
   sorusu editoryal karardır. Oxford 3000 ve Cambridge English Vocabulary
   Profile tam olarak budur: uzman kurulunun seçimi. Koruma "ince"dir ama
   vardır ve sadece seçimi kapsar, kelimeleri değil.

2. **Sui generis veri tabanı hakkı — asıl engel bu.** Yaratıcılıktan tamamen
   bağımsızdır; "içeriğin elde edilmesine, doğrulanmasına veya sunumuna esaslı
   yatırım" yapılmışsa doğar. AB'de 96/9/EC direktifi, Brexit sonrası
   İngiltere'de CDPA 1988, **ve Türkiye'de FSEK Ek Madde 8** ile geçerlidir.
   Hakkın kapsamı: içeriğin *önemli bir kısmının* başka ortama aktarılması
   (extraction) veya yeniden kullanımı.

**Sonuç:** "Oxford 3000'in kelime listesini alalım, çeviriyi ve örneği zaten
LLM ile kendimiz yazacağız" — bu, sui generis hak açısından **yine de esaslı
kısım aktarımıdır.** Kelimeler serbest; yatırımın kendisi olan *liste* değil.
Türkiye'de yerleşik bir ticari ürün için bu, göz ardı edilecek bir risk değil.

**Ama bu tartışma pratikte gereksiz** — çünkü ihtiyacımız olan şeyin açık
lisanslısı var ve pedagojik olarak en az onlar kadar iyi. Kapalı listelere
girmeye gerek yok (§2).

---

## 2. Seçilen kaynaklar

Hepsi ticari kullanıma **açıkça** izin veriyor. "İzin var mı" belirsiz olan
hiçbir kaynak listede yok.

| kaynak | ne alınır | lisans | ticari |
|---|---|---|---|
| **NGSL 2.848** (+Sup) | **kelime evreni** çekirdeği | CC BY-SA 4.0 | ✅ site açıkça "including commercial use" diyor |
| **New Dolch 875** | çocuk/temel çekirdek | CC BY-SA 4.0 | ✅ |
| **CEFR-J Vocabulary Profile v1.5** | **evren + CEFR seviyesi** A1–B2 — 7.799 satır, 6.863 lemma, `(headword, pos, CEFR)` | özel izin: "research and commercial purposes with no charge, provided that you cite the dataset properly" | ✅ atıf şartlı |
| **Octanove Vocabulary Profile C1/C2** | evren + CEFR C1–C2 — 2.136 satır, 1.955 lemma | CC BY-SA 4.0 | ✅ |
| **NAWL 959 · TSL 1.259 · BSL 1.754** | evren genişletme (akademik / TOEIC / iş) | CC BY-SA 4.0 | ✅ |
| **Nation BNC/COCA 25k bantları** | evreni 10k üstüne çıkarmak için — yalnızca gerekli bant kadar | CC BY-SA 4.0 (VUW resmi sayfası) | ✅ bkz. §2.1 |
| **wordfreq** (Python) | **frekans** (Zipf skoru → sıra) | kod MIT; veri CC kaynaklardan | ✅ |
| **Open English WordNet 2024** | **lemma + POS + anlam sayısı ipucu** | **CC BY 4.0** (ShareAlike YOK) | ✅ |
| **ipa-dict `en_US`** (CMUdict türevi) | **IPA** | **MIT** | ✅ |
| **Tatoeba** (en–tr çiftleri) | LLM'e verilecek örnek **kanıtı** | CC BY 2.0 FR | ✅ atıf şartlı |
| **Kaikki.org / Wiktionary (en)** | LLM'e verilecek tanım/çekim **kanıtı** | CC BY-SA 4.0 + GFDL | ⚠️ bkz. §4 — yalnızca kanıt, asla sevk |
| `content/en` (legacy_dist) | geçici köprü kanıtı (K4) | kendi verimiz | ✅ |

### Alınmayanlar ve nedeni

| kaynak | neden hayır |
|---|---|
| **Oxford 3000 / 5000** | Kapalı. Liste seçimi editoryal; sui generis hak Türkiye dahil geçerli. NGSL aynı işi görüyor. |
| **Cambridge English Vocabulary Profile (EVP)** | Kapalı. Cambridge veri lisanslamayı ayrı sözleşmeyle satıyor; API şartları ticari kullanımı açıkça yasaklıyor. CEFR-J + Octanove ikilisi A1–C2'yi kapatıyor. |
| **ipa-dict `en_UK`** | **GPL 3.0.** Kapalı bir ürünün veri dosyasına GPL bulaştırmanın anlamı yok. Sadece `en_US` (MIT) alınır; İngiliz telaffuzu gerekirse ayrı ve MIT/BSD bir kaynak aranır. |
| **SUBTLEX-US doğrudan** | Gereksiz — wordfreq zaten SUBTLEX'i içeriyor ve tek arayüz veriyor. Ayrıca altyazı frekansı tek başına *öğretim* sırası vermiyor (bugünkü DB'nin hatası tam olarak buydu, bkz. MIGRATION-PLAN §0.3). |
| **EFLLex** (UCLouvain CENTAL) | 15.280 lemma, A1–C1, **ders kitabı ve graded reader korpusundan** — pedagojik olarak tam istediğimiz şey. Ama **CC BY-NC-SA 4.0 olduğu bildiriliyor**; NonCommercial ticari üründe kullanılamaz. Lisans birincil kaynaktan doğrulanamadı, o yüzden **dışarıda**. Doğrulanır ve NC değilse listeye alınmalı — en iyi adaydır. |
| **NGSL xlsx'inin etiketsiz 77.023 satırı** | Aynı dosyada NGSL/NAWL bandı dışında 77 bin satırlık ham frekans kuyruğu var. Bu *dereceli liste değil*, korpus frekansı. `colby` peynirini B2 yapan mekanizma tam olarak budur — alınmaz. |
| **`antdurrant/word.lists` deposunu lisans kaynağı saymak** | Depo MIT ama içinde Oxford 3000/5000 PDF'leri de duruyor. **Bir deponun MIT olması içindeki üçüncü taraf listeleri MIT yapmaz.** Depo yalnızca lisansını bağımsız doğruladığımız listeler (NGSL ailesi, New Dolch) için *ayna* olarak kullanılır. |
| **Princeton WordNet 3.1 (orijinal)** | OEWN 2024 hem daha güncel hem CC BY 4.0 ile net lisanslı. |
| **WordNet gloss'ları / synset eşanlamlıları içerik olarak** | Kullanıcı kararı: "dilbilimsel aşırı teknik ifadeler istemiyorum". `baffle → gravel` tam olarak bu. OEWN yalnızca **iskelet** için (lemma, POS, kaç anlam var), metin için değil. |

---

## 2.1 Evren büyüklüğü — ölçülmüş, tahmin değil

Listeler indirilip birleştirildi (2026-09-05). Kademeli birikim:

| eklenen liste | yeni lemma | toplam |
|---|---:|---:|
| NGSL (+Sup) | 2.848 | 2.848 |
| New Dolch | 81 | 2.929 |
| CEFR-J A1–B2 | 4.070 | **6.999** |
| NAWL (akademik) | 502 | 7.501 |
| TSL (TOEIC) | 405 | 7.906 |
| BSL (iş İngilizcesi) | 537 | 8.443 |
| Octanove C1–C2 | 1.538 | **9.981** |

**9.981 tekil lemma** — hepsi uzman tarafından derlenmiş bir *öğretim* listesinde
yer alıyor, hiçbiri ham frekanstan gelmiyor, hepsi ticari lisanslı. CEFR-J +
Octanove tek başına **9.779 tekil `(headword, pos)` çifti** veriyor ve her birinde
CEFR etiketi hazır — yani K1'in kimlik anahtarıyla birebir aynı biçimde.

**10k üstü.** 15k'ya çıkmanın lisans-temiz tek yolu Nation'ın BNC/COCA
bantlarıdır (CC BY-SA 4.0). Bunlar *kelime ailesi* bandıdır, lemma değil; bir
aile birden çok lemma+POS üretir, dolayısıyla 1–10 bantları kabaca 15k öğeye
denk gelir. Ama 10. banttan sonra kelimeler gerçekten seyrekleşir.

**Karar biçimi: evren büyüklüğü bir sayı değil, bir sütun.**

```
items.tier  1  NGSL + New Dolch                 ~2.900   çekirdek
            2  + CEFR-J A1–B2                   ~7.000   genel öğrenici
            3  + NAWL/TSL/BSL + Octanove        ~10.000  B2–C2 tam kapsam
            4  + BNC/COCA bant 11..N            ~15.000  uzun kuyruk
```

Her kelime **hangi listeden, hangi tier'dan geldiğini** taşır. Sonuç:

- Evreni büyütmek ödenmiş hiçbir işi geçersiz kılmaz (MIGRATION-PLAN §2).
- Kesme noktası istendiği zaman değiştirilir; tier bir sorgudur, kimlik değil.
- **Kalite yapısal olarak korunur:** bir kelime evrene girebilmek için en az bir
  dereceli öğretim listesinde bulunmak zorunda. `colby` hiçbirinde yok — bugünkü
  DB'ye altyazı frekansıyla girmişti, bu şemada giremez. Yani sayı büyüdüğünde
  kalite düşmez, çünkü büyüme frekanstan değil listelerden geliyor.

**Tavsiye:** evren tier 3'e (~10.000) kurulsun, şema tier 4'ü desteklesin, pilot
(K2) yine 300 kelime ödesin. 15k'ya gerçekten ihtiyaç duyulursa BNC/COCA bandı
eklemek bir satırdır ve hiçbir kartın yeniden üretilmesini gerektirmez.

**Ayrıca uzun kuyruk zaten bizim işimiz değil.** Ürün vizyonunda (§5.1) uzun
kuyruğu uygulamanın anlık LLM çağrısı karşılıyor ve Chrome eklentisi kelimeleri
kullanıcının kendi izlediği içerikten yakalıyor. Kullanıcının Netflix'te
karşılaştığı kelime, herhangi bir frekans listesinden daha iyi bir alaka
sinyalidir. Bu DB 10k çekirdeği **ön-öder**; kullanıcının sözcük uzayı sınırsız
kalır. "15k olsa güzel olurdu" ihtiyacının büyük kısmı buradan karşılanıyor.

---

## 3. Alan alan: hangi alan nereden

Kural: **öğrenciye görünen her metin LLM tarafından yazılır.** Kaynak yalnızca
(a) hangi kelime, (b) olgusal sayı/etiket, (c) LLM'e verilen kanıt sağlar.

| hedef alan | kaynak | rol |
|---|---|---|
| kelime evreni (hangi lemma+POS) | NGSL + NGSL-Spoken + New Dolch | **seçim** |
| `items.pos` | OEWN | olgu |
| `item_level.cefr` | CEFR-J (A1–B2), Octanove (C1–C2) | olgu/etiket |
| `item_level.freq_rank` | wordfreq | olgu |
| `item_phonetics.ipa` | ipa-dict en_US | olgu |
| `senses` kaç satır olacak | OEWN anlam sayısı = **ipucu**, kararı LLM verir | kanıt |
| `sense_cards.gloss_en` | — | **LLM yazar** (kanıt: OEWN + Kaikki tanımları) |
| `sense_gloss_l1` (TR) | — | **LLM yazar** (kanıt: Tatoeba en–tr) |
| `sense_examples` | — | **LLM yazar** (kanıt: Tatoeba + Kaikki örnekleri) |
| eş/zıt anlam | — | **LLM yazar** (kanıt: OEWN ilişkileri) |
| `item_forms` (çekim) | Kaikki veya LLM | kanıt/olgu |
| `register`, `usage_note` | — | **LLM yazar** |

Bu tablo aynı zamanda **bugünkü kalite sorunlarının çözümüdür**: `liver`'ın 60
kelimelik tıp tanımı, `baffle → gravel`, "Did he hell." örneği ve
`interstate → uluslararası otoyol` çevirisinin hepsi "kaynak metnini doğrudan
sevk et" kararından geliyordu. Bu tabloda o karar hiç yok.

---

## 4. Lisans mimarisi — katmanlar zaten doğru yerde

Şu tesadüf değil, mimariyi bu yüzden böyle kurduk: **ShareAlike yükümlülüğü
dağıtımda doğar, kullanımda değil.** Katmanlarımız tam bu çizgiden geçiyor.

```
data/raw/ + data/builds/     KANIT KATMANI      makineden çıkmaz, dağıtılmaz
                             CC BY-SA dahil her lisans burada serbest
        │
        │  LLM yeniden yazar — kaynak ifadesi geçmez
        ▼
data/stores/ + data/dist/    SEVKİYAT KATMANI   kullanıcıya gider
                             yalnızca LLM metni + olgular (frekans, IPA, CEFR)
```

Uygulanacak dört kural:

1. **Kaikki/Wiktionary metni `dist/`'e asla girmez.** Yalnızca prompt'a kanıt
   olarak verilir. `dist` üretiminde kaynak metin alanı bulunması bir **kapı
   ihlalidir** (MIGRATION-PLAN §6.1: ihlalde sıfır dosya + exit 1).
2. **Her ingestor lisansını beyan eder.** `evidence.source` alanı zaten var;
   yanına `ingestors/registry.py` içinde `license` + `attribution` + `shippable:
   bool` eklenir. `shippable=False` olan bir kaynaktan gelen değer `dist/`'e
   yazılırsa materialize durur.
3. **`dist/` içine `ATTRIBUTION.md` konur** ve `_dist_meta.json`'a kullanılan
   kaynakların listesi yazılır. Atıf CEFR-J, Tatoeba, OEWN, ipa-dict ve NGSL
   için zaten şart.
4. **GPL'li hiçbir veri dosyası repoya girmez.** `en_UK` IPA bu yüzden dışarıda.

---

## 5. Avukata sorulacak iki madde

Geri kalan her şey kaynakların kendi açık izniyle çözülüyor. Bu ikisi çözülmüyor:

1. **NGSL'in CC BY-SA'sı bizim kelime listemize bulaşır mı?** Evrenimiz NGSL'den
   türetiliyor; ürünün kelime listesini yayınlamak NGSL'in bir *uyarlaması* mı
   (ShareAlike tetiklenir) yoksa bağımsız bir *derleme* mi? İki hazırlıklı
   cevabımız var: (a) atıf verip kelime listesi dosyasını BY-SA altında
   yayınlamayı kabul etmek — LLM'in yazdığı kart içeriği ayrı dosyada kaldığı
   için ürün kapalı kalır; (b) NGSL'i yalnızca *doğrulama* için kullanıp nihai
   üyeliği frekans + CEFR olgularından türetmek. **(a) tavsiyem** — daha
   dürüst, daha basit ve NGSL'in ruhuna uygun.

2. **LLM'e CC BY-SA kanıt verip çıktısını kapalı sevk etmek türev eser mi?**
   Hukuken oturmamış bir alan. Riski düşüren şey zaten yaptığımız: kanıt
   *birden çok* kaynaktan gelir, çıktı kısa ve bağımsız yazılır, kaynak
   ifadesi kopyalanmaz. Yine de Kaikki'yi kanıttan tamamen çıkarmak mümkün —
   OEWN (CC BY 4.0, ShareAlike yok) tek başına da yeterli kanıt verir.
   **Bu bir düğmedir**, mimari karar değil: `ingestors/registry.py`'de
   Kaikki'yi kapatmak tek satır.

---

## 6. Ne kadar veri, ne kadar iş

Pilot (K2: 300 kelime) için indirilecekler:

| dosya | boyut | not |
|---|---|---|
| NGSL 1.01 with SFI (xlsx) | 4 MB | NGSL + NAWL bantları aynı dosyada |
| TSL / BSL / New Dolch (csv) | < 150 KB | üçü birlikte |
| CEFR-J + Octanove (csv) | 280 KB | ölçüldü: 233 KB + 46 KB |
| ipa-dict `en_US.txt` | ~5 MB | tek dosya |
| OEWN 2024 | ~310 MB | tek seferlik; POS + anlam sayısı için |
| wordfreq | pip paketi | indirme yok |
| Tatoeba en–tr | ~50 MB | opsiyonel, örnek kanıtı için |
| ~~Kaikki en~~ | ~10 GB | **pilotta indirilmiyor** — `legacy_dist` (K4) yerini tutuyor |

Yani pilot için ağır indirme yok. Kaikki kararı Adım 5'ten sonra, kart kalitesi
ölçülünce verilir.

---

## 7. Kaynak künyeleri

- New General Service List — Browne, C., Culligan, B. & Phillips, J. (2013, güncel 2023). CC BY-SA 4.0. https://www.newgeneralservicelist.com/
- CEFR-J Vocabulary Profile v1.5 — Tono, Y., Tokyo University of Foreign Studies. https://github.com/openlanguageprofiles/olp-en-cefrj
- Octanove Vocabulary Profile C1/C2 v1.0 — Octanove Labs. CC BY-SA 4.0.
- Open English WordNet 2024 — Global WordNet Association. CC BY 4.0. https://en-word.net/
- ipa-dict — open-dict-data. MIT (`en_US`). https://github.com/open-dict-data/ipa-dict
- wordfreq — Robyn Speer. MIT. https://github.com/rspeer/wordfreq
- Tatoeba — CC BY 2.0 FR. https://tatoeba.org
- Kaikki.org / Wiktextract — Tatu Ylonen; Wiktionary verisi CC BY-SA 4.0 + GFDL.
- BNC/COCA word family lists — Nation, P., Victoria University of Wellington. CC BY-SA 4.0. https://www.wgtn.ac.nz/lals/resources/paul-nations-resources
- NAWL / TSL / BSL / New Dolch — NGSL Project (Browne, Culligan, Phillips). CC BY-SA 4.0.
- (değerlendirildi, alınmadı) EFLLex — Dürlich & François (2018), UCLouvain CENTAL. https://cental.uclouvain.be/cefrlex/efllex/
