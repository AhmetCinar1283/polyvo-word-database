"""
Plan raporunun VERISI — sayaclar, sebepler, ornek oge adlari. Yalnizca SAYAR;
bicimlendirme `render.py`, onay `confirm.py` isidir.

ODENECEK CAGRI SAYISI BIR ARALIKTIR: `paid_calls` ilk deneme (alt sinir),
`paid_calls_max` her birim `max_attempts` kez denenirse (ust sinir) —
tek sayi, cok denemeli islerde HER ZAMAN yanlis bir "plandan sapti" uyarisi
uretirdi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from polyvo.core.jobs.plan.verdict import PROCESS


@dataclass(frozen=True)
class PlanEntry:
    """Plandaki tek bir birim: hangi verdikt, hangi sebep, onbellekte mi."""

    key: str
    name: str
    verdict: str
    reason: str | None = None
    #: Yalnizca `process` birimleri icin anlamli; digerlerinde `None`.
    cached: bool | None = None


@dataclass
class PlanReport:
    """Bir kosunun oge-oge dokumu, LLM'e gitmeden hesaplanmis."""

    command: str
    model_label: str
    mode: str
    max_attempts: int = 1
    entries: list[PlanEntry] = field(default_factory=list)

    def add(self, entry: PlanEntry) -> None:
        """Plana bir birim ekler."""
        self.entries.append(entry)

    @property
    def examined(self) -> int:
        """Plana giren toplam birim sayisi."""
        return len(self.entries)

    @property
    def process_total(self) -> int:
        """Islenecek (cagri alacak) birim sayisi."""
        return sum(1 for e in self.entries if e.verdict == PROCESS)

    @property
    def cached_calls(self) -> int:
        """Ilk denemesi onbellekten BEDAVA donecek birim sayisi."""
        return sum(1 for e in self.entries if e.verdict == PROCESS and e.cached)

    @property
    def paid_calls(self) -> int:
        """Odenecek dis cagrilarin ALT siniri (her birim tek deneme)."""
        return self.process_total - self.cached_calls

    @property
    def paid_calls_max(self) -> int:
        """Odenecek dis cagrilarin UST siniri (her birim `max_attempts` kez).

        Onbellekten donen ilk deneme reddedilirse sonraki denemenin prompt'u
        farklidir (`retry_note` eklenir) ve onbellekte olmayabilir — bu yuzden
        ust sinir onbellekli birimleri de kapsar."""
        return self.process_total * self.max_attempts - self.cached_calls

    def verdict_counts(self) -> dict[str, int]:
        """Verdikt -> birim sayisi."""
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.verdict] = counts.get(entry.verdict, 0) + 1
        return counts

    def skipped(self) -> dict[str, int]:
        """Yalnizca atlanan verdiktlerin dokumu."""
        return {k: v for k, v in sorted(self.verdict_counts().items())
                if k != PROCESS}

    def process_reasons(self) -> dict[str, int]:
        """`process` birimlerinin sebep dokumu — para NICIN harcaniyor."""
        counts: dict[str, int] = {}
        for entry in self.entries:
            if entry.verdict == PROCESS and entry.reason:
                counts[entry.reason] = counts.get(entry.reason, 0) + 1
        return counts

    def samples(self, verdict: str, limit: int = 5) -> list[str]:
        """Bir verdikte ait ilk `limit` oge adi — tam liste basilmaz."""
        out = []
        for entry in self.entries:
            if entry.verdict == verdict:
                out.append(entry.name)
                if len(out) >= limit:
                    break
        return out

    def verdict_map(self) -> dict[str, str]:
        """`stable_key -> verdikt`. Kosu dongusu kararini plandan OKUR, yeniden
        hesaplamaz — iki yerde iki kopya karar olsaydi ayrisirlardi."""
        return {e.key: e.verdict for e in self.entries}
