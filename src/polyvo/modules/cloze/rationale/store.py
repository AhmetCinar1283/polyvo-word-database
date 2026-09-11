"""
`sense_cloze_rationale` (+ `_hint`, `_option_reason`) deposu — bu UC
tablonun TEK yazicisi.

`sense_cloze`, `sense_cloze_question`, `sense_cloze_option` tablolarina
BURADAN HIC dokunulmaz (V2-IS-5 §2): bu is cloze'un USTUNE yazar, ICINE
degil.

BAYATLIK (§12): `load_existing` depodaki `question_sha256`i sorunun O ANKI
metninden yeniden hesaplanan hash ile karsilastirir — tutmayan satir donen
sozluge HIC KONMAZ, `verdict.decide` onu "satir yok" sayar ve birim
yeniden islenebilir olur. Motora tek satir dokunulmaz.
"""

from __future__ import annotations

from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.rationale import fingerprint
from polyvo.modules.cloze.rationale import units as rationale_units

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class ClozeRationaleStore(ArtifactStore):
    """Ipucu + sik basina aciklama paketinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_cloze_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`stable_key -> Existing`. BAYAT satir (hash tutmuyor) hic donmez."""
        rows = self.conn.execute(
            "SELECT stable_key, question_sha256, status, tier, model"
            " FROM sense_cloze_rationale").fetchall()
        if not rows:
            return {}
        current = {
            key: fingerprint.question_sha256(questions)
            for key, questions in
            rationale_units.approved_packages(self.conn).items()
        }
        return {
            stable_key: Existing(tier=tier, status=status, rank=rank_for(model))
            for stable_key, stored_hash, status, tier, model in rows
            if current.get(stable_key) == stored_hash
        }

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis paketi yazar; reddedilirse ICERIK yazilmaz."""
        data = request.unit.data
        sense_id = data["sense_id"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_cloze_rationale (sense_id,"
            " stable_key, status, reject_reason, warnings, tier, source,"
            " model, prompt_hash, question_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, data["stable_key"], request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version, data["question_sha256"]))

        # Once silinir: eski bir paketin uyeleri yeni pakette oksuz kalmasin.
        self.conn.execute("DELETE FROM sense_cloze_hint WHERE sense_id = ?",
                          (sense_id,))
        self.conn.execute(
            "DELETE FROM sense_cloze_option_reason WHERE sense_id = ?",
            (sense_id,))
        if not approved:
            return

        self.conn.executemany(
            "INSERT INTO sense_cloze_hint (sense_id, seq, hint_seq, hint,"
            " tier, source) VALUES (?,?,1,?,?,?)",
            [(sense_id, h["seq"], h["hint"], request.tier, SOURCE_MODEL)
             for h in request.payload["hints"]])
        self.conn.executemany(
            "INSERT INTO sense_cloze_option_reason (sense_id, seq, opt_seq,"
            " reason, tier, source) VALUES (?,?,?,?,?,?)",
            [(sense_id, r["seq"], r["opt_seq"], r["reason"], request.tier,
              SOURCE_MODEL)
             for r in request.payload["reasons"]])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
