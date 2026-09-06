"""
TEK bir birimin deneme dongusu: prompt -> LLM -> QA -> gunluk, en fazla N kez.

BIR BIRIM YARIM ISLENMEZ — butce kontrolu birime girmeden ONCE yapilir
(`run.py`), yoksa yarim kalan deneme "reddedilmis" sanilip rank kapisina takilir.

Reddedilen deneme de gunluge yazilir (onbellek yalnizca parse edilebileni
saklar). Red sebebi bir sonraki denemenin prompt'una `retry_note` olarak
eklenir — farkli onbellek anahtarina duser, gercekten yeni cevap gelebilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polyvo.core.jobs import attempts as attempt_log
from polyvo.core.jobs.base import Job, JobContext, Unit


@dataclass
class AttemptOutcome:
    """Bir birimin deneme dongusunun sonucu."""

    status: str = "rejected"
    reason: str | None = None
    payload: dict = field(default_factory=dict)
    #: Onbellekten GELMEYEN (yani odenen) cagri sayisi.
    new_calls: int = 0
    #: Onbellekten bedava donen cagri sayisi.
    cached_calls: int = 0


def run_attempts(job: Job, ctx: JobContext, unit: Unit, *, provider,
                 cache_conn, attempts_conn, run_id: str,
                 pace_delay: float = 0.0) -> AttemptOutcome:
    """Birimi en fazla `job.max_attempts` kez dener; ilk onayda durur."""
    outcome = AttemptOutcome(reason="hic deneme yapilmadi")
    retry_note: str | None = None

    for attempt in range(1, job.max_attempts + 1):
        prompt = job.build_prompt(unit, retry_note)
        parsed, from_cache, raw = provider.complete_json(
            prompt, cache_conn, max_tokens=job.max_tokens,
            temperature=job.temperature, pace_delay=pace_delay,
        )
        if from_cache:
            outcome.cached_calls += 1
        else:
            outcome.new_calls += 1

        qa = job.run_qa(parsed, unit)
        # `error` ve `rejected` ayri: birincisi cevap JSON'a cevrilemedi
        # (saglayici/prompt sorunu), ikincisi icerik QA'dan gecmedi.
        status = "approved" if qa.ok else ("error" if parsed is None else "rejected")

        attempt_log.record(
            attempts_conn, run_id=run_id, family=job.family, kind=job.kind,
            l2=ctx.l2, l1=ctx.l1, variant=ctx.variant, stable_key=unit.key,
            model_label=provider.label, prompt_version=job.prompt_version,
            attempt=attempt, from_cache=from_cache, status=status,
            reject_reason=qa.reason, raw_response=raw,
        )

        outcome.status, outcome.reason, outcome.payload = status, qa.reason, qa.payload
        if qa.ok:
            # `reason` onayda da dolu olabilir: garanti edilemeyen bir QA
            # kontrolu reddetmez, UYARIR (§6.7). O metin korunur.
            break
        retry_note = qa.reason

    return outcome
