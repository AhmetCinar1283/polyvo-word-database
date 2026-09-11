"""
Grammar testlerinin ORTAK kurulum yardimcilari — `cloze_helpers.py`nin
onayli cloze paketini KULLANIR (grammar cumleleri `APP.sentences` seam'inden
alir), kendi sahte grammar cevabini ve kosu yardimcisini ekler.

Burada TEST YOKTUR: yalnizca tohumlama + kosu sarmalayicisi. Gercek `data/`
dizinine hicbir sey yazilmaz — cagiran dosya `isolated_data_root`
fixture'ini kullanir.
"""

from __future__ import annotations

import json

from cloze_helpers import (   # noqa: F401 — testler bunlari da kullanir
    L2,
    RATIONALE_ANSWER,
    TAG,
    FakeProvider,
    cloze_answer,
    rationale_answer,
    run_cloze,
    run_rationale,
    seed_all,
)
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.modules.grammar.job import GrammarJob
from polyvo.modules.grammar.store import GrammarStore
from polyvo.modules.grammar.catalog_translate.job import (
    GrammarCatalogTranslationJob,
)
from polyvo.modules.grammar.catalog_translate.store import (
    GrammarCatalogTranslationStore,
)
from polyvo.modules.grammar.translate.job import GrammarTranslationJob
from polyvo.modules.grammar.translate.store import GrammarTranslationStore

#: Varsayilan onayli cloze paketinin (bkz. `cloze_helpers.cloze_answer`)
#: UC cumlesine karsilik gelen, katalogda GERCEKTEN var olan gecerli bir
#: grammar cevabi.
GRAMMAR_ANSWER = {
    "sentences": [
        {"seq": 1,
         "rules": [
             {"rank": 1, "rule_id": "EN.TENSE.PRESENT_SIMPLE",
              "trigger": "keep",
              "note": "Describes a habitual action, keeping money in a "
                     "bank as a routine."},
         ],
         "candidates": []},
        {"seq": 2,
         "rules": [
             {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE",
              "trigger": "walked",
              "note": "A completed action at a specific past time this "
                     "morning."},
             {"rank": 2, "rule_id": "EN.INF.TO_INFINITIVE",
              "trigger": "to pay",
              "note": "The to-infinitive expresses the purpose of the walk."},
         ],
         "candidates": []},
        {"seq": 3,
         "rules": [
             {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE",
              "trigger": "went",
              "note": "A completed action after the long meeting ended."},
             {"rank": 2, "rule_id": "EN.INF.TO_INFINITIVE",
              "trigger": "to ask",
              "note": "The to-infinitive expresses the purpose of going "
                     "to the bank."},
         ],
         "candidates": []},
    ],
}


def grammar_answer(sentences=None) -> dict:
    """Gecerli bir grammar cevabi (testler bunu bozarak kullanir)."""
    if sentences is None:
        return json.loads(json.dumps(GRAMMAR_ANSWER))
    return {"sentences": sentences}


def run_grammar(provider, *, propose_only: bool = False, **kwargs):
    """Grammar analiz isini sahte saglayiciyla ucdan uca kosturur."""
    store = GrammarStore(propose_only=propose_only)
    try:
        return engine_run.run(GrammarJob(propose_only=propose_only),
                              JobContext(tag=TAG, l2=L2), provider=provider,
                              store=store, assume_yes=True, **kwargs)
    finally:
        store.close()


#: `GRAMMAR_ANSWER`in BES notunun (1+2+2) Turkce cevirisi. Bazi metinler
#: BILEREK kendi `trigger`inin Ingilizce halini de icinde tasir (§18
#: tuzaginin testi: dil kapisi bu yuzden dogru ceviriyi reddetmemeli).
GRAMMAR_TR_ANSWER = {
    "notes": [
        "Parayi bankada bir rutin olarak tutmayi anlatir (\"keep\" fiili).",
        "Sabah odeme yapmak icin yuruyuse cikildigi, tamamlanmis bir eylem.",
        "\"to pay\" yapisi yuruyusun amacini belirtir.",
        "Uzun toplanti bittikten sonra gidilen, tamamlanmis bir eylem.",
        "\"to ask\" yapisi bankaya gitme amacini belirtir.",
    ],
}


def grammar_translate_answer(notes=None) -> dict:
    """Gecerli bir grammar not ceviri cevabi (varsayilan: `tr`)."""
    return {"notes": list(notes) if notes is not None
                    else list(GRAMMAR_TR_ANSWER["notes"])}


def run_grammar_translate(provider, l1: str = "tr", **kwargs):
    """Grammar not ceviri isini sahte saglayiciyla ucdan uca kosturur."""
    store = GrammarTranslationStore()
    try:
        return engine_run.run(
            GrammarTranslationJob(),
            JobContext(tag=TAG, l2=L2, l1=l1, variant=l1),
            provider=provider, store=store, assume_yes=True, **kwargs)
    finally:
        store.close()


def catalog_translate_answer(name: str = "Şimdiki Zaman",
                             short: str = "Alışkanlık ya da genel doğruları"
                                          " anlatmak için kullanılır.") -> dict:
    """Gecerli bir katalog ceviri cevabi — cagiran testler kural basina
    farkli metin verebilir (FakeProvider tek cevap dondurdugu icin AYNI
    metin her kurala yazilir, testler bunu SAYIM icin kullanir)."""
    return {"name": name, "short": short}


def run_catalog_translate(provider, l1: str = "tr", limit: int | None = None,
                          **kwargs):
    """Katalog ceviri isini sahte saglayiciyla ucdan uca kosturur."""
    store = GrammarCatalogTranslationStore()
    try:
        return engine_run.run(
            GrammarCatalogTranslationJob(),
            JobContext(tag=TAG, l2=L2, l1=l1, variant=l1, limit=limit),
            provider=provider, store=store, assume_yes=True, **kwargs)
    finally:
        store.close()
