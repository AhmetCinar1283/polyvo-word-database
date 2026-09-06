"""
Kosu dongusu: onaylanmis plani birim birim uygular.

KESINTI-GUVENLI COMMIT: saglayici koparsa (`LLMUnavailable`) ya da Ctrl-C
gelirse istisna yukari firlamadan once her sey commit edilir — istisna
yutulmaz, yalnizca GECIKTIRILIR (once ozet basilsin diye).

KARAR PLANDAN OKUNUR (`plan.verdict_map()`), yeniden hesaplanmaz — ikinci
bir karar noktasi plan ile kosuyu sessizce ayristirirdi.
"""

from __future__ import annotations

from polyvo.core.jobs.base import Job, JobContext, Unit
from polyvo.core.jobs.engine.attempt import run_attempts
from polyvo.core.jobs.engine.budget import Budget
from polyvo.core.jobs.engine.progress import Progress
from polyvo.core.jobs.engine.reconcile import RunResult
from polyvo.core.jobs.plan.report import PlanReport
from polyvo.core.jobs.plan.verdict import PROCESS
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing, TIER_MODEL
from polyvo.core.llm.base import LLMUnavailable


def execute(job: Job, ctx: JobContext, units: list[Unit], plan: PlanReport,
            existing: dict[str, Existing], *, provider, store: ArtifactStore,
            cache_conn, attempts_conn, run_id: str, model_rank: int,
            max_new: int | None = None, pace_delay: float = 0.0) -> RunResult:
    """Plani uygular; sonucu olculmus sayaclarla doner. Kesinti yukari firlar."""
    result = RunResult(command=plan.command, run_id=run_id, plan=plan)
    verdicts = plan.verdict_map()
    budget = Budget(max_new)
    progress = Progress(plan.command, plan.process_total)
    interrupted: BaseException | None = None

    try:
        for unit in units:
            if verdicts.get(unit.key) != PROCESS:
                result.skipped += 1
                continue
            if budget.exhausted:
                # Butce doldu: KALAN birimlere hic dokunulmaz, yarim is birakilmaz.
                result.budget_stopped = True
                break

            outcome = run_attempts(job, ctx, unit, provider=provider,
                                   cache_conn=cache_conn,
                                   attempts_conn=attempts_conn, run_id=run_id,
                                   pace_delay=pace_delay)
            for _ in range(outcome.new_calls):
                budget.charge(False)
            result.new_calls += outcome.new_calls
            result.cached_calls += outcome.cached_calls

            decision = store.save(ctx, WriteRequest(
                unit=unit, payload=outcome.payload, status=outcome.status,
                tier=TIER_MODEL, rank=model_rank, model_label=provider.label,
                prompt_version=job.prompt_version,
                reject_reason=outcome.reason,
            ), existing.get(unit.key))
            if not decision.write:
                result.blocked += 1
                result.block_reasons[decision.reason] = \
                    result.block_reasons.get(decision.reason, 0) + 1

            if outcome.status == "approved":
                result.approved += 1
            else:
                result.rejected += 1

            attempts_conn.commit()
            progress.tick(store.commit, extra={
                "onayli": f"{result.approved:,}",
                "red": f"{result.rejected:,}",
                "yeni cagri": f"{result.new_calls:,}/{plan.paid_calls:,}",
            })
    except (LLMUnavailable, KeyboardInterrupt) as exc:
        interrupted = exc

    store.commit()
    attempts_conn.commit()
    # Istisna YUTULMAZ, sonuca iliştirilir: `run.py` once ozeti basar, sonra
    # yukari firlatir. Ozet basilmadan firlatmak, kosunun nereye kadar
    # geldigini gormeden hata gormek demekti.
    result.interruption = interrupted
    return result
