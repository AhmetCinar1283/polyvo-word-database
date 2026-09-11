"""
`sense_cloze_translation` (+ `_sentence`) deposu — bu iki tablonun TEK yazicisi.

Ingilizce cloze tablolarina (`sense_cloze`, `_question`, `_option`) BURADAN
HIC dokunulmaz: ceviri odenmis soruyu yeniden uretmez. Siklar cevrilmedigi
icin `sense_cloze_option`in bu kosuyla hicbir isi yoktur.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.cloze import schema

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class ClozeTranslationStore(ArtifactStore):
    """Cloze cumlelerinin L1 cevirisinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_cloze_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """Varyanta duyarli anahtarla `Existing` — TEK tablo, TEK sorgu.

        Anahtar `stable_key::<l1>` olur; Ingilizce paketin ham anahtariyla
        CAKISMAZ, yani bir dilin cevirisi digerini etkilemez."""
        rows = self.conn.execute(
            "SELECT c.stable_key, t.status, t.tier, t.model"
            " FROM sense_cloze_translation t"
            " JOIN sense_cloze c ON c.sense_id = t.sense_id"
            " WHERE t.l1 = ?", (ctx.l1,)).fetchall()
        return {
            keys.compose_key(stable_key, ctx.variant):
                Existing(tier=tier, status=status, rank=rank_for(model))
            for stable_key, status, tier, model in rows
        }

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis ceviriyi yazar; reddedilirse ICERIK yazilmaz."""
        sense_id = request.unit.data["sense_id"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_cloze_translation (sense_id, l1,"
            " status, reject_reason, warnings, tier, source, model,"
            " prompt_hash, updated_at) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, ctx.l1, request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version))

        self.conn.execute(
            "DELETE FROM sense_cloze_translation_sentence"
            " WHERE sense_id = ? AND l1 = ?", (sense_id, ctx.l1))
        if not approved:
            return
        self.conn.executemany(
            "INSERT INTO sense_cloze_translation_sentence (sense_id, l1, seq,"
            " sentence, tier, source) VALUES (?,?,?,?,?,?)",
            [(sense_id, ctx.l1, seq, sentence, request.tier, SOURCE_MODEL)
             for seq, sentence in enumerate(request.payload["sentences"], start=1)])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
