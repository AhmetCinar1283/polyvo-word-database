"""
`Job` sozlesmesinin cloze cevirisi karsiligi. Motorun bekledigi uc metodu
baglar, baska is yapmaz.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.cloze.translate import prompt as prompt_mod, qa as qa_mod, units


class ClozeTranslationJob(Job):
    """Onaylanmis cloze cumlelerini bir L1'e ceviren is."""

    family = "cloze"
    kind = "cloze_l1"
    command = "cloze translate"
    #: Prompt metni degisince ELLE artir.
    prompt_version = "v1"

    max_attempts = 2
    max_tokens = 700
    temperature = 0.3

    def __init__(self):
        """Kosu boyunca sabit kalan L1'i tutar (`prepare` doldurur)."""
        self._l1 = ""

    def prepare(self, ctx: JobContext) -> None:
        """Kosunun L1'ini saklar — `build_prompt`/`run_qa` ctx almaz."""
        self._l1 = ctx.l1

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Onayli cloze paketi olan anlamlari yukler, varyant anahtarini uygular.

        `ctx.variant` bu kosuda HER ZAMAN `ctx.l1`dir."""
        loaded = units.load_units(ctx.tag, ctx.l2)
        return [keys.with_variant(u, ctx.variant) for u in loaded]

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin ceviri prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, self._l1, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa.py`)."""
        return qa_mod.run(parsed, unit, self._l1)
