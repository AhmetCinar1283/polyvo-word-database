"""
Her komutun paylastigi bayraklar — bir kez tanimlanir, bir kez dogrulanir.

`--start` / `--end` HER komutta AYNI seyi ifade eder: KELIME EVRENI uzerinde
bir indeks araligi. Eski repoda bu dogru degildi — bayraklar her yerde vardi
ama her komut kendi yerel birimini sayiyordu (biri kelime, biri modul, biri
item, biri paragraf), yani `--start 0 --end 2000` her komutta baska miktarda
ise ve baska bir faturaya karsilik geliyordu.

`--limit` AYRI bir seydir: cozulmus pencerenin ICINDE, komutun kendi biriminden
en fazla N tane isle. Pencereyle birlestirilmez.
"""

from __future__ import annotations

import argparse


def add_tag_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tag", "--data-title", dest="tag", default=None,
                        help="Veri basligi (yoksa polyvo.toml/ortam/tek aday)")


def add_lang_args(parser: argparse.ArgumentParser, *, l1: bool = True) -> None:
    parser.add_argument("--l2", default=None, help="Ogrenilen dil (varsayilan: konfig)")
    if l1:
        parser.add_argument("--l1", default=None, help="Ana dil (varsayilan: konfig)")


def add_window_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", type=int, default=0,
                        help="Kelime evreninde baslangic indeksi")
    parser.add_argument("--end", type=int, default=None,
                        help="Kelime evreninde DISLAYICI bitis indeksi")
    parser.add_argument("--limit", type=int, default=None,
                        help="Pencere icinde islenecek EN FAZLA birim sayisi")


def add_run_args(parser: argparse.ArgumentParser) -> None:
    """Para harcayan her komutun ortak bayraklari."""
    parser.add_argument("--redo", choices=["none", "bad", "only-bad"], default="none",
                        help="Aday kumesi: eksikler / +kotu isaretliler / sadece kotuler")
    parser.add_argument("--max-new", type=int, default=None,
                        help="En fazla N YENI cagri (onbellek isabetleri sayilmaz)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plani yazdir ve TEK cagri yapmadan cik")
    parser.add_argument("--yes", "-y", action="store_true",
                        help="Onay istemini atla")
    parser.add_argument("--pace-delay", type=float, default=0.0,
                        help="Her yeni cagridan sonra beklenecek saniye")
    parser.add_argument("--verbose", action="store_true")


def check_word_window(start: int, end: int | None) -> None:
    """Tek dogrulama noktasi. `--end <= --start` bir yazim hatasidir; sessizce
    'is yok' diye gecmek, kullaniciyi kosunun neden bos donduguyle bas basa
    birakir."""
    if start < 0:
        raise SystemExit(f"[polyvo] --start negatif olamaz: {start}")
    if end is not None and end <= start:
        raise SystemExit(
            f"[polyvo] --end ({end}) --start ({start}) degerinden buyuk olmali.")
