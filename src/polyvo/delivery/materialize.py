"""
`data/dist/<tag>/<l2>/` uretimi. Sira TARTISILMAZ:

    topla -> KAPI -> gecici dizine yaz -> yerine tasi -> ozet

Kapi ihlal bulursa `ShipGateError` firlar ve bu dosya HICBIR SEY yazmamis
olur; onceki sevkiyat da oldugu gibi durur. Yazma her zaman `.staging/`
altina yapilir, sonra tek tek `os.replace` ile yerine gecer — yarim
sevkiyat diye bir sey olamaz (§6.1).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from dataclasses import dataclass

from polyvo.core import paths
from polyvo.delivery import collect as collect_mod, gate, schema, snapshot
from polyvo.dictionary import sources

#: Sema surumu — sevkiyat bicimi degisirse Flutter tarafi bunu okur.
SCHEMA_VERSION = "2"

#: Gecici yazim dizini; basarili kosunun sonunda silinir.
STAGING = ".staging"


@dataclass
class Result:
    """Bir `run` cagrisinin sonucu."""
    directory: str
    filenames: list[str]
    meta: dict
    shipment: collect_mod.Shipment


def _attribution() -> str:
    """Metni sevk edilebilen kaynaklarin lisans/atif bilgisi (JSON metin).

    Atif VERININ YANINDA gider: sevkiyati alan taraf belgeye bakmak zorunda
    kalmasin. Liste kayit defterinden turer, elle yazilmaz."""
    return json.dumps(
        [{"name": s.name, "title": s.title, "license": s.license,
          "attribution": s.attribution}
         for s in sorted(sources.SOURCES.values(), key=lambda s: s.name)
         if s.shippable],
        ensure_ascii=False, sort_keys=True)


def _meta_rows(shipment: collect_mod.Shipment) -> list[tuple[str, str]]:
    """Her sevkiyat dosyasina yazilan `meta` satirlari (ZAMAN DAMGASI YOK)."""
    return sorted({
        "schema_version": SCHEMA_VERSION,
        "tag": shipment.tag,
        "l2": shipment.l2,
        "l1": shipment.l1 or "",
        "item_count": str(len(shipment.rows)),
        "shippable_sources": _attribution(),
    }.items())


def _new_db(path: str, ddl: str, meta: list[tuple[str, str]]) -> sqlite3.Connection:
    """Sevkiyat dosyasini sifirdan yaratir ve `meta`yi doldurur.

    WAL KULLANILMAZ: sevkiyat tek dosya olarak kopyalanir, yan dosya birakmaz."""
    conn = sqlite3.connect(path)
    conn.executescript(ddl)
    conn.executemany("INSERT INTO meta (key, value) VALUES (?,?)", meta)
    return conn


def _write_core(path: str, shipment, meta) -> None:
    """`core.db` — dilden bagimsiz kimlik + seviye."""
    conn = _new_db(path, schema.CORE_DDL, meta)
    try:
        conn.executemany(
            "INSERT INTO items (item_id, stable_key, part_of_speech, cefr,"
            " frequency_rank, sense_id, sense_ordinal) VALUES (?,?,?,?,?,?,?)",
            [(r.item_id, r.stable_key, r.pos, r.cefr, r.freq_rank,
              r.sense_id, r.sense_ordinal) for r in shipment.rows])
        conn.commit()
    finally:
        conn.close()


def _write_l2(path: str, shipment, meta) -> None:
    """`<l2>.db` — hedef dilin metni."""
    conn = _new_db(path, schema.L2_DDL, meta)
    try:
        conn.executemany(
            "INSERT INTO item_text (item_id, headword, gloss, ipa, register,"
            " usage_note, examples_json) VALUES (?,?,?,?,?,?,?)",
            [(r.item_id, r.headword, r.gloss_en, r.ipa, r.register,
              r.usage_note, r.examples_json) for r in shipment.rows])
        conn.commit()
    finally:
        conn.close()


def _write_l1(path: str, shipment, meta) -> None:
    """`i18n_<l1>.db` — ana dil karsiliklari."""
    conn = _new_db(path, schema.L1_DDL, meta)
    try:
        conn.executemany(
            "INSERT INTO item_gloss (item_id, gloss) VALUES (?,?)",
            [(r.item_id, r.gloss_l1) for r in shipment.rows])
        conn.commit()
    finally:
        conn.close()


def run(tag: str, l2: str, l1: str | None) -> Result:
    """Sevkiyati uretir. Kapi ihlalinde `ShipGateError` firlar, dosya yazilmaz."""
    shipment = collect_mod.collect(tag, l2, l1)
    gate.enforce(shipment)                      # ONCE kapi — sonra tek bayt

    directory = paths.dist_dir(tag, l2)
    staging = os.path.join(directory, STAGING)
    names = schema.filenames(l2, l1)
    meta = _meta_rows(shipment)

    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)
    try:
        _write_core(os.path.join(staging, schema.CORE_DB), shipment, meta)
        _write_l2(os.path.join(staging, schema.l2_db(l2)), shipment, meta)
        if l1:
            _write_l1(os.path.join(staging, schema.l1_db(l1)), shipment, meta)

        summary = snapshot.build(shipment, staging, names)
        snapshot.write(summary, staging)
        for name in names + [snapshot.META_FILENAME]:
            os.replace(os.path.join(staging, name), os.path.join(directory, name))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return Result(directory=directory, filenames=names, meta=summary,
                  shipment=shipment)
