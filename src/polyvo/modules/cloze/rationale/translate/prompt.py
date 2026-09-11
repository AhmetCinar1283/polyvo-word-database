"""
Cloze ipucu/aciklama ceviri promptu — anlam basina dil basina TEK cagri, uc
ipucu + on iki aciklama birlikte.

Aciklamalarda gecen sikkin Ingilizce kelimesi KASITLI olarak cevrilmez (Is 4
§14: siklar hic cevrilmez) — bu prompt modele bunu ACIKCA soyler, aksi halde
dil kapisi (§16) DOGRU bir ceviriyi "model cevirmemis" sanip reddedebilir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = ('{"hints": ["<translation 1>", "<translation 2>", '
              '"<translation 3>"], '
              '"reasons": ["<translation 1>", "...", "<translation 12>"]}')


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir birimin ipucu/aciklama ceviri prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    hints = sorted(unit.data["hints"], key=lambda h: h["seq"])
    reasons = sorted(unit.data["reasons"], key=lambda r: (r["seq"], r["opt_seq"]))

    parts = [
        f"You are a bilingual translator working into {l1_name}.",
        "These texts are hints and per-option explanations for cloze "
        f'questions about the word "{unit.data["headword"]}" '
        f'({unit.data["pos"]}).',
        "",
        "Hints (English):",
    ]
    parts.extend(f"  {i}. {h['hint']}" for i, h in enumerate(hints, start=1))
    parts += ["", "Explanations (English):"]
    parts.extend(f"  {i}. {r['reason']}" for i, r in enumerate(reasons, start=1))
    parts += [
        "",
        f"Translate all {len(hints)} hints and {len(reasons)} explanations "
        f"into {l1_name}, keeping the SAME meaning.",
        "Rules:",
        "- Translate naturally — NOT word for word.",
        f"- EXACTLY {len(hints)} hint translations and {len(reasons)} "
        "explanation translations, in the SAME order.",
        "- Each explanation discusses one English word from the exercise. "
        "KEEP that English word UNTRANSLATED inside the explanation — "
        f"translate everything else into {l1_name}.",
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
