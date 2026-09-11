"""
Plan raporunun VERISI — sayaclar, sebepler, ornek oge adlari. Yalnizca SAYAR;
bicimlendirme `render.py`, onay `confirm.py` isidir.

ODENECEK CAGRI SAYISI BIR ARALIKTIR: `paid_calls` ilk deneme (alt sinir),
`paid_calls_max` her birim `max_attempts` kez denenirse (ust sinir) —
tek sayi, cok denemeli islerde HER ZAMAN yanlis bir "plandan sapti" uyarisi
uretirdi.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from polyvo.core.jobs.plan.verdict import PROCESS, REASON_FORCED


@dataclass(frozen=True)
class PlanEntry:
    """Plandaki tek bir birim: hangi verdikt, hangi sebep, onbellekte mi."""

    key: str
    name: str
    verdict: str
    reason: str | None = None
    #: Yalnizca `process` birimleri icin anlamli; digerlerinde `None`.
    #: Onbellekte cevap VAR MI sorusunun cevabi — "bedava mi" sorusununki
    #: DEGIL: zorlanan birimde onbellek okumasi atlanir (bkz. `forced`).
    cached: bool | None = None

    @property
    def forced(self) -> bool:
        """Bu birim rank kapisini `--force` sayesinde mi gecti."""
        return self.verdict == PROCESS and self.reason == REASON_FORCED


@dataclass
class PlanReport:
    """Bir kosunun oge-oge dokumu, LLM'e gitmeden hesaplanmis."""

    command: str
    model_label: str
    mode: str
    #: `None` = rank kapisi normal; `"self"`/`"all"` = `--force` (bkz. `verdict.py`).
    force: str | None = None
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
        """Ilk denemesi onbellekten BEDAVA donecek birim sayisi.

        ZORLANAN birim buraya GIRMEZ: onbellekte cevabi olsa bile okumasi
        atlanacaktir (`--force` = modelden taze cevap), yani o cagri
        odenecektir. Onbellekteki cevabi zaten onay ONCESI yeniden
        degerlendirme tuketir (`engine/revalidate.py`)."""
        return sum(1 for e in self.entries
                   if e.verdict == PROCESS and e.cached and not e.forced)

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

    def forced_entries(self) -> list[PlanEntry]:
        """`--force` ile islenecek birimler — zorlamanin iki asamasi (onay
        oncesi yeniden degerlendirme, sonrasinda onbellek atlama) bu listeyi
        paylasir."""
        return [e for e in self.entries if e.forced]

    def settle(self, key: str, verdict: str) -> None:
        """Bir birimi cagri YAPMADAN sonuclandirir (yeniden degerlendirme).

        Plan bir tahmin degil kosunun TEK karar kaynagidir (`verdict_map`);
        birim burada degistirilmezse dongu ona bir daha LLM cagrisi yapardi."""
        for i, entry in enumerate(self.entries):
            if entry.key == key:
                self.entries[i] = replace(entry, verdict=verdict, reason=None,
                                          cached=None)
                return

    def verdict_map(self) -> dict[str, str]:
        """`stable_key -> verdikt`. Kosu dongusu kararini plandan OKUR, yeniden
        hesaplamaz — iki yerde iki kopya karar olsaydi ayrisirlardi."""
        return {e.key: e.verdict for e in self.entries}
