"""
Kaynak indirme — `data/raw/` disina hicbir sey yazmaz.

Indirme AYRI bir komuttur, build'in bir yan etkisi degil: build'in agsiz ve
tekrar edilebilir kalmasi gerekir (ayni `data/raw/` her zaman ayni
`lexicon.sqlite`'i uretmeli). Bir kaynak eksikse build onu SESSIZCE atlamaz,
raporunda "yok" olarak gosterir.

`legacy_dist` indirilmez, kopyalanir: kendi eski sevkiyatimizdir ve depoda
`content/en/` altinda durur (K4).
"""

from __future__ import annotations

import os
import shutil

from polyvo.core import paths
from polyvo.dictionary import sources

#: `legacy_dist` icin kopyalanacak dosyalar; kaynak klasor depodadir.
LEGACY_FILES = ("core.db", "en.db")


def download_one(src: sources.Source, *, force: bool = False,
                 timeout: int = 60) -> tuple[str, str]:
    """`(durum, hedef_yol)`. Durum: `indirildi` | `mevcut` | `url_yok`."""
    if not src.url or not src.filename:
        return "url_yok", ""
    dest = os.path.join(paths.raw_dir(), src.filename)
    if os.path.exists(dest) and not force:
        return "mevcut", dest

    import requests  # yalnizca indirme yolunda gerekir

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with requests.get(src.url, stream=True, timeout=timeout) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                fh.write(chunk)
    os.replace(tmp, dest)                 # yarim dosya asla hedef adi almaz
    return "indirildi", dest


def copy_legacy(*, force: bool = False) -> tuple[str, str]:
    """Eski sevkiyati `content/<l2>/`'den `data/raw/legacy_dist/`'e kopyalar."""
    from polyvo.core import config

    src_dir = os.path.join(config.project_root(), "content", config.default_l2())
    dest_dir = os.path.join(paths.raw_dir(), "legacy_dist")
    if not all(os.path.exists(os.path.join(src_dir, f)) for f in LEGACY_FILES):
        return "kaynak_yok", src_dir
    os.makedirs(dest_dir, exist_ok=True)
    copied = False
    for name in LEGACY_FILES:
        dest = os.path.join(dest_dir, name)
        if os.path.exists(dest) and not force:
            continue
        shutil.copy2(os.path.join(src_dir, name), dest)
        copied = True
    return ("kopyalandi" if copied else "mevcut"), dest_dir


def download_all(*, force: bool = False) -> list[tuple[str, str, str]]:
    """`[(kaynak_adi, durum, yol)]` — indirilebilir her kaynak + legacy."""
    out: list[tuple[str, str, str]] = []
    for src in sources.downloadable():
        status, path = download_one(src, force=force)
        out.append((src.name, status, path))
    status, path = copy_legacy(force=force)
    out.append(("legacy_dist", status, path))
    return out
