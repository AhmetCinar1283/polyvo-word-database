"""
Prompt metni — modelden ISTENEN sey burada, TEK yerde tanimlidir.

Iki kural bilincli: (1) sozluk tohumu prompt'a "dogru cevap" olarak degil
BAGLAM olarak girer — model kopyalamak zorunda degildir; (2) L1 bicim
kurallari `core/lang/`den gelir, buraya dil gomulmez.

`retry_note` bir onceki denemenin RED SEBEBIDIR: metni degistirdigi icin
onbellek anahtari da degisir, yani yeniden deneme gercekten yeni cevap alir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules
from polyvo.modules.lexicon_card.seed import Seed

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{
  "gloss_en": "<short English definition, one sentence, no example>",
  "register": "<one of: neutral | formal | informal | slang | technical>",
  "usage_note": "<optional short note, or empty string>",
  "gloss_l1": "<the single best {l1_name} equivalent>",
  "examples": ["<natural sentence using the word>", "<a second, different one>"]
}"""

#: Kabul edilen `register` degerleri; disindakiler QA'da `neutral`e duser.
REGISTERS = ("neutral", "formal", "informal", "slang", "technical")

EXAMPLE_COUNT = 2


def _context_block(seed: Seed) -> str | None:
    """Tohumdaki kanit parcalarini prompt'a okunakli bir blok olarak koyar.
    Tohum yoksa `None` — bos satir birakmasin."""
    if not seed.context:
        return None
    lines = ["", "Reference material (may be noisy or for a different sense —",
             "use it only as a hint, do NOT copy it):"]
    for kind in ("definition", "synonym", "example"):
        for payload in seed.context.get(kind, []):
            lines.append(f"  - {kind}: {payload}")
    return "\n".join(lines)


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir birimin prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    seed: Seed = unit.data.get("seed") or Seed()
    headword = unit.data["headword"]
    pos = unit.data["pos"]

    parts = [
        "You are a lexicographer building a learner's dictionary entry.",
        f'Word: "{headword}"   part of speech: {pos}',
        _context_block(seed),
        "",
        "Write the entry for the MOST COMMON sense of this word with this "
        "part of speech.",
        "",
        "Rules:",
        "- gloss_en: one short defining sentence, in simple English, that does "
        "NOT contain the word itself.",
        f"- examples: exactly {EXAMPLE_COUNT} natural sentences; each MUST "
        f'contain "{headword}" (an inflected form is fine).',
        f"- gloss_l1: the {l1_name} equivalent, nothing else — no explanation, "
        "no alternatives separated by slashes.",
    ]
    if rules.PROMPT_RULES:
        parts.append(rules.PROMPT_RULES)
    parts += [
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT.replace("{l1_name}", l1_name),
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(p for p in parts if p is not None)
