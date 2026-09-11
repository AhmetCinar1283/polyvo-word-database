"""
Grammar QA testleri — SAF fonksiyonlar, AG CAGRISI YOK.

Olculen sey Is 6'nin en guclu kapilaridir: cumlede bulunmayan `trigger`
REDDEDER, katalog disi `rule_id` REDDEDER + aday olarak dusurulur, `trivial`
kural rank=1'de REDDEDER (rank=2'de gecer), CEFR bilinmeyen kelime
REDDETMEZ, siralama uyarisi HER onayli pakete duser.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.grammar import qa
from polyvo.modules.grammar.qa import level as level_qa


def _unit(sentences):
    """Testin ihtiyaci olan minimum `Unit` — `qa.run` yalnizca
    `unit.data["sentences"]`i (seq/ref/text/cefr) okur."""
    return Unit(key="test|g1", name="test", data={
        "owner": "test", "group_key": "g1", "sentences": sentences,
        "source_sha256": "irrelevant",
    })


def _sentence(seq, text, cefr=None, ref=None):
    return {"seq": seq, "ref": ref or f"g1:{seq}", "text": text, "cefr": cefr}


def _model_response(rules_by_seq, candidates_by_seq=None):
    candidates_by_seq = candidates_by_seq or {}
    return {"sentences": [
        {"seq": seq, "rules": rules, "candidates": candidates_by_seq.get(seq, [])}
        for seq, rules in rules_by_seq.items()
    ]}


def test_trigger_cumlede_yoksa_reddedilir():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "ran",
         "note": "This is a past simple action, though the word is wrong."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert "trigger_cumlede_yok" in result.reason


def test_gecerli_trigger_kabul_edilir():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action at a specific past time."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is True
    assert result.payload["rules"][0]["rule_id"] == "EN.TENSE.PAST_SIMPLE"


def test_katalog_disi_rule_id_reddedilir_ve_aday_dusurulmuyor_rules_alaninda():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.FOO.BAR", "trigger": "walked",
         "note": "Bilinmeyen bir kural."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert "rule_id_katalogda_yok" in result.reason


def test_reddedilen_pakette_de_adaylar_payloada_dusuyor():
    """Kurallar reddedilse bile modelin bildirdigi adaylar KAYBOLMAZ —
    `store.py` bunlari ayrica yazar."""
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response(
        {1: [{"rank": 1, "rule_id": "EN.FOO.BAR", "trigger": "walked",
             "note": "Bilinmeyen bir kural."}]},
        {1: [{"proposed_name": "New pattern", "trigger": "to the bank",
             "rationale": "not in catalog"}]},
    )
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert result.payload["candidates"][0]["proposed_name"] == "New pattern"


def test_trivial_kural_rank_1de_reddedilir():
    unit = _unit([_sentence(1, "The cat is here.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.ART.THE_DEFINITE", "trigger": "The",
         "note": "The definite article refers to a specific cat."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert "trivial_kural_rank_1de" in result.reason


def test_trivial_kural_rank_2de_gecer():
    unit = _unit([_sentence(1, "The cat quickly ran away.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "ran",
         "note": "A completed past action."},
        {"rank": 2, "rule_id": "EN.ART.THE_DEFINITE", "trigger": "The",
         "note": "Refers to a specific, already-known cat."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is True
    assert len(result.payload["rules"]) == 2


def test_cefr_bilinmeyen_reddetmez_sadece_uyari_yok():
    """Seviye BILINMIYORSA (cumlede `cefr=None`) seviye asimi uyarisi
    olusmaz ama paket yine de ONAYLANIR."""
    unit = _unit([_sentence(1, "She walked to the bank.", cefr=None)])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action at a specific past time."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is True
    assert "kural_seviye_ustu" not in (result.reason or "")


def test_seviye_ustu_kural_uyari_verir_reddetmez():
    """B2 seviyeli bir cumlede `assume_known_from=A2` kural (bu ogrenci
    icin coktan bilinir sayilir) UYARIR, reddetmez."""
    unit = _unit([_sentence(1, "She can come tomorrow.", cefr="B2")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.MODAL.CAN_ABILITY", "trigger": "can",
         "note": "Expresses present ability or possibility."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is True
    assert "kural_seviye_ustu" in result.reason


def test_siralama_uyarisi_her_onayli_pakete_duser():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action at a specific past time."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is True
    assert level_qa.RANKING_UNVERIFIED in result.reason


def test_kural_sayisi_sinir_disi_reddedilir():
    unit = _unit([_sentence(1, "She walked to the bank to pay a big old "
                            "bill this morning after the meeting ended.")])
    rules = [
        {"rank": i, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "note " + str(i)}
        for i in range(1, 5)               # 4 kural, sinir 3
    ]
    parsed = _model_response({1: rules})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert "kural_sayisi_sinir_disi" in result.reason


def test_rank_boslukli_reddedilir():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action at a specific past time."},
        {"rank": 3, "rule_id": "EN.ART.THE_DEFINITE", "trigger": "the",
         "note": "Refers to a specific, known bank."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert "rank_1_n_araligi_disinda" in result.reason


def test_cevap_json_degilse_reddedilir():
    unit = _unit([_sentence(1, "She walked to the bank.")])
    result = qa.run(None, unit)
    assert result.ok is False
    assert result.reason == "cevap_json_degil"


def test_cumle_sayisi_uyusmuyorsa_reddedilir():
    unit = _unit([_sentence(1, "She walked to the bank."),
                  _sentence(2, "He runs every day.")])
    parsed = _model_response({1: [
        {"rank": 1, "rule_id": "EN.TENSE.PAST_SIMPLE", "trigger": "walked",
         "note": "A completed action."},
    ]})
    result = qa.run(parsed, unit)
    assert result.ok is False
    assert result.reason == "cumle_sayisi_uyusmuyor"
