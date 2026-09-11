"""
Ana dil paketi promptu — anlam basina dil basina TEK cagri: karsilik
(`gloss_l1` + istege bagli `gloss_note`) ve ceviri (tanim + not + ornekler)
AYNI istekte uretilir. Gerekce: model karsiligi ve cumleleri birlikte gorunce
terimi tutarli kullanir (karsilik "kiyi" derken ornekte "yaka" olmaz).

Depoda o dilde bir karsilik zaten varsa (`card['fixed_gloss']`) model onu
SABIT TERIM olarak kullanir ve `gloss_l1`e aynen yazar.

Ceviri DOGALDIR, birebir DEGILDIR. Kulturel aciklama KELIMEYE aittir
(`gloss_note`), cumleye degil.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.core.lang import get_rules

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{{
  "gloss_l1": "<the single best {l1_name} equivalent for THIS sense>",
  "gloss_note": "<OPTIONAL: a short note ONLY if there is no clean {l1_name} equivalent, else empty string>",
  "definition": "<the {l1_name} translation of the definition, one sentence>",
  "usage_note": "<the {l1_name} translation of the usage note, or empty string>",
  "examples": ["<{l1_name} translation of example 1>", "<{l1_name} translation of example 2>"]
}}"""


def _context(unit: Unit) -> list[str]:
    """Kartin baglam satirlari: kelime, tanim, register, not, ornekler."""
    card = unit.data["card"]
    parts = [
        f'Word: "{unit.data["headword"]}"   part of speech: {unit.data["pos"]}',
        f'Definition (English): {card["gloss_en"]}',
    ]
    if card.get("register"):
        parts.append(f'Register: {card["register"]}')
    if card.get("usage_note"):
        parts.append(f'Usage note (English): {card["usage_note"]}')
    parts.append("Example sentences (English):")
    parts.extend(f"  - {ex}" for ex in card["examples"])
    return parts


def _gloss_rules(unit: Unit, l1_name: str) -> list[str]:
    """Karsilik alanlarinin kurallari; sabit terim varsa onu dayatir."""
    fixed = unit.data["card"].get("fixed_gloss")
    if fixed:
        return [
            f'- gloss_l1: use EXACTLY this {l1_name} equivalent for the word: '
            f'"{fixed}" — copy it unchanged into gloss_l1.',
            "- gloss_note: leave EMPTY.",
        ]
    return [
        f"- gloss_l1: the {l1_name} equivalent for EXACTLY this sense — not a "
        "different sense of the same English word. Nothing else — no "
        "explanation, no alternatives separated by slashes.",
        f"- gloss_note: leave EMPTY unless there is truly no clean "
        f"{l1_name} equivalent (e.g. the word is borrowed as-is, or the "
        "concept has no direct match) — most words do NOT need this.",
    ]


def build(unit: Unit, l1: str, retry_note: str | None = None) -> str:
    """Bir birimin tek paket prompt metnini kurar."""
    rules = get_rules(l1)
    l1_name = rules.LANGUAGE_NAME or l1
    card = unit.data["card"]
    examples = card["examples"]

    parts = [
        "You are a bilingual lexicographer writing the full "
        f"{l1_name} entry for one English dictionary sense.",
        *_context(unit),
        "",
        f"Give the {l1_name} equivalent of the word AND translate the WHOLE "
        "entry as ONE coherent unit — use the gloss_l1 term for the word "
        "throughout the definition and every example, so a learner sees one "
        "consistent translation.",
        "Rules:",
        *_gloss_rules(unit, l1_name),
        "- Translate naturally — this is NOT a literal, word-for-word "
        "translation. Produce what a native speaker would actually say.",
        f"- definition: one sentence, the {l1_name} equivalent of the "
        "English definition.",
        f"- examples: EXACTLY {len(examples)} sentences, in the SAME order "
        "as given, each the natural translation of the corresponding "
        "English example.",
    ]
    if card.get("usage_note"):
        parts.append("- usage_note: translate it — do NOT leave it empty.")
    else:
        parts.append("- usage_note: leave EMPTY (no English note was given).")
    if rules.PROMPT_RULES:
        parts.append(rules.PROMPT_RULES)
    parts += [
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT.format(l1_name=l1_name),
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(p for p in parts if p is not None)
