"""
YAZMA KAPISI — "bu satirin uzerine yazabilir miyim?" sorusunun TEK cevabi.
Saf fonksiyon (DB'siz) — plan asamasi da ayni kapiyi TEK KURUS ODEMEDEN cagirir.

Kurallar, sirasiyla:
  1. satir yoksa                              -> YAZ
  2. yeni satir INSAN (tier 0)                -> HER ZAMAN YAZ
  3. mevcut satir INSAN, yeni makine          -> ASLA YAZMA
  4. mevcut tier daha guvenilir               -> YAZMA
  5. mevcut 'approved', yeni degil            -> ASLA YAZMA
  6. mevcut 'approved' degil, yeni 'approved' -> YAZ
  7. ayni statude, yeni model KESIN daha iyi  -> YAZ
  8. aksi halde                               -> YAZMA

Karar bir `bool` degil `WriteDecision` doner — SEBEP de tasinir, rapor
satirini sebebi ureten yer yazar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

#: tier: 0 = insan, 1/2 = sozluk tohumu, 3 = model. Kucuk olan kazanir.
TIER_HUMAN = 0
TIER_DICT_SEED = 1
TIER_MODEL = 3


@dataclass(frozen=True)
class Existing:
    """Depoda duran satirin KARAR icin gereken uc alani (tam satir degil)."""

    tier: int
    status: str = "approved"
    rank: int | None = None


class WriteDecision(NamedTuple):
    """Kapinin karari + INSANIN OKUYACAGI sebep."""

    write: bool
    reason: str


def should_write(existing: Existing | None, *, new_tier: int,
                 new_status: str, new_rank: int | None) -> WriteDecision:
    """Yeni satirin mevcut satiri ezip ezemeyecegini kurallara gore soyler."""
    if existing is None:
        return WriteDecision(True, "satir_yok")
    if new_tier == TIER_HUMAN:
        return WriteDecision(True, "insan_karari")
    if existing.tier == TIER_HUMAN:
        return WriteDecision(False, "mevcut_insan_karari")
    if existing.tier < new_tier:
        return WriteDecision(False, "mevcut_daha_guvenilir_tier")
    if existing.status == "approved" and new_status != "approved":
        return WriteDecision(False, "onayliyi_reddedilenle_ezme")
    if existing.status != "approved" and new_status == "approved":
        return WriteDecision(True, "bosluk_dolduruldu")
    if new_rank is None or existing.rank is None:
        return WriteDecision(False, "model_karsilastirilamadi")
    if new_rank < existing.rank:
        return WriteDecision(True, "daha_iyi_model")
    return WriteDecision(False, "esit_ya_da_zayif_model")
