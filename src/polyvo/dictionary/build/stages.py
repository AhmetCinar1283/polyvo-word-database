"""
Asama kayit defteri — asama adlari TEK yerde yasar.

`core/paths.build_dir(tag, stage)` bilerek hicbir asama adi bilmez; adlar
onlari ureten katmanda durur. Eski repoda `"01_build"` dizesi sekiz dosyada
geciyordu ve bir asama yeniden adlandirildiginda uc tanesi geride kalmisti.

Her asama yaninda bir `_stage_meta.json` birakir: o dizindeki verinin NE
oldugunu, hangi kaynaklardan ve HANGI LISANSLA geldigini soyler. Bu dosya
Adim 6'daki sevk kapisinin girdisidir (`shippable`), bir log degil.
"""

from __future__ import annotations

import datetime as _dt
import json
import os

from polyvo.core import paths, sqlite as sq

#: Sozluk katmaninin urettigi tek asama.
LEXICON = "01_lexicon"

#: Asamanin ana veritabani dosyasi.
LEXICON_DB = "lexicon.sqlite"

META_FILENAME = "_stage_meta.json"


def lexicon_dir(tag: str) -> str:
    """`data/builds/<tag>/01_lexicon/` dizini."""
    return paths.build_dir(tag, LEXICON)


def lexicon_db_path(tag: str) -> str:
    """`lexicon.sqlite` tam yolu."""
    return os.path.join(lexicon_dir(tag), LEXICON_DB)


def meta_path(tag: str, stage: str) -> str:
    """Bir asamanin `_stage_meta.json` tam yolu."""
    return os.path.join(paths.build_dir(tag, stage), META_FILENAME)


def write_stage_meta(tag: str, stage: str, payload: dict) -> str:
    """`_stage_meta.json` yazar ve yolunu doner."""
    directory = paths.build_dir(tag, stage)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, META_FILENAME)
    body = {
        "stage": stage,
        "tag": tag,
        "written_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        **payload,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(body, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def read_stage_meta(tag: str, stage: str) -> dict | None:
    """Yazilmis `_stage_meta.json`'u okur; yoksa `None` doner."""
    path = meta_path(tag, stage)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def lexicon_row_counts(tag: str) -> dict[str, int] | None:
    """`lexicon.sqlite`'taki her tablonun satir sayisi."""
    return sq.row_counts(lexicon_db_path(tag))
