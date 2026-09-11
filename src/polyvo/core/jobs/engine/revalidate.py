"""
ONAY ONCESI, BEDAVA yeniden degerlendirme — `--force`un ilk asamasi.

NEDEN VAR: bir prompt/QA hatasi duzeltildiginde eskiden reddedilmis satirlar
depoda kotu isaretli kalirdi. Onbellekte o satirlarin HAM CEVABI zaten duruyor
(`core/llm/cache.py`); reddedilmelerinin sebebi cevap degil o gunku QA'ydi.
Bu modul, zorlanan her birimin onbellekteki cevabini BUGUNKU QA'dan gecirir:
gecenler cagri yapilmadan onaylanir, gecmeyenler modele gitmek uzere planda
kalir.

IKI SEY BILEREK BOYLE:

1. ONAY ISTEMINDEN ONCE CALISIR VE YAZAR. Kullanici "kac cagri odenecek"
   sorusuna "H" dese bile bu duzelme KALICIDIR — hicbir dis cagri yapilmadigi
   icin onaylanacak bir maliyet yoktur, ve tam da bu yuzden ayri bir komut
   degildir: "QA'yi duzelttim, yeniden kos" akisinin bir kosuya sigmasi
   gerekiyordu.
2. `--dry-run` ICINDE YAZMAZ. O bayrak "raporla ve cik" sozu verir; sozun
   "dis cagri yapmaz" kismi kadar "depoyu degistirmez" kismi da gecerlidir.
   Prova modunda ayni hesap yapilir, yalnizca sonuc yazilmaz — kullanici yeni
   QA'nin kac satiri kurtaracagini bir kurus odemeden ve hicbir sey
   degistirmeden gorur.

Zincir `engine/attempt.py` ile AYNI sirayi izler (`retry_note` dahil):
onbellek bir denemede biterse orada durulur, kalani paralı asamaya birakilir.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.core.jobs import attempts as attempt_log
from polyvo.core.jobs.base import Job, JobContext, QaResult, Unit
from polyvo.core.jobs.plan.report import PlanReport
from polyvo.core.jobs.plan.verdict import SKIP_REVALIDATED
from polyvo.core.jobs.store.base import ArtifactStore, WriteRequest
from polyvo.core.jobs.store.policy import Existing, TIER_MODEL


@dataclass
class RevalidateResult:
    """Yeniden degerlendirmenin olculmus sonucu — iddia degil, sayac."""

    #: Zorlanan birimlerden onbellekte cevabi BULUNAN sayisi.
    examined: int = 0
    #: Bugunku QA'dan gecen birim sayisi.
    approved: int = 0
    #: Gecip DEPOYA DA yazilan birim sayisi (yazma kapisi ayrica karar verir).
    written: int = 0
    #: Onbellekteki cevabi bugunku QA'nin da reddettigi birim sayisi.
    still_rejected: int = 0
    #: Zorlanan ama onbellekte cevabi olmayan birim sayisi (dogrudan modele).
    uncached: int = 0
    #: `--dry-run`: hesap yapildi, hicbir sey yazilmadi.
    dry: bool = False

    @property
    def touched(self) -> bool:
        """Raporlanmaya deger bir sey oldu mu?"""
        return self.examined > 0 or self.uncached > 0


@dataclass
class _Step:
    """Zincirdeki tek bir denemenin yeniden degerlendirilmesi."""

    attempt: int
    status: str
    qa: QaResult
    raw: str


def _replay(job: Job, unit: Unit, *, provider, cache_conn) -> list[_Step]:
    """Onbellekteki deneme zincirini BUGUNKU QA'dan gecirir; dis cagri yok.

    `attempt.py::run_attempts` ile ayni prompt sirasini kurar — ayrisirsa
    yeniden degerlendirme kosunun gercekte gorecegi cevabi degil BASKA bir
    cevabi degerlendirmis olurdu."""
    steps: list[_Step] = []
    retry_note: str | None = None

    for attempt in range(1, job.max_attempts + 1):
        result = provider.peek_cached(job.build_prompt(unit, retry_note),
                                      cache_conn)
        if result is None:
            break                       # zincir onbellekte bitti
        qa = job.run_qa(result.parsed, unit)
        status = ("approved" if qa.ok
                  else ("error" if result.parsed is None else "rejected"))
        steps.append(_Step(attempt, status, qa, result.raw))
        if qa.ok:
            break
        retry_note = qa.reason

    return steps


def run(job: Job, ctx: JobContext, units: list[Unit], plan: PlanReport,
        existing: dict[str, Existing], *, provider, store: ArtifactStore,
        cache_conn, attempts_conn, run_id: str, model_rank: int,
        write: bool = True) -> RevalidateResult:
    """Zorlanan birimleri onbellekten yeniden degerlendirir; plani gunceller."""
    result = RevalidateResult(dry=not write)
    forced = {e.key for e in plan.forced_entries()}
    if not forced:
        return result

    by_key = {u.key: u for u in units}

    for key in (u.key for u in units if u.key in forced):
        steps = _replay(job, by_key[key], provider=provider,
                        cache_conn=cache_conn)
        if not steps:
            result.uncached += 1
            continue

        result.examined += 1
        last = steps[-1]

        if write:
            for step in steps:
                attempt_log.record(
                    attempts_conn, run_id=run_id, family=job.family,
                    kind=job.kind, l2=ctx.l2, l1=ctx.l1, variant=ctx.variant,
                    stable_key=by_key[key].data.get("stable_key", key),
                    model_label=provider.label,
                    prompt_version=job.prompt_version, attempt=step.attempt,
                    from_cache=True, status=step.status,
                    reject_reason=step.qa.reason, raw_response=step.raw,
                )

        if not last.qa.ok:
            # Bugunku QA da reddetti: birim planda KALIR, paralı asamada
            # modelden taze cevap alacak.
            result.still_rejected += 1
            continue

        result.approved += 1
        if write:
            decision = store.save(ctx, WriteRequest(
                unit=by_key[key], payload=last.qa.payload, status="approved",
                tier=TIER_MODEL, rank=model_rank, model_label=provider.label,
                prompt_version=job.prompt_version, reject_reason=last.qa.reason,
            ), existing.get(key))
            if decision.write:
                result.written += 1
        # Cevap onaylandi: prova olsun ya da olmasin bu birime artik cagri
        # yapilmaz — `--dry-run` cikacak maliyeti OLDUGU gibi gostermeli.
        plan.settle(key, SKIP_REVALIDATED)

    if write:
        store.commit()
        attempts_conn.commit()
    return result


def format_result(result: RevalidateResult, command: str, force: str) -> list[str]:
    """Sonucu satir listesine cevirir — basmaz, yalnizca bicimler."""
    tag = f"[{command}]"
    suffix = " (--dry-run: PROVA, hicbir sey yazilmadi)" if result.dry else ""
    lines = [
        f"{tag} --force {force}: onbellekteki {result.examined:,} eski cevap "
        f"BUGUNKU QA'dan gecirildi — dis cagri yapilmadi.{suffix}",
        f"{tag}   yeni QA'dan GECTI : {result.approved:,}"
        + (f" (depoya yazilan {result.written:,})"
           if result.written != result.approved else ""),
        f"{tag}   yeni QA da reddetti: {result.still_rejected:,}",
    ]

    paid = result.still_rejected + result.uncached
    if paid:
        lines += [
            f"{tag} UYARI: kalan {paid:,} zorlanan birim icin onbellek "
            f"ATLANACAK — onaylarsan",
            f"{tag}        her biri GERCEK bir dis cagridir (ayni model olsa "
            f"bile taze cevap alinir).",
        ]
    return lines


def report(result: RevalidateResult, command: str, force: str) -> None:
    """Sonucu ekrana basar (raporlanacak bir sey yoksa susar)."""
    if not result.touched:
        return
    for line in format_result(result, command, force):
        print(line, flush=True)
