"""
Onayli Ingilizce kartin BAGLAM sorgusu — `note/units.py` ve
`translate/units.py` AYNI sorguyu tekrar yazmasin diye TEK yerde durur.

Model kelimeyi degil ANLAMI islesin diye her birime `gloss_en`/`register`/
`usage_note`/ornekler baglam olarak eklenir; bu dosya BAGLAMI toplar, hangi
alanin isteniyor oldugunu bilmez (o `translate/prompt.py`nin isidir).
"""

from __future__ import annotations


def approved_cards(conn) -> dict[str, dict]:
    """`stable_key -> onayli kartin baglam alanlari` (gloss_en/register)."""
    rows = conn.execute(
        "SELECT stable_key, sense_id, gloss_en, register"
        " FROM sense_cards WHERE status = 'approved'").fetchall()
    return {
        stable_key: {"sense_id": sense_id, "gloss_en": gloss_en, "register": register}
        for stable_key, sense_id, gloss_en, register in rows
    }


def examples_by_sense(conn, sense_ids: list[int]) -> dict[int, list[str]]:
    """`sense_id -> siradaki Ingilizce ornek cumleler`."""
    if not sense_ids:
        return {}
    marks = ",".join("?" * len(sense_ids))
    rows = conn.execute(
        f"SELECT sense_id, text FROM sense_examples WHERE sense_id IN ({marks})"
        " ORDER BY sense_id, seq", sense_ids).fetchall()
    out: dict[int, list[str]] = {}
    for sense_id, text in rows:
        out.setdefault(sense_id, []).append(text)
    return out


def notes_by_sense(conn, sense_ids: list[int]) -> dict[int, dict]:
    """`sense_id -> onayli Ingilizce kullanim notu` (`sense_usage_note`).

    Notu OLMAYAN/reddedilmis anlam icin sozluk bos doner — `translate` bunu
    "not yok" olarak okur, kartsiz/onaysiz anlamla KARISTIRMAZ."""
    if not sense_ids:
        return {}
    marks = ",".join("?" * len(sense_ids))
    rows = conn.execute(
        f"SELECT sense_id, note FROM sense_usage_note"
        f" WHERE status = 'approved' AND sense_id IN ({marks})",
        sense_ids).fetchall()
    return {sense_id: {"note": note} for sense_id, note in rows}


def glosses_by_sense(conn, l1: str) -> dict[int, str]:
    """`sense_id -> o dilde DEPODA DURAN karsilik` (`sense_gloss_l1`).

    Bu tabloda satir varsa karsilik onaylidir (model ya da insan) — ceviri
    promptu onu SABIT TERIM olarak kullanir."""
    rows = conn.execute(
        "SELECT sense_id, gloss FROM sense_gloss_l1 WHERE l1 = ?", (l1,)).fetchall()
    return {sense_id: gloss for sense_id, gloss in rows}
