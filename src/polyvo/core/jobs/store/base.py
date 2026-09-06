"""
Modul deposunun taban sinifi — kapiyi ATLANAMAZ kilan sey. Motor uretilen
icerigin SEKLINI bilmez, sadece yazma kapisini bilir; bu yuzden kapi bir
yardimci degil `save`in (TABAN SINIF, final) kendisidir — modul yalnizca
`_write_row`i (private) uygular, kapiyi kendisi cagiramaz/atlayamaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from polyvo.core.jobs.base import JobContext, Unit
from polyvo.core.jobs.store.policy import (
    Existing,
    TIER_MODEL,
    WriteDecision,
    should_write,
)


@dataclass
class WriteRequest:
    """Kapiya sunulan yazma istegi: yuk + kararin dayandigi ustveri."""

    unit: Unit
    payload: dict
    status: str = "approved"
    tier: int = TIER_MODEL
    rank: int | None = None
    model_label: str | None = None
    prompt_version: str | None = None
    reject_reason: str | None = None
    extra: dict = field(default_factory=dict)


class ArtifactStore(ABC):
    """Odenmis kararlarin kalici deposu. Alt sinif iki metodu uygular."""

    @abstractmethod
    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`stable_key -> Existing`. TEK sorguda okunur; plan bunu kullanir."""

    @abstractmethod
    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapiyi GECMIS bir yazma. Yalnizca `save` cagirir."""

    def commit(self) -> None:
        """Bekleyen yazmalari kalicilastirir. Varsayilan: hicbir sey."""
        return None

    def close(self) -> None:
        """Depoyu kapatir. Varsayilan: hicbir sey."""
        return None

    def save(self, ctx: JobContext, request: WriteRequest,
             existing: Existing | None) -> WriteDecision:
        """TEK yazma yolu: once kapi, sonra (izin varsa) `_write_row`."""
        decision = should_write(existing, new_tier=request.tier,
                                new_status=request.status, new_rank=request.rank)
        if decision.write:
            self._write_row(ctx, request)
        return decision
