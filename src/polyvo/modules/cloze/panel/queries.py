"""
Panel sayfasinin depoya sordugu SORULAR — HTML burada yoktur.

Salt okunur: panel odenmis depoya dokunmaz. Duzeltme yolu `review` app'idir.

TEKDUZELIK SAYIMI da buradadir: uretilen cumlelerin kac FARKLI acilis kalibi
kullandigi. Ayni tanimi QA kapisi da kullanir (`qa/variety.py::opening_ngram`)
— sayilan sey ile reddedilen sey ayni olsun diye.

Is 5: `package()` ipucu/aciklama paketini de tasir (`_rationale_package`).
BAYAT (hash tutmayan) satir sessizce gizlenmez, acikca isaretlenir (§18).
"""

from __future__ import annotations

from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.cloze import render, schema
from polyvo.modules.cloze.qa.variety import opening_ngram
from polyvo.modules.cloze.rationale import fingerprint as rationale_fingerprint

#: Liste sayfasinda bir defada gosterilecek en fazla satir.
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _names() -> dict[str, tuple[str, str]]:
    """`stable_key -> (headword, pos)` — kimlik deposundan, TEK sorgu."""
    conn = curriculum_schema.open_identity_db()
    try:
        return {row[0]: (row[1], row[2]) for row in
                conn.execute("SELECT stable_key, headword, pos FROM items")}
    finally:
        conn.close()


def counts() -> list[tuple[str, int]]:
    """Duruma gore paket sayilari (cok olandan aza)."""
    conn = schema.open_cloze_db()
    try:
        return [(row[0], row[1]) for row in conn.execute(
            "SELECT status, COUNT(*) FROM sense_cloze GROUP BY status"
            " ORDER BY COUNT(*) DESC")]
    finally:
        conn.close()


def variety_summary() -> dict:
    """Tekduzelik olcumu: toplam cumle, farkli acilis kalibi, en sik kalip."""
    conn = schema.open_cloze_db()
    try:
        sentences = [row[0] for row in conn.execute(
            "SELECT sentence FROM sense_cloze_question")]
    finally:
        conn.close()
    openings: dict[str, int] = {}
    for sentence in sentences:
        key = opening_ngram(sentence)
        openings[key] = openings.get(key, 0) + 1
    top = sorted(openings.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    return {"sentences": len(sentences), "distinct_openings": len(openings),
            "top": top}


def list_senses(*, status: str | None = None, search: str | None = None,
                limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Cloze paketlerini `stable_key` sirasinda listeler."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    names = _names()
    where, params = [], []
    if status:
        where.append("c.status = ?")
        params.append(status)
    clause = (" WHERE " + " AND ".join(where)) if where else ""

    conn = schema.open_cloze_db()
    try:
        rows = conn.execute(
            "SELECT c.sense_id, c.stable_key, c.status, c.reject_reason,"
            " c.warnings, c.tier, c.source, COUNT(q.seq)"
            " FROM sense_cloze c LEFT JOIN sense_cloze_question q"
            "   ON q.sense_id = c.sense_id" + clause +
            " GROUP BY c.sense_id ORDER BY c.stable_key", params).fetchall()
    finally:
        conn.close()

    out = []
    for sense_id, key, st, reason, warnings, tier, source, n in rows:
        headword, pos = names.get(key, (key, ""))
        if search and not headword.lower().startswith(search.lower()):
            continue
        out.append({"sense_id": sense_id, "stable_key": key, "status": st,
                    "reject_reason": reason, "warnings": warnings, "tier": tier,
                    "source": source, "questions": n, "headword": headword,
                    "pos": pos})
        if len(out) >= limit:
            break
    return out


def _rationale_package(conn, sense_id: int, questions: list[dict]) -> dict | None:
    """Bu anlamin ipucu/aciklama paketi; salt okunur panel gorunumu.

    `question_sha256` O ANKI sorulardan yeniden hesaplanir — tutmuyorsa
    BAYAT olarak isaretlenir, gizlenmez (V2-IS-5 §18)."""
    row = conn.execute(
        "SELECT status, reject_reason, tier, source, model, updated_at,"
        " question_sha256 FROM sense_cloze_rationale WHERE sense_id = ?",
        (sense_id,)).fetchone()
    if row is None:
        return None
    status, reject_reason, tier, source, model, updated_at, stored_hash = row
    current_hash = rationale_fingerprint.question_sha256([
        {"seq": q["seq"], "sentence": q["sentence"],
         "options": [text for text, _is_answer in q["options"]]}
        for q in questions])

    hints = {seq: hint for seq, hint in conn.execute(
        "SELECT seq, hint FROM sense_cloze_hint"
        " WHERE sense_id = ? AND hint_seq = 1", (sense_id,))}
    reasons: dict[int, dict[int, str]] = {}
    for seq, opt_seq, reason in conn.execute(
            "SELECT seq, opt_seq, reason FROM sense_cloze_option_reason"
            " WHERE sense_id = ?", (sense_id,)):
        reasons.setdefault(seq, {})[opt_seq] = reason

    translations: dict[str, dict] = {}
    for l1, t_status, t_hash in conn.execute(
            "SELECT l1, status, rationale_sha256"
            " FROM sense_cloze_rationale_translation WHERE sense_id = ?",
            (sense_id,)):
        t_hints = {seq: hint for seq, hint in conn.execute(
            "SELECT seq, hint FROM sense_cloze_hint_l1"
            " WHERE sense_id = ? AND l1 = ? AND hint_seq = 1",
            (sense_id, l1))}
        t_reasons: dict[int, dict[int, str]] = {}
        for seq, opt_seq, reason in conn.execute(
                "SELECT seq, opt_seq, reason FROM sense_cloze_option_reason_l1"
                " WHERE sense_id = ? AND l1 = ?", (sense_id, l1)):
            t_reasons.setdefault(seq, {})[opt_seq] = reason
        current_rationale_hash = rationale_fingerprint.rationale_sha256(
            [{"seq": seq, "hint": hint} for seq, hint in hints.items()],
            [{"seq": seq, "opt_seq": opt_seq, "reason": reason}
             for seq, opts in reasons.items()
             for opt_seq, reason in opts.items()])
        translations[l1] = {
            "status": t_status, "stale": t_hash != current_rationale_hash,
            "hints": t_hints, "reasons": t_reasons}

    return {"status": status, "reject_reason": reject_reason, "tier": tier,
            "source": source, "model": model, "updated_at": updated_at,
            "stale": stored_hash != current_hash, "hints": hints,
            "reasons": reasons, "translations": translations}


def package(stable_key: str) -> dict | None:
    """Tek bir anlamin paketi: sorular, siklar ve cevirileri; yoksa `None`."""
    names = _names()
    headword, pos = names.get(stable_key, (stable_key, ""))
    conn = schema.open_cloze_db()
    try:
        row = conn.execute(
            "SELECT sense_id, status, reject_reason, warnings, tier, source,"
            " model, updated_at FROM sense_cloze WHERE stable_key = ?",
            (stable_key,)).fetchone()
        if row is None:
            return None
        sense_id = row[0]
        questions = []
        for seq, difficulty, sentence, answer in conn.execute(
                "SELECT seq, difficulty, sentence, answer FROM"
                " sense_cloze_question WHERE sense_id = ? ORDER BY seq",
                (sense_id,)):
            options = conn.execute(
                "SELECT text, is_answer FROM sense_cloze_option"
                " WHERE sense_id = ? AND seq = ? ORDER BY opt_seq",
                (sense_id, seq)).fetchall()
            questions.append({
                "seq": seq, "difficulty": difficulty, "sentence": sentence,
                "answer": answer, "options": [(t, bool(a)) for t, a in options],
                "blanked": render.blanked(sentence, headword)})
        translations: dict[str, list[str]] = {}
        for l1, sentence in conn.execute(
                "SELECT l1, sentence FROM sense_cloze_translation_sentence"
                " WHERE sense_id = ? ORDER BY l1, seq", (sense_id,)):
            translations.setdefault(l1, []).append(sentence)
        rationale = _rationale_package(conn, sense_id, questions)
    finally:
        conn.close()

    return {"stable_key": stable_key, "headword": headword, "pos": pos,
            "sense_id": sense_id, "status": row[1], "reject_reason": row[2],
            "warnings": row[3], "tier": row[4], "source": row[5],
            "model": row[6], "updated_at": row[7], "questions": questions,
            "translations": translations, "rationale": rationale}
