"""
Plan raporunun EKRAN BICIMI — tek yerde tanimli, test edilebilir.

`format_plan` saf bir fonksiyondur: `PlanReport` alir, satir listesi doner,
hicbir sey basmaz. Bicimin testi bu yuzden ekrani yakalamadan yazilabilir
(Adim 2 kabul kosulu: "PlanReport.render cikti bicimi tanimli").

TAM LISTE BASILMAZ: her sebep icin en fazla `SAMPLE_LIMIT` ornek ad
gosterilir. 5.000 birimlik bir kosuda tam dokum terminali doldurur ve
tam da okunmasi gereken ozet satirini ekrandan kaydirirdi.
"""

from __future__ import annotations

from polyvo.core.jobs.plan.report import PlanReport
from polyvo.core.jobs.plan.verdict import (
    PROCESS_REASON_LABELS,
    SKIP_REASON_LABELS,
)

SAMPLE_LIMIT = 5


def _samples_suffix(names: list[str]) -> str:
    """Ornek adlari parantez icinde kisa bir eke cevirir."""
    return f"  ({', '.join(names)}…)" if names else ""


def format_plan(report: PlanReport) -> list[str]:
    """Plan raporunu satir listesine cevirir — basmaz, yalnizca bicimler."""
    tag = f"[{report.command}]"
    force_suffix = f", --force {report.force}" if report.force else ""
    lines = [
        f"{tag} PLAN — model {report.model_label}, --redo {report.mode}"
        f"{force_suffix}, {report.examined:,} birim incelendi",
    ]

    for reason, count in sorted(report.process_reasons().items()):
        label = PROCESS_REASON_LABELS.get(reason, reason)
        lines.append(f"{tag}   islenecek {count:>6,}  {label}")

    for verdict, count in report.skipped().items():
        label = SKIP_REASON_LABELS.get(verdict, verdict)
        samples = report.samples(verdict, SAMPLE_LIMIT)
        lines.append(f"{tag}   atlanan   {count:>6,}  {label}"
                     f"{_samples_suffix(samples)}")

    lines.append(f"{tag}   toplam islenecek: {report.process_total:,}")
    lines.append(f"{tag}      onbellekten (bedava): {report.cached_calls:,}")
    if report.max_attempts > 1:
        lines.append(f"{tag}      ODENECEK DIS CAGRI : {report.paid_calls:,}"
                     f"–{report.paid_calls_max:,} "
                     f"(birim basina en fazla {report.max_attempts} deneme)")
    else:
        lines.append(f"{tag}      ODENECEK DIS CAGRI : {report.paid_calls:,}")
    return lines


def render(report: PlanReport) -> None:
    """Plan raporunu ekrana basar."""
    for line in format_plan(report):
        print(line, flush=True)
