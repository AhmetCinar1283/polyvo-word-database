"""
Katalog aciklamasi ceviri promptu — kural basina TEK cagri, `name_en` +
`short_en` birlikte cevrilir. `rule_id` BURADA DA cevrilmez, prompta
GORUNMEZ (model gormedigi bir seyi yanlislikla cevirmez).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alani arar.
SCHEMA_HINT = '{"name": "<translated name>", "short": "<translated short description>"}'


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir katalog kuralinin isim + kisa aciklama ceviri prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    name_en = unit.data["name_en"]
    short_en = unit.data["short_en"]

    parts = [
        f"You are a bilingual translator working into {l1_name}.",
        "This is the catalog entry for an English grammar rule, shown to "
        "language learners.",
        "",
        f'Name (English): "{name_en}"',
        f'Short description (English): "{short_en}"',
        "",
        f"Translate BOTH into {l1_name}, keeping the SAME meaning.",
        "Rules:",
        "- Translate naturally — NOT word for word.",
        "- Keep the name SHORT (a label, not a sentence).",
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
