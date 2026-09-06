"""
Odenmis depodan duzeltilebilir satirlari cikarir (JSONL).

Cikti bir IZDUSUMDUR: serbestce silinir, yeniden uretilir. Icinde `tier`,
`status` gibi baglam alanlari da yazilir ama bunlar INSANIN GORMESI icindir;
geri okunurken yok sayilirlar (`record.IGNORED_FIELDS`).

Reddedilmis kartlarin icerigi depoda YOKTUR (bilerek — bkz. `lexicon_card/
store.py`); o alanlar dosyaya HIC YAZILMAZ.

Bos alan neden yazilmaz: "bulunmayan alan dokunulmaz" kuralindan dolayi bos
bir alan yazmak, ice aktarmada "bu alani bosalt" gibi okunurdu. Cikan dosya
hic duzeltilmeden geri okunabilmelidir (`tests/test_review.py`).
"""

from __future__ import annotations

import json
import os

from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.review import record

#: `--status` icin "hepsi" anlamina gelen deger.
STATUS_ALL = "all"

EXPORT_FILENAME = "review-export.jsonl"


def _headwords() -> dict[int, tuple[str, str]]:
    """`item_id -> (headword, pos)` — kimlik deposundan, TEK sorgu."""
    conn = curriculum_schema.open_identity_db()
    try:
        return {row[0]: (row[1], row[2]) for row in
                conn.execute("SELECT item_id, headword, pos FROM items")}
    finally:
        conn.close()


def rows(l1: str | None, *, status: str = STATUS_ALL,
         limit: int | None = None) -> list[dict]:
    """Duzeltmeye acik satirlari `item_id` sirasinda (deterministik) doner."""
    names = _headwords()
    conn = lexicon_schema.open_lexicon_db()
    try:
        where, params = "", []
        if status != STATUS_ALL:
            where, params = " WHERE status = ?", [status]
        cards = conn.execute(
            "SELECT sense_id, item_id, stable_key, gloss_en, register,"
            " usage_note, tier, status, reject_reason FROM sense_cards"
            + where + " ORDER BY item_id", params).fetchall()
        if limit is not None:
            cards = cards[:limit]

        glosses = {}
        if l1:
            glosses = {row[0]: row[1] for row in conn.execute(
                "SELECT sense_id, gloss FROM sense_gloss_l1 WHERE l1 = ?", (l1,))}
        examples: dict[int, list[str]] = {}
        for sense_id, text in conn.execute(
                "SELECT sense_id, text FROM sense_examples ORDER BY sense_id, seq"):
            examples.setdefault(sense_id, []).append(text)
    finally:
        conn.close()

    out = []
    for sense_id, item_id, key, gloss_en, register, usage, tier, st, reason in cards:
        headword, pos = names.get(item_id, ("", ""))
        row = {
            record.KEY_FIELD: key, "item_id": item_id, "sense_id": sense_id,
            "headword": headword, "pos": pos, "tier": tier, "status": st,
            "gloss_en": gloss_en, "register": register, "usage_note": usage,
            "examples": examples.get(sense_id, []),
        }
        if l1:
            row["gloss_l1"] = glosses.get(sense_id)
        if reason:
            row["reject_reason"] = reason
        # Bos duzeltilebilir alanlar YAZILMAZ: yoklari "dokunma" demektir.
        for name in record.EDITABLE_FIELDS:
            if name in row and not row[name]:
                del row[name]
        out.append(row)
    return out


def default_path(workspace: str) -> str:
    """Izdusum dizini altindaki varsayilan cikti yolu."""
    return os.path.join(workspace, EXPORT_FILENAME)


def write(exported: list[dict], path: str) -> str:
    """Satirlari JSONL olarak yazar; dizini gerekiyorsa olusturur."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in exported:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path
