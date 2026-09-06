"""
Duzeltmelerin depoya YAZILDIGI tek yer.

Iki soz verir:
  1. `tier=0` ve `source="human"` BURADA sabittir; dosyadan okunmaz.
  2. Sorunlu tek satir varsa HICBIR SATIR yazilmaz — dogrulama tam bitmeden
     ilk `execute` bile calismaz (`delivery/gate.py` ile ayni disiplin).

Yazma izni yine `core/jobs/store/policy.py`den sorulur. Insan karari kapiyi
her zaman gecer; kapinin BURADA da cagrilmasi, ikinci bir kural kumesi
olmadigini garanti eder.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polyvo.core.jobs.store import policy
from polyvo.core.llm.quality import rank_for
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.review import backup as backup_mod
from polyvo.review import record

#: Insan satirinin degismez kimligi — dosyadan OKUNMAZ.
HUMAN_TIER = policy.TIER_HUMAN
HUMAN_SOURCE = "human"
HUMAN_STATUS = "approved"

#: `sense_cards` satirina dokunan alanlar (digerleri kendi tablosunda yasar).
CARD_FIELDS = ("gloss_en", "register", "usage_note")


class ReviewError(RuntimeError):
    """Ice aktarma dogrulamayi gecemedi — hicbir satir yazilmadi."""


@dataclass
class Problem:
    """Bir satirin neden yazilamadigi."""
    stable_key: str
    reason: str


@dataclass
class ApplyResult:
    """Bir `import`/`restore` kosusunun sonucu."""
    applied: int = 0
    skipped_unknown: int = 0
    ignored_fields: int = 0
    #: Yazildiktan sonra hala 'approved' olmayan kartlar (sevkiyata girmezler).
    still_unapproved: list[str] = field(default_factory=list)
    backup_path: str | None = None


def _index(conn) -> dict[str, tuple[int, int, int, str, str | None]]:
    """`stable_key -> (sense_id, item_id, tier, status, model)`, TEK sorgu."""
    return {row[0]: (row[1], row[2], row[3], row[4], row[5]) for row in conn.execute(
        "SELECT stable_key, sense_id, item_id, tier, status, model FROM sense_cards")}


def _write(conn, sense_id: int, correction: record.Correction,
           l1: str | None) -> None:
    """Kapidan gecmis tek bir duzeltmeyi yazar (transaction cagirana ait)."""
    values = correction.values
    card = {name: values[name] for name in CARD_FIELDS if name in values}
    if card:
        columns = ", ".join(f"{name} = ?" for name in card)
        conn.execute(
            f"UPDATE sense_cards SET {columns}, tier = ?, status = ?,"
            " reject_reason = NULL, source = ?, model = NULL,"
            " updated_at = CURRENT_TIMESTAMP WHERE sense_id = ?",
            [*card.values(), HUMAN_TIER, HUMAN_STATUS, HUMAN_SOURCE, sense_id])

    if "gloss_l1" in values:
        conn.execute(
            "INSERT OR REPLACE INTO sense_gloss_l1 (sense_id, l1, gloss, tier,"
            " source, model) VALUES (?,?,?,?,?,NULL)",
            (sense_id, l1, values["gloss_l1"], HUMAN_TIER, HUMAN_SOURCE))

    if "examples" in values:
        # Once silinir: insanin 2 ornegi, modelin 3. ornegini oksuz birakmasin.
        conn.execute("DELETE FROM sense_examples WHERE sense_id = ?", (sense_id,))
        conn.executemany(
            "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
            " VALUES (?,?,?,?,?)",
            [(sense_id, seq, text, HUMAN_TIER, HUMAN_SOURCE)
             for seq, text in enumerate(values["examples"], start=1)])


def apply(corrections: list[record.Correction], *, l1: str | None,
          skip_unknown: bool = False, write_backup: bool = True,
          conn=None) -> ApplyResult:
    """Duzeltmeleri dogrular, kapidan gecirir ve TEK transaction'da yazar."""
    owned = conn is None
    conn = conn if conn is not None else lexicon_schema.open_lexicon_db()
    try:
        index = _index(conn)
        problems: list[Problem] = []
        planned: list[tuple[int, record.Correction, str | None]] = []
        skipped = 0

        for correction in corrections:
            found = index.get(correction.stable_key)
            if found is None:
                # Kimlik URETILMEZ: karsiligi olmayan anahtar duzeltilemez.
                if skip_unknown:
                    skipped += 1
                    continue
                problems.append(Problem(correction.stable_key, "depoda_yok"))
                continue

            sense_id, _item_id, tier, status, model = found
            row_l1 = correction.l1 or l1
            if "gloss_l1" in correction.values and not row_l1:
                problems.append(Problem(correction.stable_key, "l1_verilmedi"))
                continue

            decision = policy.should_write(
                policy.Existing(tier=tier, status=status, rank=rank_for(model)),
                new_tier=HUMAN_TIER, new_status=HUMAN_STATUS, new_rank=None)
            if not decision.write:            # insan karari icin olmamali
                problems.append(Problem(correction.stable_key,
                                        f"kapi_reddetti: {decision.reason}"))
                continue
            planned.append((sense_id, correction, row_l1))

        if problems:
            detail = "\n  ".join(f"{p.stable_key}: {p.reason}" for p in problems)
            raise ReviewError(f"{len(problems)} satir yazilamadi:\n  {detail}")

        with conn:                            # tek transaction: hep ya da hic
            for sense_id, correction, row_l1 in planned:
                _write(conn, sense_id, correction, row_l1)

        result = ApplyResult(
            applied=len(planned), skipped_unknown=skipped,
            ignored_fields=sum(len(c.ignored) for c in corrections))
        if planned:
            keys = [c.stable_key for _s, c, _l in planned]
            marks = ",".join("?" * len(keys))
            result.still_unapproved = sorted(
                row[0] for row in conn.execute(
                    f"SELECT stable_key FROM sense_cards WHERE status != ?"
                    f" AND stable_key IN ({marks})", [HUMAN_STATUS, *keys]))
        if write_backup and planned:
            result.backup_path = backup_mod.append(
                [c for _s, c, _l in planned], l1=l1)
        return result
    finally:
        if owned:
            conn.close()
