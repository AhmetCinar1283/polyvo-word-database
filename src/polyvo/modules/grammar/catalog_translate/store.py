"""
`grammar_catalog_translation` (+ `grammar_rule_l1`) deposu — bu iki
tablonun TEK yazicisi.

BAYATLIK: `load_existing` depodaki `catalog_sha256`i katalogun (kod
icindeki `name_en`+`short_en`) O ANKI halinden yeniden hesaplanan hash ile
karsilastirir — tutmayan satir donen sozluge HIC KONMAZ. Katalog kodda
durdugu icin bu satir yalnizca kod DEGISTIGINDE (isim/aciklama duzenlendiginde)
tetiklenir.

`grammar_rule_l1`e insan da `tier=0` ile satir yazabilir (`review/`) — bu
depo o satiri OKUR (load_existing), UZERINE yazmaz (`policy.should_write`
tier'i kucuk olanin kazandigi kurali uygular).
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.grammar import fingerprint, schema
from polyvo.modules.grammar.catalog import get as catalog_get

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


class GrammarCatalogTranslationStore(ArtifactStore):
    """Katalog aciklamasinin L1 cevirisinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_grammar_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """Varyanta duyarli anahtarla `Existing`; BAYAT satir hic donmez."""
        rows = self.conn.execute(
            "SELECT rule_id, catalog_sha256, status, tier, model"
            " FROM grammar_catalog_translation WHERE l1 = ?",
            (ctx.l1,)).fetchall()
        out: dict[str, Existing] = {}
        for rule_id, stored_hash, status, tier, model in rows:
            rule = catalog_get(rule_id)
            if rule is None or fingerprint.catalog_sha256(rule) != stored_hash:
                continue                  # katalogdan silinmis/degismis
            out[keys.compose_key(rule_id, ctx.variant)] = Existing(
                tier=tier, status=status, rank=rank_for(model))
        return out

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis ceviriyi yazar; reddedilirse ICERIK yazilmaz."""
        rule_id = request.unit.data["rule_id"]
        approved = request.status == "approved"

        self.conn.execute(
            "INSERT OR REPLACE INTO grammar_catalog_translation (rule_id,"
            " l1, status, reject_reason, warnings, tier, source, model,"
            " prompt_hash, catalog_sha256, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (rule_id, ctx.l1, request.status,
             None if approved else request.reject_reason,
             request.reject_reason if approved else None,
             request.tier, SOURCE_MODEL, request.model_label,
             request.prompt_version, request.unit.data["catalog_sha256"]))

        if not approved:
            self.conn.execute(
                "DELETE FROM grammar_rule_l1 WHERE rule_id = ? AND l1 = ?",
                (rule_id, ctx.l1))
            return

        self.conn.execute(
            "INSERT OR REPLACE INTO grammar_rule_l1 (rule_id, l1, name,"
            " short, tier, source) VALUES (?,?,?,?,?,?)",
            (rule_id, ctx.l1, request.payload["name"],
             request.payload["short"], request.tier, SOURCE_MODEL))

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
