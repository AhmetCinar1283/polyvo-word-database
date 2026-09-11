"""
Ana dil paketinin deposu — bes tablonun TEK yazicisi: `sense_gloss_l1`,
`sense_gloss_l1_note`, `sense_gloss_l1_state` (karsilik parcasi) ve
`sense_translation`, `sense_translation_examples` (ceviri parcasi).

Paket iki PARCADAN olusur ve depoda iki parca ayri durur (sema degismedi).
Birim duzeyinde karar (`load_existing`) iki parcanin birlesimidir; yazarken
her parca icin AYNI yazma kapisi (`policy.should_write`) ayrica sorulur —
boylece onayli/insan parca, eksik parca icin yapilan cagrida ezilmez.

Kartin kendisine (`sense_cards`, `sense_examples`, `sense_usage_note`)
BURADAN HIC dokunulmaz.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing, should_write
from polyvo.core.llm.quality import rank_for
from polyvo.modules.lexicon_card import schema

#: `source` sutununa yazilan kimlik.
SOURCE_MODEL = "llm"


def _weakest(parts: list[Existing]) -> Existing:
    """Rank'i en zayif parca (`None` en zayif sayilir) — rank kapisi, yeni
    modelin paketin EN AZ bir parcasina yeni bilgi getirip getirmedigini sorar."""
    return max(parts, key=lambda p: float("inf") if p.rank is None else p.rank)


def combine(gloss: Existing | None, entry: Existing | None) -> Existing | None:
    """Iki parcadan birimin TEK `Existing`i. Eksik parca varsa `None`
    (birim islenir); ikisi onayliysa onayli; degilse onayli OLMAYAN parca —
    tier 0 bir parca, eksik/kotu kardesini `skip_human`a kilitlemesin diye."""
    if gloss is None or entry is None:
        return None
    bad = [p for p in (gloss, entry) if p.status != "approved"]
    if bad:
        return _weakest(bad)
    weakest = _weakest([gloss, entry])
    return Existing(tier=min(gloss.tier, entry.tier), status="approved",
                    rank=weakest.rank)


class LexiconL1EntryStore(ArtifactStore):
    """Karsilik + ceviri paketinin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_lexicon_db()

    # --- okuma: parca basina durum ---------------------------------------

    def _gloss_parts(self, l1: str, sense_id: int | None = None) -> dict[int, Existing]:
        """`sense_id -> karsilik parcasinin durumu`. Gercek icerik
        (`sense_gloss_l1`) her zaman durum tablosunu ezer — insan satiri
        (tier 0) durum tablosu bayatlasa da hep korunur."""
        where, args = " WHERE l1 = ?", [l1]
        if sense_id is not None:
            where, args = where + " AND sense_id = ?", args + [sense_id]
        parts: dict[int, Existing] = {}
        for sid, tier, model in self.conn.execute(
                "SELECT sense_id, tier, model FROM sense_gloss_l1" + where, args):
            parts[sid] = Existing(tier=tier, status="approved", rank=rank_for(model))
        for sid, status, tier, model in self.conn.execute(
                "SELECT sense_id, status, tier, model FROM sense_gloss_l1_state"
                + where, args):
            parts.setdefault(sid, Existing(tier=tier, status=status,
                                           rank=rank_for(model)))
        return parts

    def _entry_parts(self, l1: str, sense_id: int | None = None) -> dict[int, Existing]:
        """`sense_id -> ceviri parcasinin durumu` (tablo kendi `status`unu tasir)."""
        where, args = " WHERE l1 = ?", [l1]
        if sense_id is not None:
            where, args = where + " AND sense_id = ?", args + [sense_id]
        return {
            sid: Existing(tier=tier, status=status, rank=rank_for(model))
            for sid, status, tier, model in self.conn.execute(
                "SELECT sense_id, status, tier, model FROM sense_translation"
                + where, args)
        }

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """Varyanta duyarli anahtarla birimin birlesik `Existing`i."""
        gloss = self._gloss_parts(ctx.l1)
        entry = self._entry_parts(ctx.l1)
        existing: dict[str, Existing] = {}
        for stable_key, sense_id in self.conn.execute(
                "SELECT stable_key, sense_id FROM sense_cards"):
            combined = combine(gloss.get(sense_id), entry.get(sense_id))
            if combined is not None:
                existing[keys.compose_key(stable_key, ctx.variant)] = combined
        return existing

    # --- yazma: parca basina ayni kapi -----------------------------------

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Paketi yazar. Her parca icin yazma kapisi AYRICA sorulur;
        reddedilen pakette hicbir parcanin ICERIGI yazilmaz (hepsi ya da hic)."""
        sense_id = request.unit.data["sense_id"]
        approved = request.status == "approved"
        payload = request.payload

        def allowed(part: Existing | None) -> bool:
            """Bu parcanin mevcut satiri yeni istekle ezilebilir mi?"""
            return should_write(part, new_tier=request.tier,
                                new_status=request.status,
                                new_rank=request.rank).write

        # Onayli istekte yuk bir parcayi TASIMIYORSA (ör. insan duzeltmesi
        # yalnizca karsilik yazar) o parca yazilmaz.
        if (not approved or "gloss_l1" in payload) and \
                allowed(self._gloss_parts(ctx.l1, sense_id).get(sense_id)):
            self._write_gloss(ctx, request, sense_id)
        if (not approved or "definition" in payload) and \
                allowed(self._entry_parts(ctx.l1, sense_id).get(sense_id)):
            self._write_entry(ctx, request, sense_id)

    def _write_gloss(self, ctx: JobContext, request: WriteRequest, sense_id: int) -> None:
        """Karsilik parcasi: onayliysa icerik (+not), her durumda durum satiri."""
        payload = request.payload
        if request.status == "approved":
            self.conn.execute(
                "INSERT OR REPLACE INTO sense_gloss_l1 (sense_id, l1, gloss,"
                " tier, source, model) VALUES (?,?,?,?,?,?)",
                (sense_id, ctx.l1, payload["gloss_l1"], request.tier,
                 SOURCE_MODEL, request.model_label))
            if payload.get("gloss_note"):
                self.conn.execute(
                    "INSERT OR REPLACE INTO sense_gloss_l1_note (sense_id,"
                    " l1, note, tier, source, model) VALUES (?,?,?,?,?,?)",
                    (sense_id, ctx.l1, payload["gloss_note"], request.tier,
                     SOURCE_MODEL, request.model_label))

        # Onayli da reddedilmis de durum tablosuna duser: redo matrisi
        # "kotu satir"i BURADAN tanir (`sense_gloss_l1`de status yok).
        self.conn.execute(
            "INSERT OR REPLACE INTO sense_gloss_l1_state (sense_id, l1,"
            " status, reject_reason, tier, model, prompt_hash)"
            " VALUES (?,?,?,?,?,?,?)",
            (sense_id, ctx.l1, request.status, request.reject_reason,
             request.tier, request.model_label, request.prompt_version))

    def _write_entry(self, ctx: JobContext, request: WriteRequest, sense_id: int) -> None:
        """Ceviri parcasi: reddedilirse ICERIK yazilmaz, yalnizca durum."""
        payload = request.payload
        approved = request.status == "approved"
        definition = payload.get("definition") if approved else None
        note = payload.get("usage_note") if approved else None

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_translation (sense_id, l1,"
            " definition, usage_note, status, reject_reason, tier, source,"
            " model, prompt_hash, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, ctx.l1, definition, note, request.status,
             request.reject_reason, request.tier, SOURCE_MODEL,
             request.model_label, request.prompt_version))

        self.conn.execute(
            "DELETE FROM sense_translation_examples WHERE sense_id = ? AND l1 = ?",
            (sense_id, ctx.l1))
        if approved:
            self.conn.executemany(
                "INSERT INTO sense_translation_examples (sense_id, l1, seq,"
                " text, tier, source) VALUES (?,?,?,?,?,?)",
                [(sense_id, ctx.l1, seq, text, request.tier, SOURCE_MODEL)
                 for seq, text in enumerate(payload.get("examples", []), start=1)])

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
