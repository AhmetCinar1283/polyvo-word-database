"""
`polyvo lexicon-card cards` — kart uretim kosusunu baslatir.

Bu dosya IS YAPMAZ: bayraklari cozer, is/saglayici/depo uclusunu kurar,
`core/jobs/engine/run.py`'a verir. Plan, onay, butce, deneme gunlugu ve
yazma kapisi motorun isidir — burada tekrarlanmaz.

`--dry-run` TEK KURUS harcamaz; onay istemi `--yes` verilmedikce cikar.
"""

from __future__ import annotations

import argparse

from polyvo.core import config, paths
from polyvo.core.jobs import cli_args
from polyvo.core.jobs.base import JobContext
from polyvo.core.jobs.engine import run as engine_run
from polyvo.core.llm import cli as llm_cli
from polyvo.core.llm.base import LLMUnavailable
from polyvo.modules.lexicon_card.job import LexiconCardJob
from polyvo.modules.lexicon_card.store import LexiconCardStore

#: Pilot BILEREK tek modele sabitlenmistir; bayrakla degistirilebilir ama
#: varsayilan degismez — iki farkli modelle yarim dolmus bir depo, reddetme
#: oranini olculemez hale getirirdi.
DEFAULT_PROVIDER = "cloudflare"
DEFAULT_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"


def add_cards_args(parser: argparse.ArgumentParser) -> None:
    """Kapsam bayraklari + motorun ve saglayicinin ortak bayraklari."""
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")
    parser.add_argument("--l2", default=None,
                        help="Hedef dil (varsayilan: polyvo.toml project.l2)")
    parser.add_argument("--l1", default=None,
                        help="Ana dil, gloss bu dilde uretilir (varsayilan: polyvo.toml project.l1)")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Evrenin ilk N kelimesiyle sinirla (pilot icin)")
    cli_args.add_job_args(parser)
    llm_cli.add_llm_args(parser, default_provider=DEFAULT_PROVIDER,
                         default_model=DEFAULT_MODEL)


def cmd_cards(args: argparse.Namespace) -> int:
    """Kart uretim kosusunu calistirir; cikis kodunu doner."""
    ctx = JobContext(
        tag=paths.resolve_tag(args.tag),
        l2=args.l2 or config.default_l2(),
        l1=args.l1 or config.default_l1(),
        limit=args.limit,
    )
    provider = llm_cli.resolve_llm_settings(
        args, default_provider=DEFAULT_PROVIDER, default_model=DEFAULT_MODEL)
    store = LexiconCardStore()
    try:
        result = engine_run.run(LexiconCardJob(), ctx, provider=provider,
                                store=store, **cli_args.run_kwargs(args))
    except LLMUnavailable as exc:
        # Ozet zaten basildi (motor kesintiyi ondan SONRA firlatir).
        llm_cli.fail(exc, "lexicon-card")
        return 1
    except KeyboardInterrupt:
        print("\n[lexicon-card] kullanici durdurdu — yazilanlar korundu.")
        return 130
    finally:
        store.close()
    return 0 if not result.interrupted else 1
