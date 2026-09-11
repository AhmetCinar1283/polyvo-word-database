"""
`sense_cloze_rationale_translation` (+ `_hint_l1`, `_option_reason_l1`)
deposu — bu UC tablonun TEK yazicisi.

Ingilizce `sense_cloze_hint`/`sense_cloze_option_reason` tablolarina BURADAN
HIC dokunulmaz: ceviri odenmis ipucu/aciklamayi yeniden uretmez.

BAYATLIK (§12): `load_existing` depodaki `rationale_sha256`i Ingilizce
metnin O ANKI halinden yeniden hesaplanan hash ile karsilastirir — tutmayan
satir donen sozluge HIC KONMAZ.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.cloze import schema
from polyvo.modules.cloze.rationale import fingerprint
from polyvo.modules.cloze.rationale.translate import units as translate_units

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class ClozeRationaleTranslationStore(ArtifactStore):
    """Ipucu + sik aciklamasinin L1 cevirisinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_cloze_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """Varyanta duyarli anahtarla `Existing`; BAYAT satir hic donmez."""
        rows = self.conn.execute(
            "SELECT c.stable_key, t.rationale_sha256, t.status, t.tier,"
            " t.model FROM sense_cloze_rationale_translation t"
            " JOIN sense_cloze_rationale c ON c.sense_id = t.sense_id"
            " WHERE t.l1 = ?", (ctx.l1,)).fetchall()
        if not rows:
            return {}
        current = {
            key: fingerprint.rationale_sha256(found["hints"], found["reasons"])
            for key, found in
            translate_units.approved_rationales(self.conn).items()
        }
        out: dict[str, Existing] = {}
        for stable_key, stored_hash, status, tier, model in rows:
            if current.get(stable_key) != stored_hash:
                continue
            out[keys.compose_key(stable_key, ctx.variant)] = Existing(
                tier=tier, status=status, rank=rank_for(model))
        return out

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis ceviriyi yazar; reddedilirse ICERIK yazilmaz."""
        sense_id = request.unit.data["sense_id"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_cloze_rationale_translation"
            " (sense_id, l1, status, reject_reason, warnings, tier, source,"
            " model, prompt_hash, rationale_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, ctx.l1, request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version, request.unit.data["rationale_sha256"]))

        self.conn.execute(
            "DELETE FROM sense_cloze_hint_l1 WHERE sense_id = ? AND l1 = ?",
            (sense_id, ctx.l1))
        self.conn.execute(
            "DELETE FROM sense_cloze_option_reason_l1"
            " WHERE sense_id = ? AND l1 = ?", (sense_id, ctx.l1))
        if not approved:
            return

        hints = sorted(request.unit.data["hints"], key=lambda h: h["seq"])
        reasons = sorted(request.unit.data["reasons"],
                         key=lambda r: (r["seq"], r["opt_seq"]))
        self.conn.executemany(
            "INSERT INTO sense_cloze_hint_l1 (sense_id, l1, seq, hint_seq,"
            " hint, tier, source) VALUES (?,?,?,1,?,?,?)",
            [(sense_id, ctx.l1, h["seq"], translated, request.tier,
              SOURCE_MODEL)
             for h, translated in zip(hints, request.payload["hints"])])
        self.conn.executemany(
            "INSERT INTO sense_cloze_option_reason_l1 (sense_id, l1, seq,"
            " opt_seq, reason, tier, source) VALUES (?,?,?,?,?,?,?)",
            [(sense_id, ctx.l1, r["seq"], r["opt_seq"], translated,
              request.tier, SOURCE_MODEL)
             for r, translated in zip(reasons, request.payload["reasons"])])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
