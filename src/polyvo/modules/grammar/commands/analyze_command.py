"""
`polyvo grammar analyze` — `APP.sentences` seam'inden toplanan her grup icin
en cok uc kurallik grammar paketi uretir.

`--propose-only` (Kademe 1, keşif kosusu): model kural SECER ve eksik
gordugunu ADAY olarak bildirir, ama HICBIR kural satiri yazilmaz — yalnizca
`grammar_candidate` birikir. Bayrak `GrammarJob`/`GrammarStore`
NESNELERINDEN tasinir, `core/jobs/` motoruna DOKUNULMAZ.

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
from polyvo.modules.grammar.job import GrammarJob
from polyvo.modules.grammar.model import DEFAULT_MODEL, DEFAULT_PROVIDER
from polyvo.modules.grammar.store import GrammarStore


def add_analyze_args(parser: argparse.ArgumentParser) -> None:
    """Kapsam bayraklari + motorun ve saglayicinin ortak bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Evrenin ilk N grubuyla sinirla (pilot icin)")
    parser.add_argument(
        "--propose-only", action="store_true",
        help="Kademe 1 kesif kosusu: yalnizca aday biriktirir, hicbir "
             "kural satiri YAZMAZ.")
    cli_args.add_job_args(parser)
    llm_cli.add_llm_args(parser, default_provider=DEFAULT_PROVIDER,
                         default_model=DEFAULT_MODEL)


def cmd_analyze(args: argparse.Namespace) -> int:
    """Grammar analiz kosusunu calistirir; cikis kodunu doner."""
    ctx = JobContext(
        tag=paths.resolve_tag(args.tag),
        l2=args.l2 or config.default_l2(),
        limit=args.limit,
    )
    provider = llm_cli.resolve_llm_settings(
        args, default_provider=DEFAULT_PROVIDER, default_model=DEFAULT_MODEL)
    store = GrammarStore(propose_only=args.propose_only)
    try:
        result = engine_run.run(
            GrammarJob(propose_only=args.propose_only), ctx,
            provider=provider, store=store, **cli_args.run_kwargs(args))
    except LLMUnavailable as exc:
        llm_cli.fail(exc, "grammar analyze")
        return 1
    except KeyboardInterrupt:
        print("\n[grammar analyze] kullanici durdurdu — yazilanlar korundu.")
        return 130
    finally:
        store.close()
    return 0 if not result.interrupted else 1
