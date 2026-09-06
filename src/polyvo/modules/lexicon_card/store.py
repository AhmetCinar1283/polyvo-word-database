"""
`lexicon.sqlite` deposu — kartin BUTUN parcalari (EN kart + L1 gloss + ornek
+ tohum) TEK transaction'da yazilir; motor `commit()` cagirana kadar hicbiri
kalicilasmaz. Yarim kart diye bir sey olamaz.

Kapiyi bu sinif CAGIRMAZ: `ArtifactStore.save` cagirir, buradaki `_write_row`
yalnizca kapidan GECMIS satiri yazar (`core/jobs/store/base.py`).

Tohum kurali burada uygulanir: model bir alani uretmediyse sozluk tohumu
(tier 1) o alani doldurur; urettiyse tohum yazilmaz. Insan tohumunu (tier 0)
zaten kapinin kendisi korur.
"""

from __future__ import annotations

from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.quality import rank_for
from polyvo.modules.lexicon_card import schema

#: `source` sutununa yazilan kimlik — satirin NEREDEN geldigi.
SOURCE_MODEL = "llm"
SOURCE_DICT = "dictionary_seed"


class LexiconCardStore(ArtifactStore):
    """`sense_cards` ve baglı tablolarin kalici deposu."""

    def __init__(self, conn=None):
        """Depoyu acar. `conn` verilirse (test) o kullanilir, kapatilmaz."""
        self._owned = conn is None
        self.conn = conn if conn is not None else schema.open_lexicon_db()

    def load_existing(self, ctx: JobContext) -> dict[str, Existing]:
        """`stable_key -> Existing`, TEK sorgu. `rank` model adindan turetilir
        (depoda saklanmaz — `model_quality.json` aninda gecerli olsun diye)."""
        rows = self.conn.execute(
            "SELECT stable_key, tier, status, model FROM sense_cards").fetchall()
        return {
            stable_key: Existing(tier=tier, status=status, rank=rank_for(model))
            for stable_key, tier, status, model in rows
        }

    def _write_row(self, ctx: JobContext, request: WriteRequest) -> None:
        """Kapidan gecmis karti butun parcalariyla yazar."""
        unit = request.unit
        item_id = unit.data["item_id"]
        sense_id = unit.data["sense_id"]
        payload = request.payload

        self.conn.execute(
            "INSERT OR REPLACE INTO sense_cards (sense_id, item_id, stable_key,"
            " gloss_en, register, usage_note, tier, status, reject_reason,"
            " source, model, prompt_hash, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (sense_id, item_id, unit.key, payload.get("gloss_en"),
             payload.get("register"), payload.get("usage_note"),
             request.tier, request.status, request.reject_reason,
             SOURCE_MODEL, request.model_label, request.prompt_version))

        # Reddedilen cevabin ICERIGI yazilmaz — satir yalnizca "burasi kotu"
        # demek icin durur, redo matrisi onu boyle tanir.
        if request.status == "approved":
            self._write_content(ctx, request)
        self._write_seed(unit, payload)

    def _write_content(self, ctx: JobContext, request: WriteRequest) -> None:
        """Onaylanmis karta ait L1 gloss ve ornek cumleleri yazar."""
        sense_id = request.unit.data["sense_id"]
        payload = request.payload
        if ctx.l1 and payload.get("gloss_l1"):
            self.conn.execute(
                "INSERT OR REPLACE INTO sense_gloss_l1 (sense_id, l1, gloss,"
                " tier, source, model) VALUES (?,?,?,?,?,?)",
                (sense_id, ctx.l1, payload["gloss_l1"], request.tier,
                 SOURCE_MODEL, request.model_label))

        # Ornekler once SILINIR: eski kosunun 3. ornegi yeni kosunun 2
        # orneginin yaninda oksuz kalmasin.
        self.conn.execute("DELETE FROM sense_examples WHERE sense_id = ?",
                          (sense_id,))
        self.conn.executemany(
            "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
            " VALUES (?,?,?,?,?)",
            [(sense_id, seq, text, request.tier, SOURCE_MODEL)
             for seq, text in enumerate(payload.get("examples", []), start=1)])

    def _write_seed(self, unit, payload: dict) -> None:
        """Modelin uretmedigi OLGULARI sozluk tohumundan doldurur (tier 1).
        Model o alani urettiyse buraya hic girilmez."""
        item_id = unit.data["item_id"]
        seed = unit.data.get("seed")
        ipa = payload.get("ipa") or (seed.ipa if seed is not None else None)
        if ipa:
            self.conn.execute(
                "INSERT OR IGNORE INTO item_phonetics (item_id, variant, ipa,"
                " source) VALUES (?,?,?,?)",
                (item_id, "us", ipa, SOURCE_DICT))
        if unit.data.get("cefr") or unit.data.get("freq_rank"):
            self.conn.execute(
                "INSERT OR IGNORE INTO item_level (item_id, cefr, freq_rank,"
                " source) VALUES (?,?,?,?)",
                (item_id, unit.data.get("cefr"), unit.data.get("freq_rank"),
                 SOURCE_DICT))

    def commit(self) -> None:
        """Bekleyen butun yazmalari tek seferde kalicilastirir."""
        self.conn.commit()

    def close(self) -> None:
        """Kendi actigi baglantiyi kapatir; disaridan verileni birakmaz."""
        if self._owned:
            self.conn.close()
