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

Is 3: `usage_note` artik `sense_usage_note`dan gelir (kart sutunundan DEGIL).
`--l1 <kod>` verildiginde `gloss_l1`e ek olarak `gloss_note_l1` (kelime
karsiliginin kosullu notu) ve `definition_l1`/`usage_note_l1`/`examples_l1`
(ceviri paketi, yalnizca onaylanmissa) da cikar.

Is 4: `cloze` (uc soru + siklari) ve `--l1` ile `cloze_l1` (cevrilen
cumleler) AYRI bir dosyadan (`data/stores/cloze.sqlite`) okunur.

Is 5: `cloze_rationale` (soru basina ipucu + sik basina aciklama) ve `--l1`
ile `cloze_rationale_l1` (cevirisi) AYNI dosyadan, yalnizca ONAYLI paketten
okunur.

Is 6: `grammar` (cumle basina en cok uc kurallik paket) ve `--l1` ile
`grammar_l1` (notlarin cevirisi) `data/stores/grammar.sqlite`den, yalnizca
ONAYLI paketten okunur. `owner="cloze"` SABIT varsayilir (bkz. `apply.py`
docstring'i) — anahtar burada da `stable_key`dir. Adaylar (`grammar_
candidate`) BURAYA HIC YAZILMAZ: sevk edilmezler, panel ayri gosterir.
"""

from __future__ import annotations

import json
import os

from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.cloze import schema as cloze_schema
from polyvo.modules.grammar import schema as grammar_schema
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


def _usage_notes(conn) -> dict[int, str]:
    """`sense_id -> onayli Ingilizce kullanim notu` (`sense_usage_note`)."""
    return {sense_id: note for sense_id, note in conn.execute(
        "SELECT sense_id, note FROM sense_usage_note WHERE status = 'approved'")}


def _gloss_notes(conn, l1: str) -> dict[int, str]:
    """`sense_id -> gloss_l1`in kosullu notu (`sense_gloss_l1_note`)."""
    return {sense_id: note for sense_id, note in conn.execute(
        "SELECT sense_id, note FROM sense_gloss_l1_note WHERE l1 = ?", (l1,))}


def _translations(conn, l1: str) -> dict[int, tuple[str | None, str | None]]:
    """`sense_id -> (definition, usage_note)` — yalnizca ONAYLI paket."""
    return {sense_id: (definition, usage_note) for sense_id, definition, usage_note in
            conn.execute("SELECT sense_id, definition, usage_note FROM"
                        " sense_translation WHERE l1 = ? AND status = 'approved'",
                        (l1,))}


def _translation_examples(conn, l1: str) -> dict[int, list[str]]:
    """`sense_id -> ceviri ornek cumleleri` (`sense_translation_examples`)."""
    out: dict[int, list[str]] = {}
    for sense_id, text in conn.execute(
            "SELECT sense_id, text FROM sense_translation_examples"
            " WHERE l1 = ? ORDER BY sense_id, seq", (l1,)):
        out.setdefault(sense_id, []).append(text)
    return out


def _cloze_packages() -> dict[int, list[dict]]:
    """`sense_id -> [{sentence, answer, options}]` — yalnizca ONAYLI paketler.

    Zorluk etiketi DISARI YAZILMAZ: sira zaten zorlugu belirler ve dosyadan
    geri okunmaz (`apply.py`), yazmak yaniltici olurdu."""
    conn = cloze_schema.open_cloze_db()
    try:
        options: dict[tuple[int, int], list[str]] = {}
        for sense_id, seq, text in conn.execute(
                "SELECT sense_id, seq, text FROM sense_cloze_option"
                " ORDER BY sense_id, seq, opt_seq"):
            options.setdefault((sense_id, seq), []).append(text)
        out: dict[int, list[dict]] = {}
        for sense_id, seq, sentence, answer in conn.execute(
                "SELECT q.sense_id, q.seq, q.sentence, q.answer"
                " FROM sense_cloze_question q JOIN sense_cloze c"
                "   ON c.sense_id = q.sense_id"
                " WHERE c.status = 'approved' ORDER BY q.sense_id, q.seq"):
            out.setdefault(sense_id, []).append({
                "sentence": sentence, "answer": answer,
                "options": options.get((sense_id, seq), [])})
        return out
    finally:
        conn.close()


def _cloze_translations(l1: str) -> dict[int, list[str]]:
    """`sense_id -> cevrilmis cloze cumleleri` (yalnizca ONAYLI ceviri)."""
    conn = cloze_schema.open_cloze_db()
    try:
        out: dict[int, list[str]] = {}
        for sense_id, sentence in conn.execute(
                "SELECT s.sense_id, s.sentence"
                " FROM sense_cloze_translation_sentence s"
                " JOIN sense_cloze_translation t"
                "   ON t.sense_id = s.sense_id AND t.l1 = s.l1"
                " WHERE s.l1 = ? AND t.status = 'approved'"
                " ORDER BY s.sense_id, s.seq", (l1,)):
            out.setdefault(sense_id, []).append(sentence)
        return out
    finally:
        conn.close()


def _cloze_rationales() -> dict[int, list[dict]]:
    """`sense_id -> [{"hint":..., "reasons":[...]}]` — yalnizca ONAYLI paket.

    Zorluk/opt_seq etiketi disari YAZILMAZ: sira zaten belirler ve dosyadan
    geri okunmaz (`apply.py`), yazmak yaniltici olurdu."""
    conn = cloze_schema.open_cloze_db()
    try:
        hints: dict[tuple[int, int], str] = {}
        for sense_id, seq, hint in conn.execute(
                "SELECT sense_id, seq, hint FROM sense_cloze_hint"
                " WHERE hint_seq = 1 ORDER BY sense_id, seq"):
            hints[(sense_id, seq)] = hint
        reasons: dict[tuple[int, int], list[str]] = {}
        for sense_id, seq, reason in conn.execute(
                "SELECT sense_id, seq, reason FROM sense_cloze_option_reason"
                " ORDER BY sense_id, seq, opt_seq"):
            reasons.setdefault((sense_id, seq), []).append(reason)
        out: dict[int, list[dict]] = {}
        for sense_id, seq in conn.execute(
                "SELECT q.sense_id, q.seq FROM sense_cloze_question q"
                " JOIN sense_cloze_rationale c ON c.sense_id = q.sense_id"
                " WHERE c.status = 'approved' ORDER BY q.sense_id, q.seq"):
            out.setdefault(sense_id, []).append({
                "hint": hints.get((sense_id, seq), ""),
                "reasons": reasons.get((sense_id, seq), [])})
        return out
    finally:
        conn.close()


def _cloze_rationale_translations(l1: str) -> dict[int, list[dict]]:
    """`cloze_rationale`nin ceviri karsiligi — yalnizca ONAYLI ceviri."""
    conn = cloze_schema.open_cloze_db()
    try:
        hints: dict[tuple[int, int], str] = {}
        for sense_id, seq, hint in conn.execute(
                "SELECT sense_id, seq, hint FROM sense_cloze_hint_l1"
                " WHERE l1 = ? AND hint_seq = 1 ORDER BY sense_id, seq",
                (l1,)):
            hints[(sense_id, seq)] = hint
        reasons: dict[tuple[int, int], list[str]] = {}
        for sense_id, seq, reason in conn.execute(
                "SELECT sense_id, seq, reason FROM sense_cloze_option_reason_l1"
                " WHERE l1 = ? ORDER BY sense_id, seq, opt_seq", (l1,)):
            reasons.setdefault((sense_id, seq), []).append(reason)
        out: dict[int, list[dict]] = {}
        for sense_id, seq in conn.execute(
                "SELECT t.sense_id, h.seq"
                " FROM sense_cloze_rationale_translation t"
                " JOIN sense_cloze_hint_l1 h"
                "   ON h.sense_id = t.sense_id AND h.l1 = t.l1"
                " WHERE t.l1 = ? AND t.status = 'approved'"
                " ORDER BY t.sense_id, h.seq", (l1,)):
            out.setdefault(sense_id, []).append({
                "hint": hints.get((sense_id, seq), ""),
                "reasons": reasons.get((sense_id, seq), [])})
        return out
    finally:
        conn.close()


def _grammar_packages() -> dict[str, list[dict]]:
    """`stable_key -> [{"rules": [...]}]` cumle sirasinda — yalnizca ONAYLI
    grammar paketi (`owner="cloze"` sabit varsayimla)."""
    conn = grammar_schema.open_grammar_db()
    try:
        rules_by_ref: dict[str, list[dict]] = {}
        for ref, rank, rule_id, trigger, note in conn.execute(
                "SELECT ref, rank, rule_id, trigger, note FROM"
                " sentence_grammar_rule WHERE owner = 'cloze'"
                " ORDER BY ref, rank"):
            rules_by_ref.setdefault(ref, []).append({
                "rank": rank, "rule_id": rule_id, "trigger": trigger,
                "note": note})
        out: dict[str, list[dict]] = {}
        for group_key, ref in conn.execute(
                "SELECT DISTINCT g.group_key, r.ref FROM sentence_grammar g"
                " JOIN sentence_grammar_rule r ON r.owner = g.owner"
                "   AND r.group_key = g.group_key"
                " WHERE g.owner = 'cloze' AND g.status = 'approved'"
                " ORDER BY g.group_key, r.ref"):
            out.setdefault(group_key, []).append(
                {"rules": rules_by_ref.get(ref, [])})
        return out
    finally:
        conn.close()


def _grammar_translations(l1: str) -> dict[str, list[dict]]:
    """`grammar`nin ceviri karsiligi — yalnizca ONAYLI ceviri. `rule_id`/
    `trigger` cevrilmedigi icin BURADA YOKTUR, yalnizca `rank` + `note`."""
    conn = grammar_schema.open_grammar_db()
    try:
        notes_by_ref: dict[str, list[dict]] = {}
        for ref, rank, note in conn.execute(
                "SELECT ref, rank, note FROM sentence_grammar_rule_l1"
                " WHERE l1 = ? ORDER BY ref, rank", (l1,)):
            notes_by_ref.setdefault(ref, []).append(
                {"rank": rank, "note": note})
        out: dict[str, list[dict]] = {}
        for group_key, ref in conn.execute(
                "SELECT DISTINCT t.group_key, r.ref FROM"
                " sentence_grammar_translation t JOIN sentence_grammar_rule r"
                "   ON r.owner = t.owner AND r.group_key = t.group_key"
                " WHERE t.owner = 'cloze' AND t.l1 = ? AND t.status = 'approved'"
                " ORDER BY t.group_key, r.ref", (l1,)):
            out.setdefault(group_key, []).append(
                {"rules": notes_by_ref.get(ref, [])})
        return out
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
            " tier, status, reject_reason FROM sense_cards"
            + where + " ORDER BY item_id", params).fetchall()
        if limit is not None:
            cards = cards[:limit]

        usage_notes = _usage_notes(conn)
        glosses, gloss_notes, translations, translation_examples = {}, {}, {}, {}
        if l1:
            glosses = {row[0]: row[1] for row in conn.execute(
                "SELECT sense_id, gloss FROM sense_gloss_l1 WHERE l1 = ?", (l1,))}
            gloss_notes = _gloss_notes(conn, l1)
            translations = _translations(conn, l1)
            translation_examples = _translation_examples(conn, l1)
        examples: dict[int, list[str]] = {}
        for sense_id, text in conn.execute(
                "SELECT sense_id, text FROM sense_examples ORDER BY sense_id, seq"):
            examples.setdefault(sense_id, []).append(text)
    finally:
        conn.close()

    cloze_packages = _cloze_packages()
    cloze_translations = _cloze_translations(l1) if l1 else {}
    cloze_rationales = _cloze_rationales()
    cloze_rationale_translations = (
        _cloze_rationale_translations(l1) if l1 else {})
    grammar_packages = _grammar_packages()
    grammar_translations = _grammar_translations(l1) if l1 else {}

    out = []
    for sense_id, item_id, key, gloss_en, register, tier, st, reason in cards:
        headword, pos = names.get(item_id, ("", ""))
        row = {
            record.KEY_FIELD: key, "item_id": item_id, "sense_id": sense_id,
            "headword": headword, "pos": pos, "tier": tier, "status": st,
            "gloss_en": gloss_en, "register": register,
            "usage_note": usage_notes.get(sense_id),
            "examples": examples.get(sense_id, []),
            "cloze": cloze_packages.get(sense_id, []),
            "cloze_rationale": cloze_rationales.get(sense_id, []),
            "grammar": grammar_packages.get(key, []),
        }
        if l1:
            row["gloss_l1"] = glosses.get(sense_id)
            row["gloss_note_l1"] = gloss_notes.get(sense_id)
            definition, translated_note = translations.get(sense_id, (None, None))
            row["definition_l1"] = definition
            row["usage_note_l1"] = translated_note
            row["examples_l1"] = translation_examples.get(sense_id, [])
            row["cloze_l1"] = cloze_translations.get(sense_id, [])
            row["cloze_rationale_l1"] = cloze_rationale_translations.get(
                sense_id, [])
            row["grammar_l1"] = grammar_translations.get(key, [])
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
