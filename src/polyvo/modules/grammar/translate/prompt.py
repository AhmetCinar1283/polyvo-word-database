"""
Grammar not cevirisi promptu — grup basina dil basina TEK cagri, gruptaki
TUM notlar birlikte.

`rule_id` ve `trigger` ASLA cevrilmez (Is 6 §18): `trigger` cumlenin
Ingilizce parcasidir. Bu prompt yalnizca `note`u cevirir; `trigger` BAGLAM
olarak verilir (model notun neye atifta bulundugunu gorsun diye), cevap
alaninda GERI ISTENMEZ.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alani arar.
SCHEMA_HINT = '{"notes": ["<translation 1>", "<translation 2>", "..."]}'


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir grubun kural notlarinin ceviri prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    items = unit.data["rules"]

    parts = [
        f"You are a bilingual translator working into {l1_name}.",
        "These are short, sentence-specific notes explaining how an "
        "English grammar rule shows up in a particular sentence.",
        "",
        "Notes (English):",
    ]
    for i, item in enumerate(items, start=1):
        parts.append(f'  {i}. [rule trigger: "{item["trigger"]}"] {item["note"]}')
    parts += [
        "",
        f"Translate all {len(items)} notes into {l1_name}, keeping the "
        "SAME meaning. The bracketed trigger is CONTEXT ONLY — do not "
        "include it, translated or not, in your answer.",
        "Rules:",
        "- Translate naturally — NOT word for word.",
        f"- EXACTLY {len(items)} translations, in the SAME order.",
        "- Do not add anything the original text does not say.",
    ]
    if rules.PROMPT_RULES:
        parts.append(rules.PROMPT_RULES)
    parts += [
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(parts)
