"""
`Job` sozlesmesinin cloze ipucu/aciklama karsiligi. Motorun bekledigi UC
metodu baglar, baska is yapmaz.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.cloze.rationale import prompt as prompt_mod
from polyvo.modules.cloze.rationale import qa as qa_mod
from polyvo.modules.cloze.rationale import units


class ClozeRationaleJob(Job):
    """Onayli her cloze paketi icin ipucu + sik aciklamasi ureten is."""

    family = "cloze"
    kind = "cloze_rationale"
    command = "cloze rationale"
    #: Prompt metni degisince ELLE artir.
    prompt_version = "v1"

    max_attempts = 2
    #: Uc ipucu + on iki aciklama tek cevapta doner.
    max_tokens = 1400
    temperature = 0.4

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Onayli cloze paketi olan anlamlari yukler.

        Rationale DILE BAGLI DEGILDIR — ceviri ayri bir kosudur; bu yuzden
        `ctx.variant` bos kalir ve anahtar ham `stable_key`dir."""
        loaded = units.load_units(ctx.tag, ctx.l2)
        return [keys.with_variant(u, ctx.variant) for u in loaded]

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin ipucu/aciklama prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa/`)."""
        return qa_mod.run(parsed, unit)
