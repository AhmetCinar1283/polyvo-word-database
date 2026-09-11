"""
`sense_usage_note` deposu — bu tablonun TEK yazicisi.

Kartin kendisine (`sense_cards`) BURADAN HIC dokunulmaz: not karttan AYRI bir
satir ailesidir (Is 3). Bos not da GECERLI bir onaylanmis satirdir — ikinci
kosuda `skip_done` boyle calisir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.lexicon_card import schema

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class LexiconNoteStore(ArtifactStore):
    """`sense_usage_note`un kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_lexicon_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`stable_key -> Existing`, TEK sorgu. Not dile bagli degildir,
        anahtar HAM `stable_key`dir (`ctx.variant` bu koşuda hep bos)."""
        rows = self.conn.execute(
            "SELECT sc.stable_key, n.status, n.tier, n.model"
            " FROM sense_usage_note n"
            " JOIN sense_cards sc ON sc.sense_id = n.sense_id").fetchall()
        return {
            stable_key: Existing(tier=tier, status=status, rank=rank_for(model))
            for stable_key, status, tier, model in rows
        }

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis notu yazar. Reddedilen cevabin ICERIGI yazilmaz —
        satir yalnizca 'burasi kotu' demek icin durur."""
        sense_id = request.unit.data["card"]["sense_id"]
        payload = request.payload
        note = payload.get("note", "") if request.status == "approved" else ""
        reason = payload.get("reason") if request.status == "approved" else None

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_usage_note (sense_id, note, reason,"
            " status, reject_reason, tier, source, model, prompt_hash,"
            " updated_at) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, note, reason, request.status, request.reject_reason,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version))

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
