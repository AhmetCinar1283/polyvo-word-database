"""
Motoru kullanan HER komutun paylastigi CLI bayraklari — tek yerde.

Bayraklar burada oldugu icin `--redo bad` her komutta ayni seyi yapar ve
yardim metni her komutta ayni sozu verir. Eski repoda `--dry-run` uc ayri
komutta uc ayri anlamda tanimlanmisti; birinde "raporla ve cik", digerinde
"yaz ama commit'leme" demekti.

`run_kwargs` bir Namespace'i dogrudan `engine.run(**kwargs)` cagrisina
cevirir: bayrak adi ile motor parametresi arasindaki esleme de TEK yerde
kalsin diye.
"""

from __future__ import annotations

import argparse

from polyvo.core.jobs.plan.verdict import FORCE_MODES, REDO_MODES


def add_job_args(parser: argparse.ArgumentParser) -> None:
    """`--redo`, `--force`, `--dry-run`, `--yes`, `--max-new`, `--pace-delay` ekler."""
    parser.add_argument(
        "--redo", choices=list(REDO_MODES), default="none",
        help="Mevcut satirlar icin: 'none' = kullanilabilir olani atla "
             "(varsayilan); 'bad' = eksikleri doldur VE kotu isaretli satirlari "
             "yeniden uret; 'only-bad' = yalnizca onarim, eksik satir uretme. "
             "Kotu OLMAYAN satira hicbir modda LLM cagrisi yapilmaz.")
    parser.add_argument(
        "--force", choices=list(FORCE_MODES), default=None,
        help="Kotu satirlar icin RANK KAPISINI gevset — normalde ayni/zayif "
             "modelle reddedilmis satir bir DAHA denenmez (para bosa gitmesin "
             "diye), bu QA kurallari sonradan gevsetilse bile boyledir. "
             "'self' = yalnizca AYNI seviyedeki modelle reddedilmis satirlari "
             "yeniden dene ('elimdeki en iyisi bu, yine de dene'); "
             "'all' = daha ONCE DAHA IYI bir model tarafindan reddedilmis "
             "satirlari da dahil HER kotu satiri dene. Zorlanan birim IKI "
             "asamadan gecer: (1) onay ISTEMINDEN ONCE onbellekteki eski "
             "cevap BUGUNKU QA'dan gecirilir ve gecenler cagri yapilmadan "
             "duzeltilir — 'H' desen bile bu kalicidir (--dry-run'da yalnizca "
             "raporlanir, yazilmaz); (2) hala reddedilenler onaylarsan "
             "MODELE gider ve onbellek ATLANIR, yani ayni model olsa bile "
             "taze cevap alinir ve o cagri ODENIR. Rank kapisi HER --redo "
             "modunda gecerlidir (kotu satir bir mod secimi degil bir "
             "BOSLUKTUR), --force de ayni sekilde tum modlarda calisir. "
             "ONAYLI satira ve insan kararina hicbir --force satirin uzerine "
             "yazdirmaz — bu bayrak yalnizca 'denenir mi' sorusunu genisletir.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Tek bir dis cagri YAPMADAN ne olacagini raporla ve cik.")
    parser.add_argument(
        "--yes", action="store_true", dest="assume_yes",
        help="Onay istemini atla (odenecek cagri sayisi sorulmadan devam et).")
    parser.add_argument(
        "--max-new", type=int, default=None, metavar="N",
        help="En fazla N YENI dis cagri yap, sonra dur. Onbellekten donen "
             "cevaplar bu tavani harcamaz.")
    parser.add_argument(
        "--pace-delay", type=float, default=0.0, metavar="SN",
        help="Her dis cagridan sonra beklenecek sure (hiz limiti icin).")


def run_kwargs(args: argparse.Namespace) -> dict:
    """Ayristirilmis bayraklari `engine.run` parametrelerine cevirir."""
    return {
        "redo": getattr(args, "redo", "none"),
        "force": getattr(args, "force", None),
        "dry_run": getattr(args, "dry_run", False),
        "assume_yes": getattr(args, "assume_yes", False),
        "max_new": getattr(args, "max_new", None),
        "pace_delay": getattr(args, "pace_delay", 0.0),
    }
