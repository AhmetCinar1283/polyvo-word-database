"""
REDO MATRISI — bir birime LLM cagrisi yapilip yapilmayacaginin TEK karari.

Saf fonksiyon (`decide`): girdi mevcut satir + mod + model rank'i + force
bayragi, cikti bir etiket. Veritabani yok, yan etki yok — bu yuzden plan
asamasi da gercek kosu da ayni fonksiyonu cagirir ve ayrisamazlar.

Matris (satir = depodaki durum, sutun = `--redo`, `force=None`):

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

RANK KAPISI PARA icin var, DOGRULUK icin degil: ayni prompt + ayni model =
onbellekten ayni cevap gelir, yani odenen para bosa gider — QA KURALLARI
DEGISTIYSE BILE. Bu, olculmus bir kor noktadir: `qa/` gevsetildiginde
(2026-09-07) onceden reddedilmis satirlar hicbir moddo yeniden
DEGERLENDIRILMEZ, cunku skip_outranked plan asamasinda hicbir prompt
kurmadan, hicbir onbellek yoklamasi yapmadan atlar (`plan/planner.py`).
Bunun tek cikisi FORCE'tur — kullanicinin "daha iyi model yok, yine de
dene" karari, rank karsilastirmasini BILEREK bir kenara koyar:

    force=None    rank kapisi normal (yukaridaki matris)
    force="self"  rank kapisi yalnizca AYNI rank icin acilir (model_rank ==
                  existing.rank) — "elimdeki en iyi model bu, yine dene"
    force="all"   rank kapisi TAMAMEN acilir (daha zayif model, daha once
                  DAHA IYI bir model tarafindan reddedilmis satiri bile
                  dener) — en gevsek, en pahali secenek

Force ONAYLI satira ASLA dokunmaz (`skip_done`/`skip_not_bad` degismez) ve
insan satirina ASLA dokunmaz — bu iki kural hicbir bayrakla gevsetilmez,
`store/policy.py::should_write` zaten ayni satirin uzerine yazilmasini
engeller. Force yalnizca "denenir mi" sorusunu genisletir, "yazilir mi"
sorusuna karismaz.

ZORLANAN BIR BIRIM IKI ASAMADAN GECER (bkz. `engine/revalidate.py`):

  1. ONAY ONCESI, BEDAVA: onbellekteki eski cevap YENI QA'dan gecirilir.
     Gecerse satir guncellenir ve birim `skip_revalidated` olur — kullanici
     onay istemine "H" dese bile bu duzelme KALICIDIR. Prompt/QA duzeltip
     yeniden kosmanin normal yolu budur.
  2. ONAYDAN SONRA, PARALI: 1. asamada hala reddedilen birim MODELE GIDER ve
     onbellek OKUMASI atlanir (`bypass_cache`) — yoksa ayni cevap geri gelir
     ve --force hicbir sey degistirmezdi.
"""

from __future__ import annotations

from polyvo.core.jobs.store.policy import Existing, TIER_HUMAN

#: `--redo` secenekleri. Sirasi yardim metnindeki sirayla ayni.
REDO_MODES = ("none", "bad", "only-bad")

#: `--force` secenekleri. `None` (bayrak verilmez) rank kapisini degistirmez.
FORCE_MODES = ("self", "all")

PROCESS = "process"

#: `--force` yuzunden islenen birimin sebep etiketi. Zorlanan birimi TANIYAN
#: tek isaret budur: onbellek atlama da (`engine/loop.py`) onay oncesi
#: yeniden degerlendirme de (`engine/revalidate.py`) bu sebebe bakar.
REASON_FORCED = "reddedilmis_zorlanmis"

#: Onbellekteki cevabi YENI QA'dan gecip cagri gerektirmeyen birim.
SKIP_REVALIDATED = "skip_revalidated"

#: `process` verdiktinin alt sebepleri — para tam olarak NICIN harcaniyor.
PROCESS_REASON_LABELS = {
    "eksik": "satir yok — ilk uretim",
    "reddedilmis_onarim": "onceki deneme reddedilmis + bu model daha iyi",
    REASON_FORCED: "onceki deneme reddedilmis + --force ile zorlandi "
                   "(onbellek ATLANIR, taze cevap alinir)",
}

SKIP_REASON_LABELS = {
    "skip_done": "kullanilabilir satir var (--redo none)",
    "skip_missing": "satir YOK — --redo only-bad onarim turudur, eksik uretmez",
    "skip_not_bad": "satir kotu isaretli degil",
    "skip_outranked": "kotu ama bu model yeni bilgi uretmez (esit/zayif model) "
                      "— --force self/all ile zorlanabilir",
    "skip_human": "insan karari — dokunulmaz",
    SKIP_REVALIDATED: "onbellekteki cevap YENI QA'dan gecti — cagri gerekmedi",
}


def _naturally_better(existing: Existing, *, model_rank: int) -> bool:
    """Force'suz bile rank kapisini acacak KESIN daha iyi model mi."""
    return existing.rank is None or model_rank < existing.rank


def _rank_gate_open(existing: Existing, *, model_rank: int,
                    force: str | None) -> bool:
    """Kotu bir satir icin rank kapisi acik mi (yeniden denenmeye deger mi)."""
    if _naturally_better(existing, model_rank=model_rank):
        return True
    if force == "all":
        return True                             # her sey zorlanir
    if force == "self" and model_rank == existing.rank:
        return True                             # yalnizca kendi seviyesi
    return False


def decide(existing: Existing | None, *, mode: str, model_rank: int,
          force: str | None = None) -> str:
    """Bu birim icin verdikt: `process` ya da bir `skip_*` etiketi."""
    if mode not in REDO_MODES:
        raise ValueError(f"bilinmeyen --redo modu: {mode} "
                         f"(gecerli: {', '.join(REDO_MODES)})")
    if force is not None and force not in FORCE_MODES:
        raise ValueError(f"bilinmeyen --force modu: {force} "
                         f"(gecerli: {', '.join(FORCE_MODES)})")

    if existing is None:
        return "skip_missing" if mode == "only-bad" else PROCESS

    if existing.tier == TIER_HUMAN:
        return "skip_human"

    if existing.status == "approved":
        return "skip_done" if mode == "none" else "skip_not_bad"

    # Kotu satir: yalnizca KESIN daha iyi bir model (ya da --force) yeniden
    # denemeye deger.
    if not _rank_gate_open(existing, model_rank=model_rank, force=force):
        return "skip_outranked"
    return PROCESS


def process_reason(existing: Existing | None, *, model_rank: int | None = None,
                   force: str | None = None) -> str:
    """Bir birimin NICIN cagri aldigi — yalnizca raporlama icin.

    `_naturally_better` uzerinden `decide` ile AYNI parcayi paylasir: burada
    yeniden yazilan tek sey "force olmasaydi da acik miydi" sorusu, rank
    karsilastirmasinin kendisi degil."""
    if existing is None:
        return "eksik"
    if (force is not None and model_rank is not None
            and not _naturally_better(existing, model_rank=model_rank)):
        return REASON_FORCED
    return "reddedilmis_onarim"
