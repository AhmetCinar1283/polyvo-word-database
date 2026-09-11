"""
`Job` sozlesmesinin grammar karsiligi. Motorun bekledigi UC metodu baglar,
baska is yapmaz.

`propose_only` BAYRAGI JOB'UN KENDISINDE tasinir (`core/jobs/` motoruna
DOKUNULMAZ, kapsam disi): `GrammarStore`e ayni bayrakla iletilir, komut ikisini
de kendi ornekleriyle kurar (bkz. `commands/analyze_command.py`).
"""

from __future__ import annotations

from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.grammar import prompt as prompt_mod
from polyvo.modules.grammar import qa as qa_mod
from polyvo.modules.grammar import units


class GrammarJob(Job):
    """Her cumle grubu icin en cok uc kurallik grammar paketi ureten is."""

    family = "grammar"
    kind = "sentence_grammar"
    command = "grammar analyze"
    #: Prompt metni degisince ELLE artir.
    prompt_version = "v1"

    max_attempts = 2
    #: Bir grupta en cok uc cumle, cumle basina en cok uc kural.
    max_tokens = 1600
    temperature = 0.3

    def __init__(self, propose_only: bool = False):
        """`propose_only=True` yalnizca dokumantasyon amaclidir — asil davranis
        `GrammarStore`dedir; burada YALNIZCA `commands/` okuyabilsin diye tutulur."""
        self.propose_only = propose_only

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """`APP.sentences` seam'inden toplanan HER grup icin bir birim."""
        return units.load_units(ctx.tag, ctx.l2)

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin grammar prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa/`)."""
        return qa_mod.run(parsed, unit)
