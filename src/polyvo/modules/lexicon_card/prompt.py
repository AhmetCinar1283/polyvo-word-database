"""
Prompt metni — modelden ISTENEN sey burada, TEK yerde tanimlidir.

Kart DILE BAGLI DEGILDIR: yalnizca Ingilizce uretilir, ana dil karsiligi
ayri bir kosunun isidir (`translate/prompt.py`).

`usage_note` BURADA ISTENMEZ (Is 3): olcum 957 kartin 4'unde doluydu, sebep
"isteqe bagli" diye gecip kural yazilmamasiydi. Not artik kendi kosusunun
isi (`note/prompt.py`) — kosullu, sayilabilir bir sebebe baglanir.

Bilincli kural: sozluk tohumu prompt'a "dogru cevap" olarak degil BAGLAM
olarak girer — model kopyalamak zorunda degildir.

`retry_note` bir onceki denemenin RED SEBEBIDIR: metni degistirdigi icin
onbellek anahtari da degisir, yani yeniden deneme gercekten yeni cevap alir.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.lexicon_card.seed import Seed

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{
  "gloss_en": "<short English definition, one sentence, no example>",
  "register": "<one of: neutral | formal | informal | slang | technical>",
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


def build(unit: Unit, retry_note: str | None = None) -> str:
    """Bir birimin prompt metnini kurar."""
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
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(p for p in parts if p is not None)
