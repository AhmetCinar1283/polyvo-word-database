"""
`Job` sozlesmesinin lexicon_card karsiligi — motorun modulden bekledigi UC
metodu baglar, baska is yapmaz. Her metodun govdesi kendi dosyasindadir
(`units`, `seed`, `prompt`, `qa`), boylece prompt'u degistirmek bu dosyaya
dokunmaz.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.dictionary.build import stages as dict_stages
from polyvo.modules.lexicon_card import prompt as prompt_mod, qa as qa_mod, seed, units


class LexiconCardJob(Job):
    """EN sozluk karti + L1 gloss + ornek ureten is."""

    family = "lexicon"
    kind = "card"
    command = "lexicon-card cards"
    #: Prompt metni degisince ELLE artir — deneme gunlugu hangi metinden
    #: uretildigini boyle soyler.
    prompt_version = "v1"

    max_attempts = 2
    max_tokens = 900
    temperature = 0.3

    def __init__(self):
        """Kosu boyunca sabit kalan L1'i tutar (`prepare` doldurur)."""
        self._l1 = ""

    def prepare(self, ctx: JobContext) -> None:
        """Kosunun L1'ini saklar — `build_prompt`/`run_qa` ctx almaz."""
        self._l1 = ctx.l1

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Evreni birimlere cevirir ve her birime sozluk tohumunu ekler."""
        loaded = units.load_units(ctx.tag, ctx.l2)
        seeds = seed.load_seeds(dict_stages.lexicon_db_path(ctx.tag),
                                [u.data["headword"] for u in loaded])
        seed.attach(loaded, seeds)
        return loaded

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, self._l1, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa.py`)."""
        return qa_mod.run(parsed, unit, self._l1)
