"""
`polyvo lexicon-card translate` — onayli kartin karsiligini ve tanim+not+ornek
cevirisini tek cagrida bir dile uretir.

Bu dosya IS YAPMAZ: bayraklari cozer, motora ucluyu (is/saglayici/depo)
verir. `JobContext.variant = l1`: bu kosu ayri bir anahtar ailesinde yasar,
kartin kendi anahtarini EZMEZ.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.core.jobs import cli_args
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.llm import cli as llm_cli
from polyvo.core.llm.base import LLMUnavailable
from polyvo.modules.lexicon_card.commands.cards_command import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
)
from polyvo.modules.lexicon_card.translate.job import LexiconL1EntryJob
from polyvo.modules.lexicon_card.translate.store import LexiconL1EntryStore


def add_translate_args(parser: argparse.ArgumentParser) -> None:
    """Kapsam bayraklari + motorun ve saglayicinin ortak bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--l1", default=None,
                        help="Cevrilecek ana dil (varsayilan: polyvo.toml project.l1)")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Evrenin ilk N kelimesiyle sinirla (pilot icin)")
    cli_args.add_job_args(parser)
    llm_cli.add_llm_args(parser, default_provider=DEFAULT_PROVIDER,
                         default_model=DEFAULT_MODEL)


def cmd_translate(args: argparse.Namespace) -> int:
    """Ana dil paketi kosusunu calistirir; cikis kodunu doner."""
    l1 = args.l1 or config.default_l1()
    ctx = JobContext(
        tag=paths.resolve_tag(args.tag),
        l2=args.l2 or config.default_l2(),
        l1=l1,
        variant=l1,
        limit=args.limit,
    )
    provider = llm_cli.resolve_llm_settings(
        args, default_provider=DEFAULT_PROVIDER, default_model=DEFAULT_MODEL)
    store = LexiconL1EntryStore()
    try:
        result = engine_run.run(LexiconL1EntryJob(), ctx, provider=provider,
                                store=store, **cli_args.run_kwargs(args))
    except LLMUnavailable as exc:
        llm_cli.fail(exc, "lexicon-card translate")
        return 1
    except KeyboardInterrupt:
        print("\n[lexicon-card translate] kullanici durdurdu — yazilanlar korundu.")
        return 130
    finally:
        store.close()
    return 0 if not result.interrupted else 1
