"""
`Job` sozlesmesinin kullanim notu karsiligi. Motorun bekledigi uc metodu
baglar, baska is yapmaz — govdeler `units`/`prompt`/`qa` dosyalarinda.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.lexicon_card.note import prompt as prompt_mod, qa as qa_mod, units


class LexiconNoteJob(Job):
    """Onayli EN kartin ustune KOSULLU kullanim notu ureten is."""

    family = "lexicon"
    kind = "usage_note"
    command = "lexicon-card note"
    #: Prompt metni degisince ELLE artir.
    prompt_version = "v1"

    max_attempts = 2
    max_tokens = 150
    temperature = 0.3

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Onayli kartla eslesen anlamlari yukler. Not dile bagli DEGILDIR,
        varyant uygulanmaz — anahtar ham `stable_key` kalir."""
        return units.load_units(ctx.tag, ctx.l2)

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin kullanim notu prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa.py`)."""
        return qa_mod.run(parsed, unit)
