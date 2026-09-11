"""
`polyvo cloze generate` — onayli her anlam icin uc coktan secmeli soru uretir.

Bu dosya IS YAPMAZ: bayraklari cozer, is/saglayici/depo uclusunu kurar ve
`core/jobs/engine/run.py`'a verir. Plan, onay, butce, deneme gunlugu ve yazma
kapisi motorun isidir — burada tekrarlanmaz.

Cloze DILE BAGLI DEGILDIR: bu komut `--l1` ALMAZ. Ceviri ayri bir kosudur:
`polyvo cloze translate --l1 <kod>`.

`--dry-run` TEK KURUS harcamaz ve TEK SATIR yazmaz.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.core.jobs import cli_args
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.llm import cli as llm_cli
from polyvo.core.llm.base import LLMUnavailable
from polyvo.modules.cloze.job import ClozeJob
from polyvo.modules.cloze.model import DEFAULT_MODEL, DEFAULT_PROVIDER
from polyvo.modules.cloze.store import ClozeStore


def add_generate_args(parser: argparse.ArgumentParser) -> None:
    """Kapsam bayraklari + motorun ve saglayicinin ortak bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Evrenin ilk N kelimesiyle sinirla (pilot icin)")
    cli_args.add_job_args(parser)
    llm_cli.add_llm_args(parser, default_provider=DEFAULT_PROVIDER,
                         default_model=DEFAULT_MODEL)


def cmd_generate(args: argparse.Namespace) -> int:
    """Cloze uretim kosusunu calistirir; cikis kodunu doner."""
    ctx = JobContext(
        tag=paths.resolve_tag(args.tag),
        l2=args.l2 or config.default_l2(),
        limit=args.limit,
    )
    provider = llm_cli.resolve_llm_settings(
        args, default_provider=DEFAULT_PROVIDER, default_model=DEFAULT_MODEL)
    store = ClozeStore()
    try:
        result = engine_run.run(ClozeJob(), ctx, provider=provider,
                                store=store, **cli_args.run_kwargs(args))
    except LLMUnavailable as exc:
        llm_cli.fail(exc, "cloze generate")
        return 1
    except KeyboardInterrupt:
        print("\n[cloze generate] kullanici durdurdu — yazilanlar korundu.")
        return 130
    finally:
        store.close()
    return 0 if not result.interrupted else 1
