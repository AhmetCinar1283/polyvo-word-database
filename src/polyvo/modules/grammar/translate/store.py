"""
`sentence_grammar_translation` (+ `sentence_grammar_rule_l1`) deposu — bu
iki tablonun TEK yazicisi.

Ingilizce `sentence_grammar_rule`e BURADAN HIC dokunulmaz: ceviri odenmis
notu yeniden uretmez. `rule_id`/`trigger` BU TABLOYA HIC YAZILMAZ — ikisi de
cevrilmez (Is 6 §18), yalnizca `note`un cevirisi durur.

BAYATLIK: `load_existing` depodaki `note_sha256`i Ingilizce notlarin O ANKI
halinden yeniden hesaplanan hash ile karsilastirir — tutmayan satir donen
sozluge HIC KONMAZ.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.grammar import fingerprint, schema
from polyvo.modules.grammar.translate import units as translate_units

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class GrammarTranslationStore(ArtifactStore):
    """Cumleye ozel notun L1 cevirisinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_grammar_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """Varyanta duyarli anahtarla `Existing`; BAYAT satir hic donmez."""
        rows = self.conn.execute(
            "SELECT owner, group_key, note_sha256, status, tier, model"
            " FROM sentence_grammar_translation WHERE l1 = ?",
            (ctx.l1,)).fetchall()
        if not rows:
            return {}
        current = {
            key: fingerprint.note_sha256(
                [(r["ref"], r["rank"], r["note"]) for r in items])
            for key, items in translate_units.approved_rules(self.conn).items()
        }
        out: dict[str, Existing] = {}
        for owner, group_key, stored_hash, status, tier, model in rows:
            key = f"{owner}|{group_key}"
            if current.get(key) != stored_hash:
                continue
            out[keys.compose_key(key, ctx.variant)] = Existing(
                tier=tier, status=status, rank=rank_for(model))
        return out

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis ceviriyi yazar; reddedilirse ICERIK yazilmaz."""
        owner = request.unit.data["owner"]
        group_key = request.unit.data["group_key"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO sentence_grammar_translation (owner,"
            " group_key, l1, status, reject_reason, warnings, tier, source,"
            " model, prompt_hash, note_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (owner, group_key, ctx.l1, request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version, request.unit.data["note_sha256"]))

        self.conn.execute(
            "DELETE FROM sentence_grammar_rule_l1 WHERE owner = ? AND l1 = ?"
            " AND ref IN (SELECT ref FROM sentence_grammar_rule"
            "             WHERE owner = ? AND group_key = ?)",
            (owner, ctx.l1, owner, group_key))
        if not approved:
            return

        rules = request.unit.data["rules"]
        self.conn.executemany(
            "INSERT INTO sentence_grammar_rule_l1 (owner, ref, rank, l1,"
            " note, tier, source) VALUES (?,?,?,?,?,?,?)",
            [(owner, r["ref"], r["rank"], ctx.l1, translated, request.tier,
              SOURCE_MODEL)
             for r, translated in zip(rules, request.payload["notes"])])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
