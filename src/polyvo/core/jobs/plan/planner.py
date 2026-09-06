"""
Plani KURAN yer: her birime verdikti uygular ve onbellegi yoklar.

ONBELLEK YOKLAMASI BIR TAHMIN DEGILDIR. Yoklama, kosunun kullanacagi
metnin BIREBIR aynisini uretir (`job.build_prompt(unit)` — `retry_note`
yok, cunku ilk deneme boyle gider) ve onu kosuyla ayni fonksiyondan
(`hash_prompt`) gecirir. Iki taraf ayni ciftten hesapladigi icin plan ile
gerceklesen ayrisamaz.

Onbellek yoklamasi YALNIZCA `process` alan birimler icin yapilir: atlanacak
bir birimin prompt'unu kurmak bosa istir (5.000 birimlik bir kosuda
olculebilir bir gecikme).
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from polyvo.core.jobs.base import Job, Unit
from polyvo.core.jobs.plan import verdict as vd
from polyvo.core.jobs.plan.report import PlanEntry, PlanReport
from polyvo.core.jobs.store.policy import Existing
from polyvo.core.llm.cache import get_cached, hash_prompt


def _is_cached(cache_conn: sqlite3.Connection | None, label: str,
               prompt: str) -> bool | None:
    """Ilk deneme prompt'u onbellekte mi? Onbellek yoksa `None` (bilinmiyor)."""
    if cache_conn is None:
        return None
    return get_cached(cache_conn, hash_prompt(label, prompt)) is not None


def make_plan(job: Job, units: Iterable[Unit], existing: dict[str, Existing],
              *, model_label: str, model_rank: int, mode: str = "none",
              cache_conn: sqlite3.Connection | None = None) -> PlanReport:
    """Birimleri gezip verdikt + onbellek durumuyla plan raporunu uretir."""
    report = PlanReport(command=job.command or f"{job.family}.{job.kind}",
                        model_label=model_label, mode=mode,
                        max_attempts=job.max_attempts)

    for unit in units:
        row = existing.get(unit.key)
        decision = vd.decide(row, mode=mode, model_rank=model_rank)
        if decision == vd.PROCESS:
            report.add(PlanEntry(
                key=unit.key, name=unit.name, verdict=decision,
                reason=vd.process_reason(row),
                cached=_is_cached(cache_conn, model_label, job.build_prompt(unit)),
            ))
        else:
            report.add(PlanEntry(key=unit.key, name=unit.name, verdict=decision))

    return report
