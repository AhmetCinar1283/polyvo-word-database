"""
BICIM kapisi — sayilabilir olan her sey. Hepsi garanti edilebilir, hepsi
REDDEDER.

Bu kapi cevabi ayni zamanda NORMALLESTIRIR: sonraki kapilar artik "acaba
liste mi, acaba `seq` sirali mi" diye sormaz, temiz bir yapiyla calisir.
`candidates` bu asamada REDDETMEZ — bicimi bozuksa o cumlenin adaylari
sessizce BOS sayilir, tum paketi cope atmaya degmez.
"""

from __future__ import annotations

from polyvo.modules.grammar import model as model_const


def _text(value) -> str:
    """Modelin dondurdugu degeri guvenli bir metne cevirir."""
    return value.strip() if isinstance(value, str) else ""


def _check_rules(raw_rules: object) -> tuple[str | None, list[dict]]:
    """Bir cumlenin `rules` listesini dogrular ve normallestirir."""
    if not isinstance(raw_rules, list) or not (
            model_const.MIN_RULES_PER_SENTENCE
            <= len(raw_rules) <= model_const.MAX_RULES_PER_SENTENCE):
        return "kural_sayisi_sinir_disi", []

    rules: list[dict] = []
    seen_ranks: set[int] = set()
    for item in raw_rules:
        if not isinstance(item, dict):
            return "kural_nesne_degil", []
        rank = item.get("rank")
        if not isinstance(rank, int) or rank in seen_ranks:
            return "rank_boslukli_ya_da_yinelenen", []
        seen_ranks.add(rank)

        rule_id = _text(item.get("rule_id"))
        trigger = _text(item.get("trigger"))
        note = _text(item.get("note"))
        if not rule_id:
            return "rule_id_bos", []
        if not trigger:
            return "trigger_bos", []
        if not (model_const.NOTE_MIN_CHARS <= len(note)
                <= model_const.NOTE_MAX_CHARS):
            return "not_uzunluk_bandi_disinda", []
        rules.append({"rank": rank, "rule_id": rule_id, "trigger": trigger,
                      "note": note})

    if seen_ranks != set(range(1, len(rules) + 1)):
        return "rank_1_n_araligi_disinda", []
    rules.sort(key=lambda r: r["rank"])
    return None, rules


def _check_candidates(raw_candidates: object) -> list[dict]:
    """Bir cumlenin `candidates` listesini normallestirir. BICIMI bozuksa
    (liste degilse ya da ogeler eksikse) o cumlenin adaylari sessizce
    BOS sayilir — tum paketi bir aday alani yuzunden cope atmaya degmez."""
    if not isinstance(raw_candidates, list):
        return []
    out: list[dict] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        proposed_name = _text(item.get("proposed_name"))
        trigger = _text(item.get("trigger"))
        rationale = _text(item.get("rationale"))
        if proposed_name and trigger and rationale:
            out.append({"proposed_name": proposed_name, "trigger": trigger,
                        "rationale": rationale})
    return out


def check(parsed: dict | None, unit) -> tuple[str | None, list[dict]]:
    """(red_sebebi, normallestirilmis_cumleler) dondurur.

    Donen her oge `{"seq", "ref", "text", "rules", "candidates"}` tasir —
    `ref`/`text` unit'in KENDI verisinden gelir, modelden DEGIL (model yalnizca
    `seq`i geri yollar, boylece cumle metni modelin elinde DEGISTIRILEMEZ)."""
    if not isinstance(parsed, dict):
        return "cevap_json_degil", []

    raw = parsed.get("sentences")
    expected = unit.data["sentences"]
    if not isinstance(raw, list) or len(raw) != len(expected):
        return "cumle_sayisi_uyusmuyor", []

    out: list[dict] = []
    for expected_s, item in zip(expected, raw):
        if not isinstance(item, dict):
            return "cumle_nesne_degil", []
        if item.get("seq") != expected_s["seq"]:
            return "seq_sirasi_bozuk", []

        reject, rules = _check_rules(item.get("rules"))
        if reject:
            return reject, []
        candidates = _check_candidates(item.get("candidates"))

        out.append({
            "seq": expected_s["seq"], "ref": expected_s["ref"],
            "text": expected_s["text"], "cefr": expected_s.get("cefr"),
            "rules": rules, "candidates": candidates,
        })
    return None, out
