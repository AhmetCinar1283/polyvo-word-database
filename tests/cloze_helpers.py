"""
Cloze testlerinin ORTAK kurulum yardimcilari — dort test dosyasi ayni evreni,
ayni sahte saglayiciyi ve ayni onayli karti tekrar tekrar yazmasin diye.

Burada TEST YOKTUR: yalnizca tohumlama. Gercek `data/` dizinine hicbir sey
yazilmaz — cagiran dosya `isolated_data_root` fixture'ini kullanir.
"""

from __future__ import annotations

import json
import os
import sqlite3

from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.llm.base import LLMResult
from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached
from polyvo.curriculum import schema as curriculum_schema
from polyvo.dictionary.build import stages as dict_stages
from polyvo.modules.cloze import cefr
from polyvo.modules.cloze.job import ClozeJob
from polyvo.modules.cloze.rationale.job import ClozeRationaleJob
from polyvo.modules.cloze.rationale.store import ClozeRationaleStore
from polyvo.modules.cloze.rationale.translate.job import (
    ClozeRationaleTranslationJob,
)
from polyvo.modules.cloze.rationale.translate.store import (
    ClozeRationaleTranslationStore,
)
from polyvo.modules.cloze.store import ClozeStore
from polyvo.modules.lexicon_card.store import LexiconCardStore

TAG, L2 = "test", "en"

MODEL = "cloudflare:@cf/qwen/qwen3-30b-a3b-fp8"

CARD_ANSWER = {
    "gloss_en": "A place where money is kept.",
    "register": "neutral",
    "usage_note": "",
    "examples": ["I went to the bank to get some money.",
                 "The bank opens at nine."],
}


def cloze_answer(sentences=None, options=None) -> dict:
    """Gecerli bir uc soruluk cloze cevabi (testler bunu bozarak kullanir)."""
    sentences = sentences or [
        "I keep my money in a bank.",
        "She walked to the bank to pay the bill this morning.",
        "After the long meeting he went to the bank to ask about the new "
        "office rules and forms.",
    ]
    options = options or [
        ["bank", "spoon", "cloud", "chair"],
        ["bank", "garden", "kitchen", "forest"],
        ["bank", "office", "garden", "market"],
    ]
    return {"questions": [
        {"difficulty": name, "sentence": sentence, "answer": "bank",
         "options": list(opts)}
        for name, sentence, opts in zip(("kolay", "orta", "zor"),
                                        sentences, options)]}


class FakeProvider:
    """`complete_json` sozlesmesini taklit eden, agi olmayan saglayici."""

    def __init__(self, answer=None, label=MODEL):
        """Verilen cevabi her cagride dondurur; cagrilari sayar."""
        self.label = label
        self.answer = answer if answer is not None else cloze_answer()
        self.calls: list[str] = []

    def preflight(self):
        """Sahte on-kontrol — her zaman gecer."""
        return None

    def peek_cached(self, prompt, cache_conn):
        """Onbellekteki cevabi cagri yapmadan doner; yoksa None."""
        hit = get_cached(cache_conn, hash_prompt(self.label, prompt))
        if hit is None:
            return None
        return LLMResult(json.loads(hit), True, hit)

    def complete_json(self, prompt, cache_conn, *, max_tokens, temperature,
                      pace_delay=0.0, bypass_cache=False):
        """Onbellek-once davranisi dahil sahte bir cagri."""
        h = hash_prompt(self.label, prompt)
        hit = None if bypass_cache else get_cached(cache_conn, h)
        if hit is not None:
            return LLMResult(json.loads(hit), True, hit)
        self.calls.append(prompt)
        raw = json.dumps(self.answer, ensure_ascii=False)
        store_cached(cache_conn, h, self.label, prompt, raw)
        return LLMResult(json.loads(raw), False, raw)


def seed_universe(rows=(("bank", "noun", "A2", 5),)):
    """Test evrenini `workspace/<tag>/<l2>/universe.sqlite`'a yazar."""
    conn = curriculum_schema.open_universe_db(TAG, L2)
    with conn:
        conn.executemany(
            "INSERT INTO universe_items (item_id, sense_id, l2, headword, pos,"
            " cefr, freq_rank, stable_key) VALUES (?,?,?,?,?,?,?,?)",
            [(i, 1000 + i, L2, head, pos, level, rank, f"{L2}:{head}:{pos}")
             for i, (head, pos, level, rank) in enumerate(rows, start=1)])
    conn.close()


def seed_card(headword="bank", pos="noun", answer=None, status="approved"):
    """`sense_cards`a bir kart yazar (varsayilan: ONAYLI)."""
    from polyvo.modules.lexicon_card import units as card_units

    unit = next(u for u in card_units.load_units(TAG, L2)
                if u.data["headword"] == headword and u.data["pos"] == pos)
    store = LexiconCardStore()
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload=(answer or CARD_ANSWER) if status == "approved" else {},
        status=status, tier=3, reject_reason=None if status == "approved" else "test",
        model_label=MODEL), None)
    store.commit()
    store.close()


def seed_build_cefr(rows=(("bank", "A2"), ("spoon", "A2"), ("cloud", "A1"),
                          ("chair", "A1"), ("garden", "A1"), ("kitchen", "A1"),
                          ("forest", "A2"), ("office", "A1"), ("market", "A2"),
                          ("store", "B2"), ("loan", "B2"))):
    """Evren CEFR sozlugunu (`builds/<tag>/01_lexicon/lexicon.sqlite`) yazar.

    Satir `(kelime, seviye)` ya da `(kelime, pos, seviye)` olabilir: sozlukte
    seviye (kelime, POS) basina bilinir, cogu testin POS'a ihtiyaci yoktur."""
    path = dict_stages.lexicon_db_path(TAG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS candidates (headword TEXT,"
                     " pos TEXT, tier INTEGER, cefr TEXT, freq_rank INTEGER,"
                     " is_multiword INTEGER, sources TEXT, pos_source TEXT)")
        conn.executemany(
            "INSERT INTO candidates (headword, pos, tier, cefr, freq_rank,"
            " is_multiword, sources, pos_source) VALUES (?,?,1,?,1,0,'t','t')",
            [row if len(row) == 3 else (row[0], "noun", row[1])
             for row in rows])
    conn.close()
    cefr.reset_cache()          # onbellek testler arasinda tasinmasin


def seed_all(universe=None, cefr_rows=None):
    """Evren + onayli kart + CEFR sozlugu — cogu testin ihtiyaci."""
    seed_universe(universe or (("bank", "noun", "A2", 5),))
    seed_card()
    seed_build_cefr(cefr_rows) if cefr_rows else seed_build_cefr()


def run_cloze(provider, **kwargs):
    """Cloze uretim isini sahte saglayiciyla ucdan uca kosturur."""
    store = ClozeStore()
    try:
        return engine_run.run(ClozeJob(), JobContext(tag=TAG, l2=L2),
                              provider=provider, store=store,
                              assume_yes=True, **kwargs)
    finally:
        store.close()


#: Varsayilan cloze_answer()in UC sorusuna karsilik gelen gecerli bir
#: ipucu/aciklama cevabi. Her ipucu hedef kelimeyi ya da herhangi bir sikkin
#: metnini icermez; her aciklama acikladigi sikkin kendi kelimesini tasir.
RATIONALE_ANSWER = {
    "questions": [
        {
            "hint": "Think about where people keep or store their money "
                   "for safekeeping.",
            "reasons": [
                {"option": "bank",
                 "reason": "A bank is a place that keeps your money safe, "
                          "which matches this sentence."},
                {"option": "spoon",
                 "reason": "A spoon is a utensil for eating, which has "
                          "nothing to do with keeping money safe."},
                {"option": "cloud",
                 "reason": "A cloud is a mass of water vapor in the sky, "
                          "completely unrelated to storing money."},
                {"option": "chair",
                 "reason": "A chair is a piece of furniture you sit on, "
                          "not a place to keep money."},
            ],
        },
        {
            "hint": "Consider a business that handles money, checks, and "
                   "bill payments.",
            "reasons": [
                {"option": "bank",
                 "reason": "A bank is where you can pay bills and manage "
                          "your money, fitting this sentence."},
                {"option": "garden",
                 "reason": "A garden is an outdoor area for growing "
                          "plants, not a place to pay bills."},
                {"option": "kitchen",
                 "reason": "A kitchen is a room for cooking food, "
                          "unrelated to paying a bill."},
                {"option": "forest",
                 "reason": "A forest is a large area covered with trees, "
                          "nothing to do with paying bills."},
            ],
        },
        {
            "hint": "Picture where you might handle financial paperwork "
                   "or ask about accounts.",
            "reasons": [
                {"option": "bank",
                 "reason": "A bank is a financial institution where you "
                          "can ask about accounts and paperwork."},
                {"option": "office",
                 "reason": "An office is a place where people work at "
                          "desks, not where you would ask about forms."},
                {"option": "garden",
                 "reason": "A garden is a place for growing plants and "
                          "flowers, unrelated to paperwork or forms."},
                {"option": "market",
                 "reason": "A market is a place to buy and sell goods, "
                          "not where you would ask about forms."},
            ],
        },
    ],
}


def rationale_answer(questions=None) -> dict:
    """Gecerli bir ipucu/aciklama cevabi (testler bunu bozarak kullanir)."""
    if questions is None:
        return json.loads(json.dumps(RATIONALE_ANSWER))
    return {"questions": questions}


def run_rationale(provider, **kwargs):
    """Ipucu/aciklama uretim isini sahte saglayiciyla ucdan uca kosturur."""
    store = ClozeRationaleStore()
    try:
        return engine_run.run(ClozeRationaleJob(), JobContext(tag=TAG, l2=L2),
                              provider=provider, store=store,
                              assume_yes=True, **kwargs)
    finally:
        store.close()


#: Varsayilan RATIONALE_ANSWER'in Turkce cevirisi (`tr` pilotu icin).
RATIONALE_TR_ANSWER = {
    "hints": [
        "Insanlarin paralarini guvenle sakladigi yeri dusun.",
        "Fatura ve para islemleriyle ugrasan bir isletmeyi dusun.",
        "Hesaplarla ilgili evrak isi icin nereye gidebilecegini hayal et.",
    ],
    "reasons": [
        "Banka paranizi guvenle sakladigi icin bu cumleye uyuyor.",
        # "spoon" BILEREK cevrilmeden birakildi: §16'nin bilinen tuzagi
        # (siklarin Ingilizce kelimesi aciklamada KALIR, cevrilmez).
        "Bir spoon yemek yeme aracidir, para saklamakla ilgisi yoktur.",
        "Bulut gokyuzundeki su buharidir, para saklamakla tamamen ilgisizdir.",
        "Sandalye uzerine oturulan bir mobilyadir, para saklanacak bir yer degildir.",
        "Banka fatura odemenize ve paranizi yonetmenize izin verir.",
        "Bahce bitki yetistirilen acik bir alandir, fatura odenecek yer degildir.",
        "Mutfak yemek pisirilen bir odadir, fatura odemekle ilgisizdir.",
        "Orman agaclarla kapli genis bir alandir, fatura odemekle ilgisi yoktur.",
        "Banka hesap ve evrak isleri hakkinda soru sorabileceginiz mali bir kurumdur.",
        "Ofis insanlarin masada calistigi bir yerdir, form sormaya gidilecek yer degildir.",
        "Bahce bitki ve cicek yetistirilen bir yerdir, evrak isiyle ilgisizdir.",
        "Pazar mal alip satilan bir yerdir, form sormaya gidilecek yer degildir.",
    ],
}


def rationale_translate_answer(hints=None, reasons=None) -> dict:
    """Gecerli bir ipucu/aciklama ceviri cevabi (varsayilan: `tr`)."""
    return {"hints": list(hints) if hints is not None
                    else list(RATIONALE_TR_ANSWER["hints"]),
            "reasons": list(reasons) if reasons is not None
                      else list(RATIONALE_TR_ANSWER["reasons"])}


def run_rationale_translate(provider, l1="tr", **kwargs):
    """Ipucu/aciklama ceviri isini sahte saglayiciyla ucdan uca kosturur."""
    store = ClozeRationaleTranslationStore()
    try:
        return engine_run.run(
            ClozeRationaleTranslationJob(),
            JobContext(tag=TAG, l2=L2, l1=l1, variant=l1),
            provider=provider, store=store, assume_yes=True, **kwargs)
    finally:
        store.close()
