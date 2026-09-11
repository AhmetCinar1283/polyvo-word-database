"""
Kullanim notu promptu — kart promptundan AYRI ve KUCUK, tek ise odakli.

Kritik kural (Is 3): not KOSULLUDUR. Modele "istersen doldur" demek olculdu
ve sonucu 957'de 4 oldu (`prompt.py`nin eski SCHEMA_HINT'i). Bunun yerine
model once bir SEBEP secer; sebep "none" ise not BOS BIRAKILIR ve bu dogru
cevaptir — QA bunu onaylar, reddetmez.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit

#: Modelin secebilecegi sebepler — QA tam bu kumeyi bilir.
REASONS = ("idiom", "false_friend", "culture_gap", "common_error", "none")

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = ('{"reason": "<one of: idiom | false_friend | culture_gap | '
              'common_error | none>", '
              '"usage_note": "<short note explaining the reason, or empty '
              'string when reason is none>"}')


def build(unit: Unit, retry_note: str | None = None) -> str:
    """Bir birimin kullanim notu prompt metnini kurar."""
    card = unit.data["card"]
    headword = unit.data["headword"]
    pos = unit.data["pos"]

    parts = [
        "You are a lexicographer deciding whether a learner's dictionary "
        "entry needs a usage note.",
        f'Word: "{headword}"   part of speech: {pos}',
        f'Definition: {card["gloss_en"]}',
    ]
    if card.get("examples"):
        parts.append("Example sentences:")
        parts.extend(f"  - {ex}" for ex in card["examples"])

    parts += [
        "",
        "A usage note is needed ONLY when one of these applies:",
        "- idiom: the word/phrase is used idiomatically, not literally.",
        "- false_friend: a literal translation would give a WRONG meaning "
        "in many learners' native languages.",
        "- culture_gap: the concept has no clean equivalent in many native "
        "languages/cultures.",
        "- common_error: learners commonly misuse this word in a specific, "
        "predictable way.",
        "If NONE of these apply, choose reason \"none\" and leave "
        "usage_note EMPTY — that is the correct answer for most words, "
        "do NOT invent a note.",
        "",
        "Rules:",
        "- usage_note (when not empty): one short sentence, plain English, "
        "that does NOT just restate the definition in different words.",
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(p for p in parts if p is not None)
