"""
REDO MATRISI — bir birime LLM cagrisi yapilip yapilmayacaginin TEK karari.

Saf fonksiyon (`decide`): girdi mevcut satir + mod + model rank'i, cikti bir
etiket. Veritabani yok, yan etki yok — bu yuzden plan asamasi da gercek kosu
da ayni fonksiyonu cagirir ve ayrisamazlar.

Matris (satir = depodaki durum, sutun = `--redo`):

    durum \\ mod      none            bad             only-bad
    satir yok        process         process         skip_missing
    insan (tier 0)   skip_human      skip_human      skip_human
    onayli           skip_done       skip_not_bad    skip_not_bad
    kotu, model>=    skip_outranked  skip_outranked  skip_outranked
    kotu, model<     process         process         process

Reddedilmis satir bir KARAR degil bir BOSLUKTUR — `none` modu da yeniden dener.
Rank kapisi HER modda acik: ayni modelle tekrar ayni cevabi/reddi uretir,
yalnizca kesin daha iyi model denemeye deger. Rank'i bilinmeyen kotu satir
EN KOTU sayilir — "bilmiyorum" bir yukseltmeyi engellemesin.
"""

from __future__ import annotations

from polyvo.core.jobs.store.policy import Existing, TIER_HUMAN

#: `--redo` secenekleri. Sirasi yardim metnindeki sirayla ayni.
REDO_MODES = ("none", "bad", "only-bad")

PROCESS = "process"

#: `process` verdiktinin alt sebepleri — para tam olarak NICIN harcaniyor.
PROCESS_REASON_LABELS = {
    "eksik": "satir yok — ilk uretim",
    "reddedilmis_onarim": "onceki deneme reddedilmis + bu model daha iyi",
}

SKIP_REASON_LABELS = {
    "skip_done": "kullanilabilir satir var (--redo none)",
    "skip_missing": "satir YOK — --redo only-bad onarim turudur, eksik uretmez",
    "skip_not_bad": "satir kotu isaretli degil",
    "skip_outranked": "kotu ama bu model yeni bilgi uretmez (esit/zayif model)",
    "skip_human": "insan karari — dokunulmaz",
}


def decide(existing: Existing | None, *, mode: str, model_rank: int) -> str:
    """Bu birim icin verdikt: `process` ya da bir `skip_*` etiketi."""
    if mode not in REDO_MODES:
        raise ValueError(f"bilinmeyen --redo modu: {mode} "
                         f"(gecerli: {', '.join(REDO_MODES)})")

    if existing is None:
        return "skip_missing" if mode == "only-bad" else PROCESS

    if existing.tier == TIER_HUMAN:
        return "skip_human"

    if existing.status == "approved":
        return "skip_done" if mode == "none" else "skip_not_bad"

    # Kotu satir: yalnizca KESIN daha iyi bir model yeniden denemeye deger.
    if existing.rank is not None and model_rank >= existing.rank:
        return "skip_outranked"
    return PROCESS


def process_reason(existing: Existing | None) -> str:
    """Bir birimin NICIN cagri aldigi — yalnizca raporlama icin."""
    return "eksik" if existing is None else "reddedilmis_onarim"
