"""
`Job` sozlesmesinin lexicon_card karsiligi — motorun modulden bekledigi UC
metodu baglar, baska is yapmaz. Her metodun govdesi kendi dosyasindadir
(`units`, `seed`, `prompt`, `qa`), boylece prompt'u degistirmek bu dosyaya
dokunmaz.
"""

from __future__ import annotations

from polyvo.core.jobs import keys
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.dictionary.build import stages as dict_stages
from polyvo.modules.lexicon_card import prompt as prompt_mod, qa as qa_mod, seed, units


class LexiconCardJob(Job):
    """EN sozluk karti + ornek ureten is. Ana dil karsiligi bu isin degil,
    `gloss` isinin sorumlulugudur — kart dile bagli degildir."""

    family = "lexicon"
    kind = "card"
    command = "lexicon-card cards"
    #: Prompt metni degisince ELLE artir — deneme gunlugu hangi metinden
    #: uretildigini boyle soyler. v2: `gloss_l1` alani prompt'tan cikti.
    #: v3: `usage_note` alani prompt'tan cikti (Is 3, kendi kosusu var).
    prompt_version = "v3"

    max_attempts = 2
    max_tokens = 900
    temperature = 0.3

    def load_units(self, ctx: JobContext) -> list[Unit]:
        """Evreni birimlere cevirir, tohumu ekler ve varyant anahtarini uygular.

        Bu komut bugun `ctx.variant`i hic doldurmaz, dolayisiyla
        `keys.with_variant` no-op kalir (Unit degismeden doner)."""
        loaded = units.load_units(ctx.tag, ctx.l2)
        seeds = seed.load_seeds(dict_stages.lexicon_db_path(ctx.tag),
                                [u.data["headword"] for u in loaded])
        seed.attach(loaded, seeds)
        return [keys.with_variant(u, ctx.variant) for u in loaded]

    def build_prompt(self, unit: Unit, retry_note: str | None = None) -> str:
        """Birimin prompt metni (`prompt.py`)."""
        return prompt_mod.build(unit, retry_note)

    def run_qa(self, parsed: dict | None, unit: Unit) -> QaResult:
        """Cevabin icerik kapisi (`qa.py`)."""
        return qa_mod.run(parsed, unit)
