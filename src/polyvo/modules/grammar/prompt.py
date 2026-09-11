"""
Grammar promptu — grup basina TEK cagri, GRUPTAKI HER cumle icin ayri kural
listesi (Is 6 karar 6). Katalog modele KISALTILMIS verilir: yalnizca id +
`name_en` (aciklama degil) — model tutamayacagi bir sey ISTENMEZ (§6.7 dersi,
cloze'un sahne kisiti tuzagi). CEFR bandina gore SUZULMUS liste, cumlelerin
en yuksek CEFR'inin `assume_known_from` bandini asan kurallari zaten disarida
birakir — modelin gormeyecegi bir kurali secmesini beklemenin anlami yok.

Model KAPALI SOZLUKTEN secer: listede olmayan bir id UYDURAMAZ. Gercekten
kayda deger ama listede olmayan bir yapi gorurse `candidates`a yazar —
sevk edilmez, insan katalogda karsiligini acar (§9).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.grammar import levels
from polyvo.modules.grammar import model as model_const
from polyvo.modules.grammar.catalog import all_rules
from polyvo.modules.grammar.cefr_band import ceiling_for

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{
  "sentences": [
    {"seq": 1,
     "rules": [
       {"rank": 1, "rule_id": "<EN.AREA.RULE from the allowed list>",
        "trigger": "<exact contiguous text copied from THIS sentence>",
        "note": "<1-2 sentences: how this rule shows up in THIS sentence>"}
     ],
     "candidates": [
       {"proposed_name": "<short name>",
        "trigger": "<exact contiguous text from THIS sentence>",
        "rationale": "<why this deserves its own catalog entry>"}
     ]}
  ]
}"""


def _catalog_lines(ceiling: str | None) -> list[str]:
    """`id — name_en` satirlari, CEFR tavaniyla SUZULMUS (bilinmiyorsa tum
    katalog gosterilir — bilinmeyen seviye bir filtre gerekcesi degildir)."""
    lines = []
    for rule in all_rules():
        if ceiling and levels.exceeds(rule.level, ceiling):
            continue
        lines.append(f"  - {rule.id} — {rule.name_en}")
    return lines


def build(unit: Unit, retry_note: str | None = None) -> str:
    """Bir grubun (birden fazla cumlenin) grammar prompt metnini kurar."""
    sentences = unit.data["sentences"]
    ceiling = ceiling_for(sentences)
    catalog_lines = _catalog_lines(ceiling)

    parts = [
        "You are an English teacher identifying the most NOTICEABLE grammar "
        "patterns in each sentence below — ordered from the sentence's "
        "CARRYING structure (rank 1) to fine detail, not word choice.",
        "",
        "Do NOT report a rule that is present in EVERY ordinary English "
        "sentence (subject-verb agreement, articles, plural -s, personal "
        "pronouns) unless it is genuinely the most salient thing about that "
        "specific sentence — those rules carry no information about THIS "
        "sentence.",
        "",
        f"For EACH sentence, pick {model_const.MIN_RULES_PER_SENTENCE}-"
        f"{model_const.MAX_RULES_PER_SENTENCE} rules, ranked 1..N (1 = most "
        "salient), ONLY from this closed list of rule ids:",
        *catalog_lines,
        "",
        "Sentences to analyze:",
    ]
    for s in sentences:
        parts.append(f'  {s["seq"]}. "{s["text"]}"')

    parts += [
        "",
        "Rules:",
        "- Choose rule ids ONLY from the list above — never invent one.",
        "- `trigger` must be copied EXACTLY, character for character, from "
        "the sentence it belongs to — a short contiguous phrase (e.g. "
        '"is able to", not the whole sentence).',
        "- `note` describes how the rule shows up in THIS sentence (1-2 "
        "sentences), never the general rule definition.",
        "- If a sentence contains a genuinely noticeable pattern that has "
        "NO match in the list, do NOT force the closest id — report it "
        "instead as a `candidates` entry for that sentence and leave it "
        "out of `rules`.",
        "- Ranks per sentence must be 1..N with no gaps and no repeats.",
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(parts)
