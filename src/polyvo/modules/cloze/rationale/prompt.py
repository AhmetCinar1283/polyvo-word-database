"""
Cloze ipucu + aciklama promptu — anlam basina TEK cagri, uc ipucu + on iki
aciklama birlikte (V2-IS-5 §5).

Model uc soruyu birlikte gorunce birbirini tekrar etmeyen aciklama
yazabilir; ayri cagrilar ayni kalibi uc kez uretir. Dogru cevabin
aciklamasi celdiricininkine gonderme yapabilir ("`remove` esya icin
kullanilir, para icin `withdraw`") — bu ancak ikisi AYNI istekteyse
mumkundur.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.cloze.rationale.shape import HINT_BAND, REASON_BAND

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{
  "questions": [
    {"hint": "<short hint, one per question, IN ORDER>",
     "reasons": [
       {"option": "<option text EXACTLY as given>",
        "reason": "<why this option is right/wrong IN THIS SENTENCE>"}
     ]}
  ]
}"""


def build(unit: Unit, retry_note: str | None = None) -> str:
    """Bir birimin ipucu/aciklama prompt metnini kurar."""
    card = unit.data["card"]
    headword = unit.data["headword"]
    questions = sorted(unit.data["questions"], key=lambda q: q["seq"])
    option_count = len(questions[0]["options"])

    parts = [
        "You are an English teacher writing a HINT and per-option "
        "EXPLANATIONS for a multiple-choice gap-fill (cloze) question you "
        "already wrote.",
        f'Word: "{headword}"   sense: {card["gloss_en"]}',
        "",
        f"There are {len(questions)} questions below, already FIXED — do "
        "NOT change the sentence, the answer or the options.",
    ]
    for q in questions:
        parts.append(f'  Question {q["seq"]}: {q["sentence"]}')
        parts.append(f'    Options: {", ".join(q["options"])}   '
                     f'(correct: {q["answer"]})')

    parts += [
        "",
        f"For EACH question write ONE hint ({HINT_BAND.min_words}-"
        f"{HINT_BAND.max_words} words) that points the learner toward the "
        "meaning area, a typical collocation, or a grammar clue in the "
        "sentence — WITHOUT giving away the answer.",
        "Hint rules:",
        f'- NEVER mention "{headword}" or any inflected form of it.',
        "- NEVER quote the text of any option, correct or not.",
        "- NEVER refer to an option by its position (\"the first option\", "
        "\"option B\", \"the third choice\") — the learner may see the "
        "options in a different order, or not see them at all.",
        "",
        f"For EACH question, write ONE explanation per option (all "
        f"{option_count}, including the correct one), "
        f"{REASON_BAND.min_words}-{REASON_BAND.max_words} words each:",
        "- For the CORRECT option: explain why it fits THIS sentence.",
        "- For each WRONG option: explain what that word means and why it "
        "does NOT fit this sentence. You may contrast it with the correct "
        "word (e.g. \"`remove` is for objects, `withdraw` is for money\").",
        "- Every explanation MUST include the option's own word somewhere "
        "in the text.",
        "- Set \"option\" to the option text EXACTLY as given above.",
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(parts)
