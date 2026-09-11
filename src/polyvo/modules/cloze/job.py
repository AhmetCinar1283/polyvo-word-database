"""
`Job` sozlesmesinin cloze karsiligi. Motorun bekledigi UC metodu baglar,
baska is yapmaz — govdeler `units`/`prompt`/`qa` dosyalarindadir.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.cloze import prompt as prompt_mod, qa as qa_mod, units


class ClozeJob(Job):
    """Onayli her anlam icin uc coktan secmeli bosluk sorusu ureten is."""

    family = "cloze"
    kind = "cloze_en"
    command = "cloze generate"
    #: Prompt metni degisince ELLE artir.
    #: v2 (2026-09-07): sahne kisiti ZORUNLUdan ONERIye dondu ve
    #: "celdiriciyi sahneden degil HEDEF KELIMEDEN sec" kurali eklendi
    #: (gerekcesi `prompt.py` docstring'inde, olculmus sayilarla).
    #: Surum artmasa onbellek eski prompt'un cevabini dondururdu.
    prompt_version = "v2"

    max_attempts = 2
    #: Uc cumle + on iki sik tek cevapta doner.
    max_tokens = 1400
    #: Karttan yuksek: uc soru birbirinden farkli olmali.
    temperature = 0.5

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Onayli kartla eslesen anlamlari yukler.

        Cloze DILE BAGLI DEGILDIR — ceviri ayri bir kosudur; bu yuzden
        `ctx.variant` bos kalir ve anahtar ham `stable_key`dir."""
        loaded = units.load_units(ctx.tag, ctx.l2)
        return [keys.with_variant(u, ctx.variant) for u in loaded]

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin cloze prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa/`)."""
        return qa_mod.run(parsed, unit)
