"""
Ilerleme satiri + ARALIKLI COMMIT — ikisi ayni yerde, bilerek.

Ikisi tek nesnede cunku ayni soruyu cevaplarlar: "kosu simdiye kadar
nereye geldi ve o nokta DISKE YAZILDI mi?". Ayri olsalardi ekranda
gorunen ilerleme ile diskteki gercek ilerleme sessizce ayrilabilirdi —
uzun bir kosu kesildiginde "1.200 tamam" yazip 0 satir birakmak tam olarak
budur.

`commit_every` kucuk tutulur (5): saatler suren bir kosuda Ctrl-C ile
kaybedilecek is en fazla bes birimdir.
"""

from __future__ import annotations

import time
from typing import Callable


class Progress:
    """Sayaci ilerletir, araliklarla commit eder ve tek satir ozet basar."""

    def __init__(self, command: str, total: int, *, commit_every: int = 5,
                 report_every: int = 5):
        """Ilerleme sayacini kurar, baslangic zamanini not eder."""
        self.command = command
        self.total = total
        self.commit_every = max(1, commit_every)
        self.report_every = max(1, report_every)
        self.done = 0
        self._started = time.monotonic()

    def _eta(self) -> str:
        """Kalan sure tahmini — hic birim bitmediyse bos."""
        if self.done == 0 or self.total <= 0:
            return ""
        rate = (time.monotonic() - self._started) / self.done
        remaining = max(0, self.total - self.done) * rate
        return f" ~{remaining / 60:.0f} dk"

    def tick(self, commit_fn: Callable[[], None] | None = None,
             extra: dict[str, object] | None = None) -> None:
        """Bir birim bitti: sayaci artir, gerekirse commit et ve raporla."""
        self.done += 1
        if commit_fn is not None and self.done % self.commit_every == 0:
            commit_fn()
        if self.done % self.report_every == 0 or self.done == self.total:
            detail = "  ".join(f"{k} {v}" for k, v in (extra or {}).items())
            print(f"[{self.command}] {self.done:,}/{self.total:,}"
                  f"{self._eta()}  {detail}".rstrip(), flush=True)
