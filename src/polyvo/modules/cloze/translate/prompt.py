"""
Cloze ceviri promptu — anlam basina dil basina TEK cagri, uc cumle birlikte.

CEVRILEN SEY CUMLEDIR, SIKLAR DEGIL (§14). Siklar bu prompta HIC girmez:
bu bir Ingilizce alistirmasidir, siklarin cevirisi soruyu anlamsizlastirir.
Cevrilen cumle boslugu DOLDURULMUS tam cumledir; ne zaman gosterilecegi
uygulamanin karari.

Uc cumlenin birlikte cevrilmesi Is 3'un desenidir: model anlamin tamamini
gorunce terimi tutarli cevirir. Ikinci bir "birebir ceviri" alani YOKTUR.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alani arar.
SCHEMA_HINT = ('{"sentences": ["<translation of sentence 1>", '
               '"<translation of sentence 2>", "<translation of sentence 3>"]}')


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir birimin cloze ceviri prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    sentences = unit.data["sentences"]
    card = unit.data["card"]

    parts = [
        f"You are a bilingual translator working into {l1_name}.",
        f'These sentences all use the word "{unit.data["headword"]}" '
        f'({unit.data["pos"]}) in this sense: {card["gloss_en"]}',
        "",
        "Sentences (English):",
    ]
    parts.extend(f"  {i}. {s}" for i, s in enumerate(sentences, start=1))
    parts += [
        "",
        f"Translate all {len(sentences)} sentences into {l1_name}, keeping "
        "the SAME term for the word in every sentence so a learner sees one "
        "consistent translation.",
        "Rules:",
        "- Translate naturally — NOT word for word. Produce what a native "
        "speaker would actually say.",
        f"- EXACTLY {len(sentences)} translations, in the SAME order.",
        "- Translate the sentence as it stands; do not add explanations and "
        "do not mark any gap.",
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
