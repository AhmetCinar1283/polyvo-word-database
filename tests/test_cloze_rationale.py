"""
Cloze ipucu/aciklama uretim kosusu testleri — HICBIR AG CAGRISI YOK.

Olculen sey V2-IS-5'in kabul kriterleridir: bu is `sense_cloze*` uc
tablosuna DOKUNMAZ, yalnizca ONAYLI paket islenir, anlam basina tam 3 ipucu
+ 12 aciklama yazilir, dogru cevabi/sikki iceren ipucu ve kalip aciklama
reddedilir, soru insan tarafindan degistirilince paket BAYAT olur.
"""

from __future__ import annotations

import ast
import os
import re

import pytest

from cloze_helpers import (
    FakeProvider, RATIONALE_ANSWER, TAG, L2, rationale_answer,
    run_cloze, run_rationale,
    seed_all,
)
from polyvo.core import paths
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import WriteRequest
from polyvo.core.jobs.store.policy import TIER_HUMAN
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.rationale import units as rationale_units
from polyvo.modules.cloze.rationale.store import ClozeRationaleStore

RATIONALE_ROOT = os.path.join(
    "src", "polyvo", "modules", "cloze", "rationale")


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _prepared():
    """Onayli bir cloze paketi uretir — rationale'in girdisi budur."""
    seed_all()
    run_cloze(FakeProvider())


def _rationale_status() -> tuple[str, str | None]:
    """`(status, reject_reason)` — tek paket varsayimiyla."""
    conn = schema.open_cloze_db()
    try:
        row = conn.execute(
            "SELECT status, reject_reason FROM sense_cloze_rationale"
        ).fetchone()
        return tuple(row)
    finally:
        conn.close()


def _counts() -> dict[str, int]:
    """Rationale deposundaki tablo satir sayilari."""
    conn = schema.open_cloze_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("sense_cloze_rationale", "sense_cloze_hint",
                             "sense_cloze_option_reason")}
    finally:
        conn.close()


def _cloze_counts() -> dict[str, int]:
    """Ingilizce cloze tablolarinin satir sayilari — DEGISMEMESI gereken."""
    conn = schema.open_cloze_db()
    try:
        return {name: conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                for name in ("sense_cloze", "sense_cloze_question",
                             "sense_cloze_option")}
    finally:
        conn.close()


# --- Kaynak denetimi (kabul olcutu S2) --------------------------------------

def test_rationale_sense_cloze_uc_tablosuna_dokunmaz():
    """KAYNAK DENETIMI: `rationale/` altinda `sense_cloze`/`_question`/
    `_option`e yazan HICBIR dosya olmamali (`_rationale`/`_hint`/
    `_option_reason` sonekli tablolar HARIC - onlar bu isin kendi tablosu)."""
    pattern = re.compile(
        r"(INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+"
        r"(sense_cloze|sense_cloze_question|sense_cloze_option)\b(?!_)",
        re.IGNORECASE)
    offenders = []
    for dirpath, _dirs, files in os.walk(RATIONALE_ROOT):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                if pattern.search(f.read()):
                    offenders.append(path)
    assert offenders == []


# --- Girdi kapisi (kabul olcutu) --------------------------------------------

def test_onaysiz_paket_rationale_birimi_uretmez():
    """Reddedilmis/hic uretilmemis cloze paketinin aciklanacak sorusu yoktur."""
    seed_all()
    assert rationale_units.load_units(TAG, L2) == []      # cloze hic kosmadi
    run_cloze(FakeProvider())
    assert [u.key for u in rationale_units.load_units(TAG, L2)] == [
        "en:bank:noun"]


def test_reddedilmis_cloze_paketi_rationale_birimi_uretmez():
    """Cloze paketi reddedilirse (bicim hatasi) rationale girdisi olmaz."""
    seed_all()
    run_cloze(FakeProvider(answer={"questions": []}))     # bicim hatasi -> red
    assert rationale_units.load_units(TAG, L2) == []


# --- Uretim + depo (kabul olcutu) -------------------------------------------

def test_rationale_uc_ipucu_on_iki_aciklama_yazar():
    """Anlam basina TAM 3 ipucu (soru basina 1) ve TAM 12 aciklama (soru
    basina 4)."""
    _prepared()
    run_rationale(FakeProvider(answer=rationale_answer()))

    counts = _counts()
    assert counts["sense_cloze_rationale"] == 1
    assert counts["sense_cloze_hint"] == 3
    assert counts["sense_cloze_option_reason"] == 12
    assert _rationale_status()[0] == "approved"


def test_rationale_kosusu_ingilizce_cloze_tablolarina_dokunmaz():
    """Uctan uca olcum: `sense_cloze*` satir sayilari kosudan once/sonra AYNI."""
    _prepared()
    before = _cloze_counts()
    run_rationale(FakeProvider(answer=rationale_answer()))
    assert _cloze_counts() == before


def test_dry_run_tek_kurus_harcamaz_tek_satir_yazmaz():
    """`--dry-run` hicbir cagri yapmaz, hicbir satir yazmaz."""
    _prepared()
    provider = FakeProvider(answer=rationale_answer())
    result = run_rationale(provider, dry_run=True)
    assert result.plan.paid_calls == 1
    assert provider.calls == []
    assert _counts() == {"sense_cloze_rationale": 0, "sense_cloze_hint": 0,
                         "sense_cloze_option_reason": 0}


def test_ikinci_kosu_sifir_odenecek_cagri():
    """Artimlilik: paket zaten onayliyken ikinci kosu `paid_calls = 0`."""
    _prepared()
    run_rationale(FakeProvider(answer=rationale_answer()))
    second = FakeProvider(answer=rationale_answer())
    result = run_rationale(second, dry_run=True)
    assert result.plan.paid_calls == 0
    assert second.calls == []


def test_insan_satiri_varken_cagri_istenmez():
    """Tier 0 (insan) satir varken bu birime cagri YAPILMAZ."""
    _prepared()
    store = ClozeRationaleStore()
    unit = rationale_units.load_units(TAG, L2)[0]
    store.save(JobContext(tag=TAG, l2=L2), WriteRequest(
        unit=unit, payload={"hints": [], "reasons": []}, status="approved",
        tier=TIER_HUMAN, model_label=None), None)
    store.commit()
    store.close()

    result = run_rationale(FakeProvider(answer=rationale_answer()),
                           dry_run=True)
    assert result.plan.skipped() == {"skip_human": 1}


# --- QA: ipucu (kabul olcutu) -----------------------------------------------

def test_dogru_cevabi_iceren_ipucu_reddedilir():
    """Ipucu hedef kelimeyi (ya da bir bicimini) icerirse REDDEDILIR."""
    bad = rationale_answer()
    bad["questions"][0]["hint"] = "Think about where you keep your bank money."
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "ipucu_dogru_cevabi_iceriyor")
    assert _counts()["sense_cloze_hint"] == 0


def test_sik_metnini_iceren_ipucu_reddedilir():
    """Ipucu herhangi bir sikkin metnini BIREBIR icerirse REDDEDILIR."""
    bad = rationale_answer()
    bad["questions"][0]["hint"] = "This has nothing to do with a spoon at all."
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "ipucu_sik_metnini_iceriyor")


def test_konuma_gonderme_yapan_ipucu_reddedilir():
    """Ipucu sikka KONUMUYLA gonderme yaparsa REDDEDILIR (pozisyonel kalip)."""
    bad = rationale_answer()
    bad["questions"][0]["hint"] = "Just pick the first option, it fits well."
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "ipucu_konuma_gonderme_yapiyor")


# --- QA: aciklama (kabul olcutu) --------------------------------------------

def test_ayni_kalipli_dort_aciklama_reddedilir():
    """Bir sorunun dort aciklamasi (normalize edildiginde) AYNIYSA REDDEDILIR."""
    bad = rationale_answer()
    # Dordunun de KENDI kelimesini icermesi icin hepsi ayni cumleye TUM
    # sik kelimelerini tasir — yalnizca tekduzelik kapisini olcmek icin.
    same = ("This choice among bank, spoon, cloud, and chair does not fit "
           "the sentence well at all here today.")
    for r in bad["questions"][0]["reasons"]:
        r["reason"] = same
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "dort_aciklama_ayni_kalip")


def test_kendi_kelimesini_icermeyen_aciklama_reddedilir():
    """Aciklama, acikladigi sikkin KENDI kelimesini icermezse REDDEDILIR."""
    bad = rationale_answer()
    bad["questions"][0]["reasons"][1]["reason"] = (
        "This one is a kitchen utensil, unrelated to keeping money safe.")
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == (
        "rejected", "aciklama_kendi_sikkinin_kelimesini_icermiyor")


def test_var_olmayan_sikka_baglanan_aciklama_reddedilir():
    """Aciklama, o soruda VAR OLMAYAN bir sik metnine baglanmissa REDDEDILIR."""
    bad = rationale_answer()
    bad["questions"][0]["reasons"][1]["option"] = "umbrella"
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "aciklama_olmayan_sikka_bagli")


def test_eksik_soru_sayisi_reddedilir():
    """Uc soru degilse (bicim hatasi) REDDEDILIR."""
    bad = rationale_answer(questions=RATIONALE_ANSWER["questions"][:2])
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "soru_sayisi_uc_degil")


def test_eksik_aciklama_sayisi_reddedilir():
    """Bir soruda 4 aciklama yoksa (bicim hatasi) REDDEDILIR."""
    bad = rationale_answer()
    bad["questions"][0]["reasons"] = bad["questions"][0]["reasons"][:3]
    _prepared()
    run_rationale(FakeProvider(answer=bad))
    assert _rationale_status() == ("rejected", "aciklama_sayisi_dort_degil")


# --- QA: seviye — UYARIR, REDDETMEZ (kabul olcutu S6) -----------------------

def _warnings() -> str:
    """Tek rationale satirinin uyari metni."""
    conn = schema.open_cloze_db()
    try:
        return conn.execute(
            "SELECT warnings FROM sense_cloze_rationale").fetchone()[0] or ""
    finally:
        conn.close()


def test_cefri_bilinmeyen_anlam_reddedilmez_uyari_alir():
    """Kabul olcutu S6: anlamin CEFR'i YOKSA paket ONAYLANIR, yalnizca
    'seviye olculemedi' uyarisi duser."""
    seed_all(universe=(("bank", "noun", None, 5),))
    run_cloze(FakeProvider())
    run_rationale(FakeProvider(answer=rationale_answer()))

    assert _rationale_status() == ("approved", None)
    assert "ust_dil_seviyesi_olculemedi_cefr_bilinmiyor" in _warnings()


def test_cefri_bilinen_anlam_da_seviye_yuzunden_reddedilmez():
    """CEFR bilinse bile ust-dil seviyesi OLCULEMEZ: uyari duser, red yok."""
    _prepared()
    run_rationale(FakeProvider(answer=rationale_answer()))

    assert _rationale_status() == ("approved", None)
    assert "ust_dil_seviyesi_dogrulanamadi_cefr_a2" in _warnings()


# --- Bayatlik (kabul olcutu S12, S17) ---------------------------------------

def test_soru_degisince_rationale_bayat_olur_yeniden_islenir():
    """Cloze sorusu insan tarafindan DEGISTIRILINCE eski aciklama BAYATTIR
    ve birim yeniden islenebilir sayilir."""
    _prepared()
    run_rationale(FakeProvider(answer=rationale_answer()))

    conn = schema.open_cloze_db()
    with conn:
        conn.execute("UPDATE sense_cloze_question SET sentence = ?"
                     " WHERE seq = 1",
                     ("I put my savings in a bank every month.",))
    conn.close()

    store = ClozeRationaleStore()
    existing = store.load_existing(JobContext(tag=TAG, l2=L2))
    store.close()
    assert existing == {}                    # bayat satir hic donmedi

    result = run_rationale(FakeProvider(answer=rationale_answer()),
                           dry_run=True)
    assert result.plan.paid_calls == 1       # yeniden islenebilir


# --- Kaynak yapisi -----------------------------------------------------------

def test_rationale_docstringleri_var():
    """Her dosyada Turkce modul docstring'i var (proje kurali)."""
    missing = []
    for dirpath, _dirs, files in os.walk(RATIONALE_ROOT):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            tree = ast.parse(open(path, encoding="utf-8").read())
            if ast.get_docstring(tree) is None:
                missing.append(path)
    assert missing == []
