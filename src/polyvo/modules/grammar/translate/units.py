"""
Ceviri isinin birimleri — YALNIZCA onayli grammar paketleri.

Reddedilmis ya da hic uretilmemis paketin cevrilecek bir notu yoktur. Sira
`units.py` ile AYNIDIR (`owner|group_key` sirasi).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.grammar import fingerprint, schema
from polyvo.modules.grammar import units as grammar_units


def approved_rules(conn) -> dict[str, list[dict]]:
    """`owner|group_key -> [{"ref","rank","rule_id","trigger","note"}]` —
    yalnizca ONAYLI paketler.

    `store.py::load_existing` da AYNI sorguyu kullanir (bayatlik) — ikisi
    ayrisirsa "o anki metin" iki farkli sey olurdu. `trigger` de tasinir:
    çeviri dil kapisindan ONCE metinden CIKARILMASI gerekir (§18)."""
    out: dict[str, list[dict]] = {}
    for owner, group_key, ref, rank, rule_id, trigger, note in conn.execute(
            "SELECT r.owner, r.group_key, r.ref, r.rank, r.rule_id,"
            " r.trigger, r.note FROM sentence_grammar_rule r"
            " JOIN sentence_grammar g ON g.owner = r.owner"
            "   AND g.group_key = r.group_key"
            " WHERE g.status = 'approved'"
            " ORDER BY r.owner, r.group_key, r.ref, r.rank"):
        key = grammar_units.unit_key(owner, group_key)
        out.setdefault(key, []).append({
            "ref": ref, "rank": rank, "rule_id": rule_id, "trigger": trigger,
            "note": note,
        })
    return out


def load_units(tag: str, l2: str) -> list[Unit]:
    """Onayli grammar paketi olan gruplar icin ceviri birimi uretir."""
    base = grammar_units.load_units(tag, l2)
    conn = schema.open_grammar_db()
    try:
        rules_by_group = approved_rules(conn)
    finally:
        conn.close()

    units: list[Unit] = []
    for unit in base:
        rules = rules_by_group.get(unit.key)
        if not rules:
            continue                      # paketsiz/reddedilmis grup: atla
        data = dict(unit.data)
        data["rules"] = rules
        data["note_sha256"] = fingerprint.note_sha256(
            [(r["ref"], r["rank"], r["note"]) for r in rules])
        units.append(Unit(key=unit.key, name=unit.name, data=data))
    return units
