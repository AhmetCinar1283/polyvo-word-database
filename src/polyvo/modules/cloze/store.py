"""
`sense_cloze` (+ `_question`, `_option`) deposu — bu uc tablonun TEK yazicisi.

`lexicon_card`in hicbir tablosuna dokunmaz: cloze OKUR, yazmaz. Uc soru TEK
TRANSACTION'da yazilir — yarim bir paket (iki soru) hicbir zaman gorunmez.

REDDEDILEN PAKETTE ICERIK YAZILMAZ: yalnizca `sense_cloze` satiri
`status='rejected'` + `reject_reason` ile durur. Onayli pakette ayni motor
alani (`reason`) UYARILARI tasir — `warnings` sutununa oraya yazilir, cunku
"QA'nin olcemedigi sey" kaybolmamali (celdirici uyarilari).
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


class ClozeStore(ArtifactStore):
    """Uc soruluk cloze paketinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_cloze_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`stable_key -> Existing`, TEK sorgu. `stable_key` bu tabloda kendi
        sutunudur — baska bir app'in tablosuna JOIN atmak gerekmez."""
        rows = self.conn.execute(
            "SELECT stable_key, status, tier, model FROM sense_cloze").fetchall()
        return {
            keys.compose_key(stable_key, ctx.variant):
                Existing(tier=tier, status=status, rank=rank_for(model))
            for stable_key, status, tier, model in rows
        }

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis paketi yazar; reddedilirse ICERIK yazilmaz."""
        data = request.unit.data
        sense_id = data["sense_id"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_cloze (sense_id, stable_key, status,"
            " reject_reason, warnings, tier, source, model, prompt_hash,"
            " updated_at) VALUES (?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, data["stable_key"], request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version))

        # Once silinir: eski bir paketin ucuncu sorusu yeni pakette oksuz kalmasin.
        self.conn.execute("DELETE FROM sense_cloze_question WHERE sense_id = ?",
                          (sense_id,))
        self.conn.execute("DELETE FROM sense_cloze_option WHERE sense_id = ?",
                          (sense_id,))
        if not approved:
            return

        for question in request.payload.get("questions", []):
            seq = question["seq"]
            self.conn.execute(
                "INSERT INTO sense_cloze_question (sense_id, seq, difficulty,"
                " sentence, answer, tier, source) VALUES (?,?,?,?,?,?,?)",
                (sense_id, seq, question["difficulty"], question["sentence"],
                 question["answer"], request.tier, SOURCE_MODEL))
            answer = question["answer"].strip().lower()
            self.conn.executemany(
                "INSERT INTO sense_cloze_option (sense_id, seq, opt_seq, text,"
                " is_answer) VALUES (?,?,?,?,?)",
                [(sense_id, seq, opt_seq, text,
                  1 if text.strip().lower() == answer else 0)
                 for opt_seq, text in enumerate(question["options"], start=1)])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
