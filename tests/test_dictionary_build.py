"""
Katman 1 testleri — sozluk aday havuzu.

Uc sey olculur, ucu de eski repoda kirilmis seylerdir:

  1. NORMALIZE kurallari (POS/CEFR/varyant) — kaynaklar arasi uyusmazligin
     tek bir yerde ve BEKLENEN yonde cozuldugu.
  2. SESSIZ ELEME YOK — dusen her satir bir sebeple `unresolved`'a yazilir.
  3. KESIF — her ingestor `sources.SOURCES`'ta kayitli, her indirilebilir
     kaynagin hedef dosya adi var.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from polyvo.dictionary import app as dictionary_app, sources
from polyvo.dictionary.build import merge, normalize, word_cleaner
from polyvo.dictionary.build.ingestors import Candidate, Evidence, find_ingestors


# ── normalize ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("noun", "noun"),
    ("Adjective", "adj"),
    ("modal auxiliary", "modal"),
    ("be-verb", "verb"),
    ("infinitive-to", "particle"),
    ("vern", "verb"),          # Octanove yazim hatasi, ACIKCA duzeltilir
    ("", None),
    (None, None),
    ("wugword", None),         # taninmayan etiket SESSIZCE eslenmez
])
def test_normalize_pos(raw, expected):
    assert normalize.normalize_pos(raw) == expected


def test_every_mapped_pos_is_canonical():
    """POS_MAP'in cikti kumesi kanonik kumeyi ASAMAZ — asarsa kimlik anahtari
    (K1) sessizce genisler."""
    assert set(normalize.POS_MAP.values()) <= normalize.CANONICAL_POS
    assert set(normalize.POS_TYPO_FIXES.values()) <= set(normalize.POS_MAP)


@pytest.mark.parametrize("raw,expected", [
    ("  Bank ", "bank"),
    ("turn to ", "turn to"),
    ("don’t", "don't"),      # tipografik kesme duzeltilir
    ("all   right", "all right"),
])
def test_normalize_headword(raw, expected):
    assert normalize.normalize_headword(raw) == expected


def test_merge_cefr_lowest_wins():
    """K6: dusuk seviye kazanir. `abundance` B1'e karsi C2 ise B1'dir."""
    assert normalize.merge_cefr("C2", "B1") == "B1"
    assert normalize.merge_cefr(None, "A2") == "A2"
    assert normalize.merge_cefr(None, "gecersiz") is None


def test_merge_tier_lowest_wins():
    assert normalize.merge_tier(3, 1, None) == 1
    assert normalize.merge_tier(None, None) is None


def test_split_variants():
    assert normalize.split_variants("analyze/analyse") == ["analyze", "analyse"]
    assert normalize.split_variants("bank") == ["bank"]
    assert normalize.split_variants("") == []


# ── eleme ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("word,reason", [
    ("bank", None),
    ("a", None),
    ("well-being", None),
    ("all right", None),
    ("a.m.", None),
    ("café", None),          # aksanli alinti kelime ELENMEZ
    ("b", "tek_harf"),
    ("covid-19", "rakam_iceriyor"),
    ("'s", "kelime_disi_karakter"),
    ("u.s.a.", "kisaltma"),
    ("as far as i", "cok_uzun"),
])
def test_word_cleaner(word, reason):
    assert word_cleaner.reject_reason(word) == reason


# ── kesif ve kayit defteri ────────────────────────────────────────────────

def test_every_ingestor_is_registered():
    for ing in find_ingestors():
        assert ing.source_name in sources.SOURCES, ing.source_name


def test_downloadable_sources_have_filenames():
    for src in sources.SOURCES.values():
        if src.url:
            assert src.filename, src.name


def test_app_exposes_build_command():
    assert dictionary_app.APP.command("build") is not None
    assert dictionary_app.APP.command("download") is not None
    assert dictionary_app.APP.depends == ["core"]


# ── birlestirme ───────────────────────────────────────────────────────────

class _Fake:
    """Testte kaynak dosyasi degil, satir listesi veren ingestor."""

    def __init__(self, source_name, cands=(), evid=()):
        self.source_name = source_name
        self._c, self._e = list(cands), list(evid)

    def candidates(self):
        return iter(self._c)

    def evidence(self):
        return iter(self._e)


def _build(tmp_path, ingestors, tier_max=3):
    db = os.path.join(tmp_path, "lexicon.sqlite")
    report = merge.build(db, tier_max=tier_max, ingestors=ingestors)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return report, con


def test_blank_pos_row_dissolves_into_typed_rows(tmp_path):
    """NGSL POS'suz gelir, CEFR-J POS'lu. Sonuc TEK satir olmali ve tier
    NGSL'den (1) gelmeli — POS'suz satir kendi basina aday degildir."""
    report, con = _build(tmp_path, [
        _Fake("ngsl", [Candidate("bank", freq_rank=100)]),
        _Fake("cefrj", [Candidate("bank", raw_pos="noun", cefr="A2")]),
    ])
    rows = con.execute("SELECT * FROM candidates").fetchall()
    assert len(rows) == 1
    assert (rows[0]["headword"], rows[0]["pos"], rows[0]["tier"]) == ("bank", "noun", 1)
    assert rows[0]["cefr"] == "A2"
    assert set(rows[0]["sources"].split(",")) == {"ngsl", "cefrj"}
    assert report.pos_missing == 0


def test_pos_recovered_from_evidence(tmp_path):
    """K7: baska POS kaynagi yoksa kanit (legacy_dist) kullanilir."""
    report, con = _build(tmp_path, [
        _Fake("ngsl", [Candidate("abolish")]),
        _Fake("legacy_dist", evid=[Evidence("abolish", kind="pos", payload="verb")]),
    ])
    row = con.execute("SELECT pos, pos_source FROM candidates").fetchone()
    assert (row["pos"], row["pos_source"]) == ("verb", "legacy_dist")
    assert report.pos_recovered == 1


def test_pos_missing_is_reported_not_dropped(tmp_path):
    """POS'u hicbir kaynakta olmayan kelime ATILMAZ, raporlanir."""
    report, con = _build(tmp_path, [_Fake("ngsl", [Candidate("wug")])])
    row = con.execute("SELECT headword, pos FROM candidates").fetchone()
    assert (row["headword"], row["pos"]) == ("wug", None)
    assert report.pos_missing == 1
    reasons = [r[0] for r in con.execute("SELECT reason FROM unresolved")]
    assert reasons == ["pos_kaynagi_yok"]


def test_rejected_word_lands_in_unresolved_with_reason(tmp_path):
    _, con = _build(tmp_path, [
        _Fake("ngsl", [Candidate("bank", raw_pos="noun"), Candidate("covid-19")]),
    ])
    row = con.execute("SELECT headword, reason FROM unresolved").fetchone()
    assert (row["headword"], row["reason"]) == ("covid-19", "rakam_iceriyor")


def test_unknown_pos_keeps_word_but_reports_label(tmp_path):
    """Etiket taninmiyorsa KELIME degil ETIKET dusuruluru; ikisi ayri seydir."""
    _, con = _build(tmp_path, [
        _Fake("cefrj", [Candidate("bank", raw_pos="wugword")]),
        _Fake("legacy_dist", evid=[Evidence("bank", kind="pos", payload="noun")]),
    ])
    assert con.execute("SELECT pos FROM candidates").fetchone()["pos"] == "noun"
    assert con.execute(
        "SELECT count(*) FROM unresolved WHERE reason='pos_taninmiyor'"
    ).fetchone()[0] == 1


def test_tier_filter_is_scope_not_defect(tmp_path):
    """Kapsam disi satir `unresolved`'a YAZILMAZ — istenmemistir, kusurlu degil."""
    _, con = _build(tmp_path, [
        _Fake("ngsl", [Candidate("bank", raw_pos="noun")]),
        _Fake("octanove", [Candidate("abate", raw_pos="verb")]),
    ], tier_max=1)
    heads = [r[0] for r in con.execute("SELECT headword FROM candidates")]
    assert heads == ["bank"]
    assert con.execute("SELECT count(*) FROM unresolved").fetchone()[0] == 0


def test_evidence_outside_universe_is_dropped(tmp_path):
    """ipa-dict 125 bin satir tasir; evrende olmayan baslik saklanmaz."""
    report, con = _build(tmp_path, [
        _Fake("ngsl", [Candidate("bank", raw_pos="noun")]),
        _Fake("ipa_dict", evid=[Evidence("bank", "ipa", "/baenk/"),
                                Evidence("zyzzyva", "ipa", "/zizive/")]),
    ])
    payloads = [r[0] for r in con.execute("SELECT payload FROM evidence")]
    assert payloads == ["/baenk/"]
    assert report.evidence_out_of_universe == 1


def test_source_meta_carries_license(tmp_path):
    """Lisans ciktiyla BIRLIKTE seyahat eder: sevk kapisi (Adim 6) buna bakar."""
    _, con = _build(tmp_path, [_Fake("ngsl", [Candidate("bank", raw_pos="noun")])])
    row = con.execute("SELECT license, shippable FROM source_meta").fetchone()
    assert row["license"] == sources.get("ngsl").license
    assert row["shippable"] == 0


def test_build_is_deterministic(tmp_path):
    """Ayni girdi -> BIREBIR ayni dosya. Ucuz katmanin tanimi budur."""
    ings = [_Fake("ngsl", [Candidate("bank", raw_pos="noun"),
                           Candidate("apple", raw_pos="noun")]),
            _Fake("ipa_dict", evid=[Evidence("bank", "ipa", "/baenk/")])]
    db = os.path.join(tmp_path, "lexicon.sqlite")
    merge.build(db, tier_max=3, ingestors=ings)
    first = open(db, "rb").read()
    merge.build(db, tier_max=3, ingestors=ings)
    assert open(db, "rb").read() == first
