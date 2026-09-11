"""
Cloze promptu — anlam basina TEK cagri, UC soru birden.

Neden tek cagri: model ucunu AYNI ANDA gorurse birbirinden farkli olmalarini
saglayabilir; uc ayri cagri uc kez ayni kalibi uretir (V2-IS-4 §5).

Zorluk etiketi MODELDEN GELMEZ, istekte biz veririz — hangi cevabin hangi
zorluk oldugu sabittir ve QA bunu olcer.

SAHNE KISITI BILEREK YUMUSAKTIR (`v2`, 2026-09-07). Once ZORUNLUYDU ve
OLCULDU: sahne yalnizca `stable_key` hash'inden turedigi icin kelimeyle
ilgisiz duser ("vacation" -> "food, cooking and eating out") ve model, dogru
davranarak, sahneye ait bir cumle yazip hedef kelimeyi ya zorla icine
sikistirir ya da tamamen dusurur. Basarisiz 16 birimin 9'u buydu ve UC ayri
kapiyi birden atesledi: sahnenin kelime dagarcigi hedefin CEFR'ini asiyor
(bankacilik sahnesi A1 bir anlama "salary"/"debt"/"insurance" celdiricisi
uretti), hedef kelime cumleden dusuyor, cumlede seviye ustu kelime kaliyor.
Iki zorunlu istek (bu sahne + bu seviye) ayni anda tutulamaz; tutulamayan
istek modele SOYLENMEZ (§6.7).

Model TAM CUMLE dondurur (bosluk isareti degil): hedef kelime cumlede
gecer. Boslugu gosterimde biz uretiriz (`render.py`) — boylece cevirisi de
"boslugu doldurulmus tam cumlenin" cevirisi olur (§14), ekstra alan gerekmez.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Unit
from polyvo.modules.cloze import scene
from polyvo.modules.cloze.difficulty import BANDS, OPTION_COUNT

#: Modelden beklenen JSON'un ISKELETI — QA tam bu alanlari arar.
SCHEMA_HINT = """{
  "questions": [
    {"difficulty": "<kolay|orta|zor>", "sentence": "<full English sentence>",
     "answer": "<the target word exactly as it appears in the sentence>",
     "options": ["<answer>", "<distractor>", "<distractor>", "<distractor>"]}
  ]
}"""


def _level_line(cefr: str | None) -> str:
    """Seviye satiri; seviye bilinmiyorsa BU BIR RED SEBEBI DEGILDIR, yalnizca
    daha temkinli bir yonerge verilir."""
    if cefr:
        return (f"CEFR level of this sense: {cefr}. ALL THREE questions must "
                f"stay INSIDE {cefr} — the hard one is a {cefr} question that "
                f"challenges a {cefr} learner, NOT a higher-level question.")
    return ("CEFR level of this sense is unknown — keep the vocabulary simple "
            "and everyday in all three questions.")


def _level_rules(cefr: str | None) -> list[str]:
    """Seviye kurallari — QA'nin OLCTUGU seyin prompt'taki karsiligi.

    Bunlar prompt'ta yazili olmasaydi kurali REDDI ODEYEREK ogretirdik:
    model bilmedigi bir siniri tutturamaz, biz de dogru bir soruyu celdirici
    seviyesi yuzunden cope atardik."""
    if not cefr:
        return []
    return [
        f"- Every distractor must itself be at CEFR {cefr} or BELOW. A "
        "distractor the learner has never met makes the question hard for "
        "the wrong reason — the point is the target word, not the options.",
        f"- Every other content word in the sentences must also be at CEFR "
        f"{cefr} or below.",
    ]


def build(unit: Unit, retry_note: str | None = None) -> str:
    """Bir birimin cloze prompt metnini kurar."""
    card = unit.data["card"]
    headword = unit.data["headword"]
    pos = unit.data["pos"]
    scenes = scene.scenes_for(unit.data["stable_key"])

    parts = [
        "You are an English teacher writing multiple-choice gap-fill "
        "(cloze) questions for learners.",
        f'Word: "{headword}"   part of speech: {pos}',
        f'The ONE sense you must test: {card["gloss_en"]}',
    ]
    if card.get("register"):
        parts.append(f'Register: {card["register"]}')
    parts.append(_level_line(unit.data.get("cefr")))

    if card.get("examples"):
        parts.append("")
        parts.append("Sentences that ALREADY EXIST for this sense — do NOT "
                     "reuse them, do NOT rephrase them:")
        parts.extend(f"  - {ex}" for ex in card["examples"])

    parts += [
        "",
        f"Write EXACTLY {len(BANDS)} questions testing THIS sense of "
        f'"{headword}" — not another sense of the same word.',
        "",
        "Each question is one English sentence that CONTAINS the target word "
        "exactly ONCE, plus FOUR options: the correct answer (the word as it "
        "appears in the sentence) and THREE distractors.",
        "",
        "The three questions, in this exact order:",
    ]
    for seq, band in enumerate(BANDS, start=1):
        parts.append(
            f'  {seq}. difficulty "{band.name}" — sentence of about '
            f"{band.min_words}-{band.max_words} words; distractors: "
            f"{band.distractor_hint}; suggested setting: {scenes[seq - 1]}.")

    parts += [
        "",
        "Rules:",
        f"- Use the difficulty labels exactly as given: "
        f'{", ".join(b.name for b in BANDS)} — in that order.',
        f"- EXACTLY {OPTION_COUNT} options per question; the first option is "
        "the correct answer, the other three are wrong.",
        "- The target word must appear EXACTLY ONCE in the sentence, in the "
        "correct inflected form for that sentence.",
        "- Every distractor must be the SAME part of speech as the target "
        f"word ({pos}), and must NOT be the target word or a form of it.",
        "- Every distractor must be clearly WRONG in that sentence. A "
        "distractor a learner can rule out without knowing the target word "
        "(a different part of speech, an absurd meaning) measures nothing.",
        *_level_rules(unit.data.get("cefr")),
        "- The three sentences must not start with the same words as each "
        "other.",
        "- The suggested setting is a HINT for variety, not a requirement. "
        "Use it only if this sense is genuinely at home there. If the word "
        "does not belong in that setting, IGNORE the setting and pick one "
        "where it belongs. Forcing the word into a setting it does not fit "
        "is worse than reusing a setting.",
        "- Choose the distractors for the TARGET WORD, never for the "
        "setting. Options that are merely words from the setting are wrong "
        "for the wrong reason.",
        "- Sentences must be true, natural and make sense on their own.",
        "",
        "Answer with JSON ONLY, no prose and no markdown fence:",
        SCHEMA_HINT,
    ]
    if retry_note:
        parts += ["",
                  f"Your previous answer was REJECTED because: {retry_note}",
                  "Fix exactly that problem and answer again."]
    return "\n".join(parts)
