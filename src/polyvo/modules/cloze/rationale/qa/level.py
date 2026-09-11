"""
SEVIYE kapisi — ipucu/aciklama kelime dagarcigi anlamin CEFR'ini asiyor mu.

Bu kapi HICBIR SEY REDDETMEZ, yalnizca UYARIR (V2-IS-5 §6.7). Gerekce:
ipucu ve aciklama SORU METNI DEGIL, ogrenciye konusan UST-DILDIR ve zaten
L1'e cevrilecektir; ustelik evrenin buyuk bolumunde kelimenin CEFR'i hic
bilinmez (1000 kelimenin ~160'inda seviye yok). Olculemeyen bir seyi
reddetmek, `qa/distractor.py`nin bilerek kacindigi hatanin aynisi olurdu.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit


def check(questions: list[dict], unit: Unit) -> tuple[str | None, list[str]]:
    """(red_sebebi, uyarilar) doner — red_sebebi HER ZAMAN None'dir."""
    cefr = unit.data.get("cefr")
    if not cefr:
        # Anlamin seviyesi bilinmiyor: kiyaslanacak esik yok, RED YOK.
        return None, ["ust_dil_seviyesi_olculemedi_cefr_bilinmiyor"]
    return None, [f"ust_dil_seviyesi_dogrulanamadi_cefr_{cefr.lower()}"]
