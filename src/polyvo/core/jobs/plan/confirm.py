"""
Onay istemi — para harcanmadan once insana sorulan tek soru.

UC KURAL:

1. ODENECEK CAGRI YOKSA SORULMAZ. Her sey onbellekten donuyorsa onay istemek
   kullaniciyi "evet" demeye alistirir; alistigi anda onay bir kapi olmaktan
   cikar.
2. TTY YOKSA SORULMAZ AMA SESSIZ DE KALINMAZ. Otomatik bir kosuda girdi
   beklemek surer; bu yuzden gecilir ve GECILDIGI YAZILIR.
3. VARSAYILAN HAYIR. Bos Enter onay degildir — yanlis basilan bir tusun
   bedeli burada gercek paradir.
"""

from __future__ import annotations

import sys

from polyvo.core.jobs.plan.report import PlanReport


def confirm_plan(report: PlanReport, *, assume_yes: bool = False) -> bool:
    """Kosuya devam edilsin mi? Odenecek cagri yoksa sormadan `True`."""
    tag = f"[{report.command}]"

    if report.process_total == 0:
        print(f"{tag} Islenecek birim yok — cagri yapilmayacak.", flush=True)
        return False

    if report.paid_calls == 0:
        print(f"{tag} Odenecek dis cagri yok (hepsi onbellekten) — onay sorulmuyor.",
              flush=True)
        return True

    if assume_yes:
        print(f"{tag} --yes verildi: {report.paid_calls:,} odenecek cagri onaylandi.",
              flush=True)
        return True

    if not sys.stdin.isatty():
        print(f"{tag} Terminal yok (TTY degil): onay ISTEMI ATLANDI, "
              f"{report.paid_calls:,} odenecek cagri ile devam ediliyor.", flush=True)
        return True

    answer = input(f"{tag} {report.paid_calls:,} dis cagri odenecek. "
                   f"Devam edilsin mi? [e/H] ").strip().lower()
    if answer in ("e", "evet", "y", "yes"):
        return True
    print(f"{tag} Iptal edildi — hicbir cagri yapilmadi.", flush=True)
    return False
