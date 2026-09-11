"""
`Job` sozlesmesinin ana dil paketi karsiligi. Motorun bekledigi uc metodu
baglar, baska is yapmaz — govdeler `units`/`prompt`/`qa` dosyalarinda.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.modules.lexicon_card.translate import prompt as prompt_mod, qa as qa_mod, units


class LexiconL1EntryJob(Job):
    """Onayli EN kartin karsiligini VE tanim+not+ornek cevirisini tek
    cagrida bir L1'e ureten is."""

    family = "lexicon"
    kind = "l1_entry"
    command = "lexicon-card translate"
    #: Prompt metni degisince ELLE artir.
    prompt_version = "v1"

    max_attempts = 2
    #: Eski iki isin toplami (karsilik 200 + ceviri 500).
    max_tokens = 700
    temperature = 0.3

    def __init__(self):
        """Kosu boyunca sabit kalan L1'i tutar (`prepare` doldurur)."""
        self._l1 = ""

    def prepare(self, ctx: JobContext) -> None:
        """Kosunun L1'ini saklar — `build_prompt`/`run_qa` ctx almaz."""
        self._l1 = ctx.l1

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Onayli kartla eslesen anlamlari yukler, varyant anahtarini uygular.

        `ctx.variant` bu kosuda HER ZAMAN `ctx.l1`dir — anahtar bu yuzden
        `stable_key::<l1>` bicimine gecer, kartin ham anahtariyla CAKISMAZ."""
        loaded = units.load_units(ctx.tag, ctx.l2, ctx.l1)
        return [keys.with_variant(u, ctx.variant) for u in loaded]

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin tek paket prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, self._l1, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Paketin icerik kapisi (`qa/`)."""
        return qa_mod.run(parsed, unit, self._l1)
