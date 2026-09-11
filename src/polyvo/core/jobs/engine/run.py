"""
Motorun giris kapisi — ince orkestratur, mantik tutmaz. Sirayla: preflight ->
load_units -> load_existing -> make_plan -> revalidate -> render -> confirm ->
execute -> report. `--dry-run` confirm'de durur, tek dis cagri yapilmaz.

YENIDEN DEGERLENDIRME PLANDAN SONRA, RENDER'DAN ONCE calisir (`--force`
verilmisse): hicbir dis cagri yapmadigi icin onaya tabi degildir, ve
sonuclandirdigi birimleri plandan dusurur — bu yuzden ekrana basilan plan
ile onay isteminde sorulan sayi GERCEKTEN odenecek olani gosterir.

Baglanti sahipligi: `run` yalnizca KENDI actigi baglantilari kapatir.
"""

from __future__ import annotations

from polyvo.core.jobs import attempts as attempt_log
from polyvo.core.jobs import schema
from polyvo.core.jobs.base import Job, JobContext
from polyvo.core.jobs.engine import loop, reconcile, revalidate
from polyvo.core.jobs.plan import confirm, planner, render
from polyvo.core.jobs.plan.report import PlanReport
from polyvo.core.jobs.store.base import ArtifactStore
from polyvo.core.llm.cache import open_llm_cache_db
from polyvo.core.llm.quality import rank_for


def _empty_result(plan: PlanReport, run_id: str, skipped: int) -> reconcile.RunResult:
    """Hicbir cagri yapilmadan biten kosunun sonucu."""
    return reconcile.RunResult(command=plan.command, run_id=run_id, plan=plan,
                               skipped=skipped)


def run(job: Job, ctx: JobContext, *, provider, store: ArtifactStore,
        redo: str = "none", force: str | None = None,
        max_new: int | None = None, pace_delay: float = 0.0,
        dry_run: bool = False, assume_yes: bool = False,
        cache_conn=None, attempts_conn=None) -> reconcile.RunResult:
    """Bir isi ucdan uca kostur ve olculmus sonucu dondur."""
    if not dry_run:
        provider.preflight()

    job.prepare(ctx)
    units = job.load_units(ctx)
    if ctx.limit is not None:
        units = units[: ctx.limit]

    owned = []
    if cache_conn is None:
        cache_conn = open_llm_cache_db()
        owned.append(cache_conn)
    if attempts_conn is None:
        attempts_conn = schema.open_attempts()
        owned.append(attempts_conn)

    run_id = attempt_log.new_run_id()
    model_rank = rank_for(provider.label)

    try:
        existing = store.load_existing(ctx)
        plan = planner.make_plan(job, units, existing, model_label=provider.label,
                                 model_rank=model_rank, mode=redo, force=force,
                                 cache_conn=cache_conn)

        if force is not None:
            # `write=not dry_run`: prova kosusu ayni hesabi yapar ama depoya
            # dokunmaz — `--dry-run --force self` "yeni QA kac satiri
            # kurtarirdi" sorusunu bedavaya ve GERI DONULEBILIR sekilde
            # cevaplar.
            revalidate.report(
                revalidate.run(job, ctx, units, plan, existing,
                               provider=provider, store=store,
                               cache_conn=cache_conn,
                               attempts_conn=attempts_conn, run_id=run_id,
                               model_rank=model_rank, write=not dry_run),
                plan.command, force)

        render.render(plan)

        if dry_run:
            print(f"[{plan.command}] --dry-run: hicbir dis cagri yapilmadi.",
                  flush=True)
            return _empty_result(plan, run_id, skipped=len(units))
        if not confirm.confirm_plan(plan, assume_yes=assume_yes):
            return _empty_result(plan, run_id, skipped=len(units))

        result = loop.execute(job, ctx, units, plan, existing, provider=provider,
                              store=store, cache_conn=cache_conn,
                              attempts_conn=attempts_conn, run_id=run_id,
                              model_rank=model_rank, max_new=max_new,
                              pace_delay=pace_delay)
        reconcile.report(result)
        if result.interruption is not None:
            raise result.interruption
        return result
    finally:
        for conn in owned:
            conn.close()
