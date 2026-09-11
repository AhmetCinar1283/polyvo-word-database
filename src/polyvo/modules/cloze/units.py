"""
Cloze isinin birimleri — evrendeki HER kelime degil, yalnizca ONAYLI kartla
eslesen anlamlar. Kartsiz/onaysiz anlamin soracak bir anlami yoktur.

Bu dosya `lexicon_card`in yalnizca ILAN EDILMIS okuma yuzeyini
(`lexicon_card.public`) cagirir — o app'in icine dagilmis import YOKTUR
(`tests/test_layering.py` bunu olcer).

ICERIK SOZCUGU OLMAYAN ANLAM BIRIM URETMEZ — IKI kapi vardir ve ikisi de
gereklidir: sozcuk turu (`CLOZE_POS`) ve kelimenin kendisi
(`FUNCTION_WORDS`), cunku sozluk edatlari `adv` etiketler. Gerekceler
sabitlerin yanindadir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.dictionary.build import stages as dict_stages
from polyvo.modules.lexicon_card import public as card_public

#: Cloze'un sorabilecegi sozcuk turleri. Disarida kalanlar (prep, det, pron,
#: conj, num, modal, interj, particle) UC ayri sebeple cloze'a uygun degildir:
#:   1. "the"/"to"/"of" 15-25 kelimelik bir cumlede TAM BIR KEZ gecemez —
#:      `qa/blank.py` bunlari zorunlu olarak reddeder;
#:   2. WordNet'te bu turler yoktur, celdiricinin sozcuk turu OLCULEMEZ
#:      (`qa/distractor.py`);
#:   3. bir edatin "anlamini" coktan secmeli boslukla olcmek zaten dilbilgisi
#:      sorusudur, kelime bilgisi sorusu degil.
#: 2026-09-07 kosusunda 50 birimin 10'u bu turlerdendi ve odenen cagrinin
#: besde biri buraya gitti. Kural yazili degil OLCULU olsun diye burada,
#: promptta degil.
CLOZE_POS: frozenset[str] = frozenset({"noun", "verb", "adj", "adv"})

#: POS ETIKETI YETMEZ: sozluk edatlari, zamirleri ve niceleyicileri sik sik
#: `adv`/`adj` etiketler ("above", "in", "after", "all", "both"), yani
#: `CLOZE_POS` filtresinden gecerler. Bu liste ayni UC gerekceyi kelime
#: duzeyinde uygular — ozellikle ucuncusunu: bir edatin ya da niceleyicinin
#: "anlamini" coktan secmeli boslukla olcmek DILBILGISI sorusudur.
#: 2026-09-07 kosusunda basarisiz 16 birimin 7'si buydu (`above` x2, `after`,
#: `in`, `non`, `o'clock`, `it`) ve `it` YANLISLIKLA ONAYLANDI — yani bu liste
#: yalnizca ucuz olani atlamiyor, kotu bir karti da depoya girmekten aliyor.
#:
#: LISTE BILEREK DAR: yalnizca KAPALI SINIF (yeni uye almayan) sozcukler ve
#: bagimli bicimler var. `core/text/qa.py::ENGLISH_MARKERS` BURAYA UYMAZ ve
#: kasten yeniden kullanilmadi — o liste DIL TESPITI icin genis tutulmustur ve
#: `take`/`make`/`go`/`see`/`know`/`want`/`need` gibi tam da ogretilmesi
#: gereken A1 fiillerini icerir; bir ogrencinin en cok ihtiyac duydugu
#: kelimeleri evrenden atardi. Acik sinifin HICBIR uyesi (icerik zarflari
#: "carefully"/"already"/"never", icerik sifatlari, isimler, fiiller) burada
#: yoktur.
FUNCTION_WORDS: frozenset[str] = frozenset({
    # Edatlar ve yon/konum parcaciklari — zarf etiketli gelseler bile
    # aralarindaki secim dilbilgisidir, kelime bilgisi degil.
    "about", "above", "across", "after", "against", "along", "alongside",
    "among", "around", "at", "before", "behind", "below", "beneath",
    "beside", "besides", "between", "beyond", "by", "despite", "down",
    "during", "except", "for", "from", "in", "inside", "into", "near",
    "of", "off", "on", "onto", "opposite", "out", "outside", "over",
    "past", "per", "since", "through", "throughout", "till", "to",
    "toward", "towards", "under", "underneath", "until", "up", "upon",
    "versus", "via", "with", "within", "without",
    # Zamirler ve isaret sozcukleri — bir bosluga "it"/"they" koymak
    # gonderim sorusudur; celdiricileri de olculemez.
    "i", "me", "my", "mine", "myself", "you", "your", "yours", "yourself",
    "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
    "herself", "it", "its", "itself", "we", "us", "our", "ours",
    "ourselves", "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those", "here", "there",
    "someone", "somebody", "something", "anyone", "anybody", "anything",
    "everyone", "everybody", "everything", "nobody", "nothing",
    # Belirteciler ve niceleyiciler.
    "a", "an", "the", "all", "any", "both", "each", "either", "enough",
    "every", "many", "much", "neither", "no", "none", "several", "some",
    "such",
    # Baglaclar ve soru sozcukleri.
    "and", "or", "but", "nor", "so", "if", "unless", "although", "though",
    "while", "whereas", "whether", "because", "as", "than",
    "how", "what", "when", "where", "which", "who", "whom", "whose", "why",
    # Kopula, yardimci fiil ve kipler. DIKKAT: "have"/"do" BURADA YOKTUR —
    # onlar ayni zamanda sozluksel fiillerdir ("I have a car") ve ogretilir.
    "be", "am", "is", "are", "was", "were", "been", "being",
    "will", "would", "shall", "should", "can", "could", "may", "might",
    "must", "ought",
    # Olumsuzluk ve derece — "very" ile "too" arasindaki secim dilbilgisidir.
    "not", "very", "too", "quite",
    # Bagimli bicimler: tek baslarina bir bosluga girmezler. "non"/"anti"/
    # "mid"/"mini" birer ONEKTIR, sozlukte yanlislikla sifat/zarf gorunurler.
    "non", "anti", "mid", "mini", "o'clock",
})

#: `FUNCTION_WORDS` KELIME duzeyinde eler, oysa birkac kapali sinif sozcugun
#: GERCEK bir acik sinif kullanimi da vardir ve o kullanim ogretilir. Kural
#: kelime duzeyinde kaldi, istisna (kelime, POS) duzeyinde yazildi — cunku
#: ayirt eden sey POS'tur ve liste boylece OLCULEBILIR kalir: her satir
#: evrende var olan, gozle dogrulanmis bir anlamdir.
#: `may` (noun) BILEREK YOK: "a possibility or chance" glossu kipin yanlis
#: cozumlenmesidir, isim olan bir `may` yoktur.
CONTENT_EXCEPTIONS: frozenset[tuple[str, str]] = frozenset({
    ("can", "noun"),    # sivi kabi, teneke kutu
    ("will", "noun"),   # irade
    ("while", "noun"),  # bir sure
})


def is_cloze_target(headword: str, pos: str) -> bool:
    """Bu (kelime, POS) cloze sorusu olabilir mi?

    Tek karar noktasi: `load_units` de testler de burayi cagirir, yoksa
    "birim olur mu" sorusunun iki kopyasi olusur ve ayrisirlar."""
    if pos not in CLOZE_POS:
        return False
    word = headword.strip().lower()
    if (word, pos) in CONTENT_EXCEPTIONS:
        return True
    return word not in FUNCTION_WORDS


def load_units(tag: str, l2: str) -> list[Unit]:
    """Onayli her anlam icin bir birim; sira kart yukleyicisiyle AYNIDIR.

    Yalnizca `CLOZE_POS` turundeki VE `FUNCTION_WORDS`ta OLMAYAN anlamlar
    birim olur — kartsiz/onaysiz anlamin soracak bir anlami olmadigi gibi,
    bir edatin da yoktur (POS etiketi onu zarf gostermis olsa bile).

    `data['card']` promptun BAGLAM olarak kullanacagi alanlari tasir: model
    kelimeyi degil O ANLAMI sorsun, mevcut ornek cumleleri de TEKRAR ETMESIN
    diye onlar da verilir. `data['cefr_db']` seviye kapisinin evren sozlugudur
    (QA `ctx` almaz, yolu birimle tasiriz)."""
    cefr_db = dict_stages.lexicon_db_path(tag)
    return [
        Unit(
            key=view.stable_key,
            name=f"{view.headword} ({view.pos})",
            data={
                "stable_key": view.stable_key,
                "sense_id": view.sense_id,
                "item_id": view.item_id,
                "headword": view.headword,
                "pos": view.pos,
                "cefr": view.cefr,
                "cefr_db": cefr_db,
                "card": {
                    "gloss_en": view.gloss_en,
                    "register": view.register,
                    "examples": list(view.examples),
                },
            },
        )
        for view in card_public.approved_senses(tag, l2)
        if is_cloze_target(view.headword, view.pos)
    ]
