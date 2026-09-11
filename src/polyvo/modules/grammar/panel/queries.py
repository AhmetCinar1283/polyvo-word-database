"""
Panel sayfasinin depoya sordugu SORULAR — HTML burada yoktur.

Salt okunur: panel odenmis depoya dokunmaz. Duzeltme yolu `review` app'idir.

Grammar'in cumle METNI kendi deposunda YOKTUR (yalnizca `ref`/`rank`/
`rule_id` tutulur) — cumle metni `APP.sentences` KATKI SEAM'inden, `grammar`
uretim hattinin KENDI okudugu ayni yoldan (`units.py`) yeniden okunur. Bu,
"grammar hicbir kardes modules/* paketini import etmez" sozunun panelde de
GECERLI kalmasinin yoludur — `cloze`yu DOGRUDAN okumak yerine seam kullanilir.

BAYATLIK burada da GIZLENMEZ (Is 4/5'teki §17/§18 deseniyle AYNI): depodaki
`source_sha256` seam'den O ANKI cumlelerle yeniden hesaplananla karsilastirilir.

Adaylar (`grammar_candidate`) AYRI bir gorunumdedir ve "sevk edilmez"
etiketiyle gosterilir — katalogdan bagimsiz, hicbir cumleye kural olarak
BAGLANMAZLAR (Is 6 §9).
"""

from __future__ import annotations

from polyvo.core import config, paths
from polyvo.modules.grammar import schema
from polyvo.modules.grammar import units as grammar_units
from polyvo.modules.grammar.catalog import all_rules
from polyvo.modules.grammar.catalog import get as catalog_get

#: Liste sayfasinda bir defada gosterilecek en fazla satir.
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def _default_tag() -> str | None:
    """Aktif tag; belirsizse `None` doner — panel bu yuzden COKMEZ, o
    zaman yalnizca BAYATLIK bilinmez kalir (gosterim yine devam eder)."""
    try:
        return paths.resolve_tag(None)
    except SystemExit:
        return None


def _current_units() -> dict[str, object]:
    """`"owner|group_key" -> Unit` — seam'den O ANKI cumleler. Tag/L2
    cozulemezse (COK ya da HIC workspace) bos sozluk doner."""
    tag = _default_tag()
    if tag is None:
        return {}
    try:
        return {u.key: u for u in
               grammar_units.load_units(tag, config.default_l2())}
    except Exception:
        return {}


def counts() -> list[tuple[str, int]]:
    """Duruma gore paket sayilari (cok olandan aza)."""
    conn = schema.open_grammar_db()
    try:
        return [(row[0], row[1]) for row in conn.execute(
            "SELECT status, COUNT(*) FROM sentence_grammar GROUP BY status"
            " ORDER BY COUNT(*) DESC")]
    finally:
        conn.close()


def candidate_count() -> int:
    """SEVK EDILMEYEN aday sayisi — liste sayfasinda ayrica gorunur."""
    conn = schema.open_grammar_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM grammar_candidate").fetchone()[0]
    finally:
        conn.close()


def list_groups(*, status: str | None = None,
                limit: int = DEFAULT_LIMIT) -> list[dict]:
    """Grammar paketlerini `(owner, group_key)` sirasinda listeler."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    current = _current_units()
    where, params = [], []
    if status:
        where.append("g.status = ?")
        params.append(status)
    clause = (" WHERE " + " AND ".join(where)) if where else ""

    conn = schema.open_grammar_db()
    try:
        rows = conn.execute(
            "SELECT g.owner, g.group_key, g.status, g.reject_reason,"
            " g.warnings, g.tier, g.source, g.source_sha256, COUNT(r.rank)"
            " FROM sentence_grammar g LEFT JOIN sentence_grammar_rule r"
            "   ON r.owner = g.owner AND r.group_key = g.group_key"
            + clause +
            " GROUP BY g.owner, g.group_key"
            " ORDER BY g.owner, g.group_key", params).fetchall()
    finally:
        conn.close()

    out = []
    for owner, group_key, st, reason, warnings, tier, source, src_hash, n in rows:
        unit = current.get(f"{owner}|{group_key}")
        stale = unit is not None and unit.data["source_sha256"] != src_hash
        out.append({"owner": owner, "group_key": group_key, "status": st,
                    "reject_reason": reason, "warnings": warnings,
                    "tier": tier, "source": source, "rules": n,
                    "stale": stale})
        if len(out) >= limit:
            break
    return out


def sentence_package(owner: str, group_key: str) -> dict | None:
    """Tek bir grubun paketi: cumleler + kurallar + adaylar + ceviriler;
    yoksa `None`."""
    conn = schema.open_grammar_db()
    try:
        row = conn.execute(
            "SELECT status, reject_reason, warnings, tier, source, model,"
            " updated_at, source_sha256 FROM sentence_grammar"
            " WHERE owner = ? AND group_key = ?", (owner, group_key)).fetchone()
        if row is None:
            return None
        (status, reject_reason, warnings, tier, source, model, updated_at,
         src_hash) = row

        rules_by_ref: dict[str, list[dict]] = {}
        for ref, rank, rule_id, trigger, note in conn.execute(
                "SELECT ref, rank, rule_id, trigger, note FROM"
                " sentence_grammar_rule WHERE owner = ? AND group_key = ?"
                " ORDER BY ref, rank", (owner, group_key)):
            rules_by_ref.setdefault(ref, []).append({
                "rank": rank, "rule_id": rule_id, "trigger": trigger,
                "note": note, "catalog": catalog_get(rule_id)})

        candidates_by_ref: dict[str, list[dict]] = {}
        for ref, seq, name, trigger, rationale, cand_status in conn.execute(
                "SELECT ref, seq, proposed_name, trigger, rationale, status"
                " FROM grammar_candidate WHERE owner = ?", (owner,)):
            # `ref` bicimi `<group_key>:<seq>`dir; grup esitligi burada TAM
            # kesme ile sinanir (LIKE deseniyle DEGIL — bir group_key'in
            # baskasinin ONEKI olma riskini tasimaz).
            ref_group, _, _ref_seq = ref.rpartition(":")
            if ref_group != group_key:
                continue
            candidates_by_ref.setdefault(ref, []).append({
                "seq": seq, "proposed_name": name, "trigger": trigger,
                "rationale": rationale, "status": cand_status})

        translations: dict[str, dict] = {}
        for l1, t_status, _t_hash in conn.execute(
                "SELECT l1, status, note_sha256 FROM"
                " sentence_grammar_translation WHERE owner = ?"
                " AND group_key = ?", (owner, group_key)):
            notes_by_ref: dict[str, list[dict]] = {}
            for ref, rank, note in conn.execute(
                    "SELECT ref, rank, note FROM sentence_grammar_rule_l1"
                    " WHERE owner = ? AND l1 = ? AND ref IN (SELECT ref FROM"
                    " sentence_grammar_rule WHERE owner = ? AND group_key = ?)",
                    (owner, l1, owner, group_key)):
                notes_by_ref.setdefault(ref, []).append(
                    {"rank": rank, "note": note})
            translations[l1] = {"status": t_status, "notes": notes_by_ref}
    finally:
        conn.close()

    unit = _current_units().get(f"{owner}|{group_key}")
    sentences = unit.data["sentences"] if unit is not None else []
    stale = unit is not None and unit.data["source_sha256"] != src_hash

    return {"owner": owner, "group_key": group_key, "status": status,
            "reject_reason": reject_reason, "warnings": warnings,
            "tier": tier, "source": source, "model": model,
            "updated_at": updated_at, "stale": stale, "sentences": sentences,
            "rules_by_ref": rules_by_ref,
            "candidates_by_ref": candidates_by_ref,
            "translations": translations}


def list_rules() -> list[dict]:
    """Katalogdaki HER (birlestirilmemis) kural + kac cumlede kullanildigi
    (cok kullanilan once) — kurala gore gorunumun listesi."""
    conn = schema.open_grammar_db()
    try:
        counts_by_id = {row[0]: row[1] for row in conn.execute(
            "SELECT r.rule_id, COUNT(*) FROM sentence_grammar_rule r"
            " JOIN sentence_grammar g ON g.owner = r.owner"
            "   AND g.group_key = r.group_key"
            " WHERE g.status = 'approved' GROUP BY r.rule_id")}
    finally:
        conn.close()
    out = [{"rule": rule, "uses": counts_by_id.get(rule.id, 0)}
          for rule in all_rules() if rule.merged_into is None]
    out.sort(key=lambda item: (-item["uses"], item["rule"].id))
    return out


def rule_usage(rule_id: str) -> dict | None:
    """Bir katalog kuralinin KULLANILDIGI TUM cumleler; kural katalogda
    yoksa `None`."""
    rule = catalog_get(rule_id)
    if rule is None:
        return None
    conn = schema.open_grammar_db()
    try:
        rows = conn.execute(
            "SELECT r.owner, r.group_key, r.ref, r.rank, r.trigger, r.note"
            " FROM sentence_grammar_rule r JOIN sentence_grammar g"
            "   ON g.owner = r.owner AND g.group_key = r.group_key"
            " WHERE r.rule_id = ? AND g.status = 'approved'"
            " ORDER BY r.owner, r.group_key, r.ref, r.rank",
            (rule_id,)).fetchall()
    finally:
        conn.close()
    usages = [dict(zip(
        ("owner", "group_key", "ref", "rank", "trigger", "note"), row))
        for row in rows]
    return {"rule": rule, "usages": usages}


def candidates(*, limit: int = DEFAULT_LIMIT) -> list[dict]:
    """SEVK EDILMEYEN aday listesi — kurala/cumleye gore gorunumden AYRI,
    katalogdan BAGIMSIZ (Is 6 §9)."""
    limit = max(1, min(int(limit), MAX_LIMIT))
    conn = schema.open_grammar_db()
    try:
        rows = conn.execute(
            "SELECT owner, ref, seq, proposed_name, trigger, rationale,"
            " status, updated_at FROM grammar_candidate"
            " ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()
    return [dict(zip(
        ("owner", "ref", "seq", "proposed_name", "trigger", "rationale",
         "status", "updated_at"), row)) for row in rows]
