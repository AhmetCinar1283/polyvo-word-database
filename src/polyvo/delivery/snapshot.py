"""
`_dist_meta.json` — bir sevkiyatin kimlik karti: hangi tag/dil, hangi satir
sayilari, her dosyanin sha256'si.

Neden ayri dosya: sevkiyat `.db`'lerinin kendisi ZAMAN DAMGASI TASIMAZ ki
ayni girdi iki kez ayni baytlari uretsin (Adim 3'teki determinizm olcusuyle
ayni gerekce). Uretim zamani yalnizca buraya yazilir.

`verify/` bu dosyayi OLCU olarak kullanir: dist'te duran baytlar, sevk
edildikleri andaki baytlar mi?
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os

META_FILENAME = "_dist_meta.json"


def meta_path(directory: str) -> str:
    """Bir sevkiyat dizinindeki `_dist_meta.json` tam yolu."""
    return os.path.join(directory, META_FILENAME)


def file_digest(path: str) -> str:
    """Dosyanin sha256'si (buyuk dosyada da bellege sigsin diye parcali)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build(shipment, directory: str, filenames: list[str]) -> dict:
    """Sevkiyat ozetini uretir (dosyalar `directory` icinde durmali)."""
    return {
        "tag": shipment.tag,
        "l2": shipment.l2,
        "l1": shipment.l1,
        "written_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "shipped_items": len(shipment.rows),
        "skipped_missing": shipment.skipped_missing,
        "skipped_not_approved": shipment.skipped_not_approved,
        "files": {
            name: {
                "bytes": os.path.getsize(os.path.join(directory, name)),
                "sha256": file_digest(os.path.join(directory, name)),
            }
            for name in filenames
        },
    }


def write(payload: dict, directory: str) -> str:
    """Ozeti dizine yazar ve yolunu doner."""
    path = meta_path(directory)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def read(directory: str) -> dict | None:
    """Varsa onceki ozeti okur; yoksa `None`."""
    path = meta_path(directory)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
