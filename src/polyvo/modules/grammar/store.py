"""
`sentence_grammar` (+ `_rule`, `grammar_candidate`) deposu — bu uc tablonun
TEK yazicisi.

BAYATLIK (Is 6 §16): `load_existing` depodaki `source_sha256`i cumlelerin O
ANKI metninden yeniden hesaplanan hash ile karsilastirir — tutmayan satir
donen sozluge HIC KONMAZ, `verdict.decide` onu "satir yok" sayar ve grup
yeniden islenebilir olur. Motora tek satir dokunulmaz.

`propose_only=True` ile kurulan depo YALNIZCA `grammar_candidate` yazar
(§9, Kademe 1): kural satiri hicbir kosulda yazilmaz. Aday havuzu bunun
DISINDA HER durumda guncellenir — grup reddedilse bile modelin bildirdigi
adaylar KAYBOLMAZ (bkz. `qa/__init__.py::_candidates_payload`).
"""

from __future__ import annotations

from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.grammar import schema
from polyvo.modules.grammar import units as units_mod

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class GrammarStore(ArtifactStore):
    """Grup basina en cok uc kurallik grammar paketinin kalici deposu."""

    def __init__(self, conn=None, propose_only: bool = False):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz.
        `propose_only=True` iken `_write_row` yalnizca aday yazar."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_grammar_db()
        self.propose_only = propose_only

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`owner|group_key -> Existing`. BAYAT satir (hash tutmuyor) hic
        donmez."""
        rows = self.conn.execute(
            "SELECT owner, group_key, source_sha256, status, tier, model"
            " FROM sentence_grammar").fetchall()
        if not rows:
            return {}
        current = {unit.key: unit.data["source_sha256"]
                  for unit in units_mod.load_units(ctx.tag, ctx.l2)}
        out: dict[str, Existing] = {}
        for owner, group_key, stored_hash, status, tier, model in rows:
            key = units_mod.unit_key(owner, group_key)
            if current.get(key) == stored_hash:
                out[key] = Existing(tier=tier, status=status,
                                    rank=rank_for(model))
        return out

    def _write_candidates(self, owner: str, refs: list[str],
                          candidates: list[dict]) -> None:
        """Aday havuzunu bu grubun REF'leri icin BASTAN yazar."""
        for ref in refs:
            self.conn.execute(
                "DELETE FROM grammar_candidate WHERE owner = ? AND ref = ?",
                (owner, ref))
        self.conn.executemany(
            "INSERT INTO grammar_candidate (owner, ref, seq, proposed_name,"
            " trigger, rationale, status) VALUES (?,?,?,?,?,?,'new')",
            [(owner, c["ref"], c["seq"], c["proposed_name"], c["trigger"],
              c["rationale"]) for c in candidates])

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis paketi yazar; reddedilirse KURAL SATIRI yazilmaz."""
        data = request.unit.data
        owner = data["owner"]
        group_key = data["group_key"]
        approved = request.status == "approved"
        refs = request.payload.get("refs") or [
            s["ref"] for s in data["sentences"]]

        self._write_candidates(owner, refs, request.payload.get(
            "candidates", []))

        if self.propose_only:
            return                    # KURAL SATIRI HIC YAZILMAZ (Kademe 1)

        self.conn.execute(
            "INSERT OR REPLACE INTO sentence_grammar (owner, group_key,"
            " status, reject_reason, warnings, tier, source, model,"
            " prompt_hash, source_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (owner, group_key, request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version, data["source_sha256"]))

        # Once silinir: eski bir paketin dorduncu cumlesi yeni pakette
        # oksuz kalmasin.
        for ref in refs:
            self.conn.execute(
                "DELETE FROM sentence_grammar_rule WHERE owner = ? AND ref = ?",
                (owner, ref))
        if not approved:
            return

        self.conn.executemany(
            "INSERT INTO sentence_grammar_rule (owner, group_key, ref, rank,"
            " rule_id, trigger, note, tier, source)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            [(owner, group_key, r["ref"], r["rank"], r["rule_id"],
              r["trigger"], r["note"], request.tier, SOURCE_MODEL)
             for r in request.payload.get("rules", [])])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
