"""
CELDIRICI kapilari.

BU ISIN EN BUYUK KALITE RISKI BURADADIR VE DURUSTCE BOYLE RAPORLANIR:
"celdirici gercekten bosluga uymuyor mu" sorusunu MEKANIK OLARAK
DOGRULAMANIN YOLU YOKTUR — gomme (embedding) katmani yok, anlamsal yakinlik
olculemiyor. Bu yuzden o kontrol **KESINLIKLE REDDETMEZ**; her pakete bir
UYARI dusurur ve insan denetimine birakir (§11). Sayiya guvenip ornek
okumamak, tam olarak bu bosluga dusmektir: QA'nin olcemedigi sey depoda
"kabul edilmis" gorunur.

Buna karsilik UC sey sayilabilir ve REDDEDER:
  1. celdirici hedef kelimenin kendisi ya da bir bicimi (bedava eleme),
  2. celdiricinin sozcuk turu hedefle ayni degil (bedava eleme),
  3. celdiricinin CEFR'i hedef anlamin CEFR'ini BIR BANDDAN FAZLA asiyor
     (§12) — o zaman soru hedef kelime yuzunden degil, CELDIRICIYI tanimadigi
     icin zorlasir.
Evren disi celdiricide olcum yok -> uyari.

CEFR tavaninin IKI PAYI vardir, ikisi de olculmus bir celiskiden dogar:
  - `cefr.LEVEL_TOLERANCE`: tam bir band asma reddetmez,
  - `Band.enforce_distractor_level`: "zor" bandinda hic reddetmez, UYARIR.
Gerekce difficulty.py'de yazilidir: bir A1 kelimesinin yakin anlamlilari
A2+'dir; tavani harfiyen uygulamak "zor" bandini imkansiz kilar. 2026-09-07
kosusunda 42 reddin 27'si tam olarak buydu.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.text import qa as text_qa
from polyvo.modules.cloze import cefr
from polyvo.modules.cloze.difficulty import band_for

#: Depodaki POS adindan WordNet POS koduna. Listede olmayan tur (prep, det,
#: pron, conj, num, modal, interj, particle) WordNet'te yoktur -> olculemez.
_WORDNET_POS: dict[str, tuple[str, ...]] = {
    "noun": ("n",),
    "verb": ("v",),
    "adj": ("a", "s"),
    "adv": ("r",),
}


def _wordnet_pos_codes(word: str) -> set[str] | None:
    """Kelimenin WordNet'teki POS kodlari; WordNet yoksa/kelime yoksa `None`."""
    try:
        from nltk.corpus import wordnet as wn
        synsets = wn.synsets(word)
    except Exception:
        return None
    if not synsets:
        return None
    return {s.pos() for s in synsets}


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) dondurur."""
    headword = unit.data["headword"]
    pos = unit.data["pos"]
    sense_cefr = unit.data.get("cefr")
    levels = cefr.load(unit.data["cefr_db"])
    expected_codes = _WORDNET_POS.get(pos)

    warnings: list[str] = []
    for question in questions:
        band = band_for(question["seq"])
        answer = question["answer"].lower()
        for option in question["options"]:
            if option.lower() == answer:
                continue

            if text_qa.loose_same_word(option, headword):
                return "celdirici_hedef_kelimenin_bicimi", warnings

            if " " in option.strip():
                warnings.append("celdirici_cok_kelimeli_olculemedi")
                continue

            codes = _wordnet_pos_codes(option)
            if expected_codes is None or codes is None:
                warnings.append("celdirici_sozcuk_turu_olculemedi")
            elif not (codes & set(expected_codes)):
                return "celdirici_sozcuk_turu_farkli", warnings

            # POS verilir: celdiricinin turu hedefle ayni olmak zorunda, ve
            # sozlukte seviye (kelime, POS) basina bilinir — `take` fiil A1,
            # isim B1'dir.
            option_cefr = levels.get(option.strip().lower(), pos)
            if option_cefr is None:
                warnings.append("celdirici_evren_disi_cefr_olculemedi")
            elif cefr.exceeds(option_cefr, sense_cefr, cefr.LEVEL_TOLERANCE):
                if band.enforce_distractor_level:
                    return "celdirici_cefr_hedefin_ustunde", warnings
                warnings.append(f"celdirici_cefr_hedefin_ustunde_seq{question['seq']}")

    # HER pakete dusen, ASLA reddetmeyen uyari — bkz. modul docstring'i.
    warnings.append("celdiricinin_uymadigi_dogrulanamadi")
    return None, sorted(set(warnings))
