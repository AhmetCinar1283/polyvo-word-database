"""
Kosu sonu MUTABAKATI: plan ne dedi, gercekte ne oldu — plan denetlenmeden
guvenilmez. Uyari yalnizca GERCEK sapmada basilir: butce/kesinti yuzunden
az cagri yapmak sapma degildir. Cok denemeli isler icin plan bir ARALIKTIR.

`reconcile` saf (satir listesi doner), `report` basar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polyvo.core.jobs.plan.report import PlanReport
from polyvo.core.jobs.plan.verdict import SKIP_REASON_LABELS


@dataclass
class RunResult:
    """Bir kosunun olculmus sonucu — iddia degil, sayac."""

    command: str
    run_id: str
    plan: PlanReport
    approved: int = 0
    rejected: int = 0
    skipped: int = 0
    #: Odenmis ama depoya YAZILMAMIS cevaplar (yazma kapisi engelledi).
    blocked: int = 0
    new_calls: int = 0
    cached_calls: int = 0
    budget_stopped: bool = False
    #: Kosuyu kesen istisna (Ctrl-C / saglayici koptu). Ozet BASILDIKTAN sonra
    #: yukari firlatilir: yarida kalan bir kosunun ne kadar ilerledigini
    #: gormek, istisnanin kendisi kadar onemlidir.
    interruption: BaseException | None = None
    #: Kapinin engelleme sebeplerinin dokumu (`policy.WriteDecision.reason`).
    block_reasons: dict[str, int] = field(default_factory=dict)

    @property
    def processed(self) -> int:
        """Gercekten islenen (cagri alan) birim sayisi."""
        return self.approved + self.rejected

    @property
    def interrupted(self) -> bool:
        """Kosu yarida kesildi mi?"""
        return self.interruption is not None


def _drift_line(result: RunResult) -> str | None:
    """Plan araligindan sapma varsa uyari satiri, yoksa `None`."""
    if result.budget_stopped or result.interrupted:
        return None
    low, high = result.plan.paid_calls, result.plan.paid_calls_max
    if low <= result.new_calls <= high:
        return None
    aralik = f"{low:,}" if low == high else f"{low:,}–{high:,}"
    yon = "FAZLA" if result.new_calls > high else "AZ"
    return (f"[{result.command}] UYARI: gercek dis cagri plandan {yon} cikti "
            f"(plan {aralik}, gerceklesen {result.new_calls:,}).")


def reconcile(result: RunResult) -> list[str]:
    """Kosu sonu ozetini satir listesine cevirir — basmaz, yalnizca bicimler."""
    tag = f"[{result.command}]"
    oran = (f"%{100 * result.approved / result.processed:.1f}"
            if result.processed else "-")

    lines = [
        f"{tag} Bitti. Islenen {result.processed:,} birim — "
        f"onayli {result.approved:,} ({oran}), reddedilen {result.rejected:,}. "
        f"Dokunulmayan: {result.skipped:,}.",
        f"{tag}   dis cagri: {result.new_calls:,} yeni / "
        f"{result.cached_calls:,} onbellekten.",
    ]

    if result.blocked:
        lines.append(f"{tag}   {result.blocked:,} cevap depoya YAZILMADI "
                     f"(mevcut satir korundu):")
        for reason, count in sorted(result.block_reasons.items(),
                                    key=lambda kv: -kv[1]):
            lines.append(f"{tag}      {count:>6,}  {reason}")

    for verdict, count in result.plan.skipped().items():
        lines.append(f"{tag}   atlandi {count:>6,}  "
                     f"{SKIP_REASON_LABELS.get(verdict, verdict)}")

    if result.budget_stopped:
        lines.append(f"{tag} --max-new butcesi doldu; kalan birimlere "
                     f"DOKUNULMADI.")

    if result.interrupted:
        lines.append(f"{tag} Kosu YARIDA KESILDI ({result.interruption}) — "
                     f"buraya kadarki ilerleme KAYDEDILDI.")

    drift = _drift_line(result)
    if drift:
        lines.append(drift)

    lines.append(f"{tag}   kosu kimligi: {result.run_id} "
                 f"(deneme gunlugunde bu kimlikle aranir)")
    return lines


def report(result: RunResult) -> None:
    """Kosu sonu ozetini ekrana basar."""
    for line in reconcile(result):
        print(line, flush=True)
