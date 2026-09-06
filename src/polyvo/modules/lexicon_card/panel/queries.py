"""
Panel sayfasinin depoya sordugu SORULAR — HTML burada yoktur.

Salt okunur: panel odenmis depoya dokunmaz. Duzeltme yolu `review` app'idir.
"""

from __future__ import annotations

from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema

#: Liste sayfasinda bir defada gosterilecek en fazla satir.
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _headwords(conn=None) -> dict[int, tuple[str, str]]:
    """`item_id -> (headword, pos)` — kimlik deposundan."""
    own = conn is None
    conn = conn if conn is not None else curriculum_schema.open_identity_db()
    try:
        return {row[0]: (row[1], row[2]) for row in
                conn.execute("SELECT item_id, headword, pos FROM items")}
    finally:
        if own:
            conn.close()


def counts() -> list[tuple[str, int]]:
    """Duruma gore kart sayilari (cok olandan aza)."""
    conn = lexicon_schema.open_lexicon_db()
    try:
        return [(row[0], row[1]) for row in conn.execute(
            "SELECT status, COUNT(*) FROM sense_cards GROUP BY status"
            " ORDER BY COUNT(*) DESC")]
    finally:
        conn.close()


def list_cards(*, status: str | None = None, search: str | None = None,
               limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Kartlari `item_id` sirasinda listeler (arama basligin BASINDAN eslesir)."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    names = _headwords()
    where, params = [], []
    if status:
        where.append("status = ?")
        params.append(status)
    clause = (" WHERE " + " AND ".join(where)) if where else ""

    conn = lexicon_schema.open_lexicon_db()
    try:
        rows = conn.execute(
            "SELECT item_id, sense_id, stable_key, gloss_en, tier, status,"
            " source, model, reject_reason FROM sense_cards" + clause +
            " ORDER BY item_id", params).fetchall()
    finally:
        conn.close()

    out = []
    needle = (search or "").strip().lower()
    for item_id, sense_id, key, gloss, tier, st, source, model, reason in rows:
        headword, pos = names.get(item_id, ("", ""))
        if needle and not headword.lower().startswith(needle):
            continue
        out.append({
            "item_id": item_id, "sense_id": sense_id, "stable_key": key,
            "headword": headword, "pos": pos, "gloss_en": gloss, "tier": tier,
            "status": st, "source": source, "model": model,
            "reject_reason": reason,
        })
        if len(out) >= limit:
            break
    return out


def card(stable_key: str) -> dict | None:
    """Tek bir kartin tum parcalari (gloss, ornekler, L1, IPA, seviye)."""
    conn = lexicon_schema.open_lexicon_db()
    try:
        row = conn.execute(
            "SELECT item_id, sense_id, stable_key, gloss_en, register,"
            " usage_note, tier, status, source, model, reject_reason,"
            " updated_at FROM sense_cards WHERE stable_key = ?",
            (stable_key,)).fetchone()
        if row is None:
            return None
        columns = ("item_id", "sense_id", "stable_key", "gloss_en", "register",
                   "usage_note", "tier", "status", "source", "model",
                   "reject_reason", "updated_at")
        detail = dict(zip(columns, row))
        sense_id, item_id = detail["sense_id"], detail["item_id"]

        detail["examples"] = [
            (seq, text, tier, source) for seq, text, tier, source in conn.execute(
                "SELECT seq, text, tier, source FROM sense_examples"
                " WHERE sense_id = ? ORDER BY seq", (sense_id,))]
        detail["glosses_l1"] = [
            (l1, gloss, tier, source) for l1, gloss, tier, source in conn.execute(
                "SELECT l1, gloss, tier, source FROM sense_gloss_l1"
                " WHERE sense_id = ? ORDER BY l1", (sense_id,))]
        detail["phonetics"] = [
            (variant, ipa, source) for variant, ipa, source in conn.execute(
                "SELECT variant, ipa, source FROM item_phonetics"
                " WHERE item_id = ? ORDER BY variant", (item_id,))]
        detail["level"] = conn.execute(
            "SELECT cefr, freq_rank, source FROM item_level WHERE item_id = ?",
            (item_id,)).fetchone()
    finally:
        conn.close()

    headword, pos = _headwords().get(detail["item_id"], ("", ""))
    detail["headword"], detail["pos"] = headword, pos
    return detail
