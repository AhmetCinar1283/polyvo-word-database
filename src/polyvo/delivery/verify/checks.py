"""
Sevkiyat kontrolleri. Her kontrol bir `CheckResult` doner; tek bir basarisiz
kontrol bile komutu exit 1 yapar (§6.1 — yesil olmayan kapi kapi degildir).

Kontrol edilen sey UCTAN UCA hattir: evren -> odenmis depo -> dist. Bir
asamada satir kaybolduysa burada gorunur.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass

from polyvo.core import paths, sqlite as sq
from polyvo.curriculum import schema as curriculum_schema
from polyvo.delivery import materialize, schema, snapshot
from polyvo.modules.lexicon_card import schema as lexicon_schema


@dataclass
class CheckResult:
    """Tek bir kontrolun sonucu."""
    name: str
    ok: bool
    detail: str = ""

    def __str__(self) -> str:
        """Rapor satiri."""
        mark = "OK " if self.ok else "HATA"
        return f"  [{mark}] {self.name}" + (f" — {self.detail}" if self.detail else "")


def _ids(path: str, sql: str) -> set[int]:
    """Sevkiyat dosyasindan bir id kumesi okur."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {r[0] for r in conn.execute(sql)}
    finally:
        conn.close()


def _meta_value(path: str, key: str) -> str | None:
    """Sevkiyat dosyasinin `meta` tablosundan bir deger okur."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def run_checks(tag: str, l2: str, l1: str | None) -> list[CheckResult]:
    """Hattin tamamini kontrol eder; bos olmayan bir liste doner."""
    out: list[CheckResult] = []
    directory = paths.dist_dir(tag, l2)
    names = schema.filenames(l2, l1)

    out.extend(_upstream_checks(tag, l2))
    out.extend(_file_checks(directory, names))
    if not all(c.ok for c in out):
        # Dosyalar saglam degilse icerik kontrolleri anlamsizdir — sessizce
        # "gecti" demektense burada durulur (§6.8).
        return out
    out.extend(_content_checks(directory, names, l2, l1))
    return out


def _upstream_checks(tag: str, l2: str) -> list[CheckResult]:
    """Sevkiyatin girdileri (evren + odenmis depo) yerinde mi."""
    universe = curriculum_schema.universe_db_path(tag, l2)
    lexicon = lexicon_schema.lexicon_db_path()
    results = [
        CheckResult("evren izdusumu var", os.path.exists(universe), universe),
        CheckResult("odenmis depo var", os.path.exists(lexicon), lexicon),
    ]
    if all(r.ok for r in results):
        counts = sq.row_counts(lexicon) or {}
        results.append(CheckResult(
            "depoda onaylanmis kart var", counts.get("sense_cards", 0) > 0,
            f"sense_cards={counts.get('sense_cards', 0)}"))
    return results


def _file_checks(directory: str, names: list[str]) -> list[CheckResult]:
    """Dosyalar var mi, SQLite mi, ozetteki sha256 ile ayni mi."""
    results = []
    for name in names:
        path = os.path.join(directory, name)
        results.append(CheckResult(f"{name} SQLite dosyasi",
                                   os.path.exists(path) and sq.is_sqlite(path), path))

    meta = snapshot.read(directory)
    results.append(CheckResult("_dist_meta.json okunabiliyor", meta is not None,
                               snapshot.meta_path(directory)))
    if meta is None or not all(r.ok for r in results):
        return results

    for name in names:
        expected = (meta.get("files", {}).get(name) or {}).get("sha256")
        actual = snapshot.file_digest(os.path.join(directory, name))
        results.append(CheckResult(
            f"{name} ozetle ayni (sha256)", expected == actual,
            "" if expected == actual else f"beklenen {expected}, bulunan {actual}"))
    return results


def _content_checks(directory: str, names: list[str], l2: str,
                    l1: str | None) -> list[CheckResult]:
    """Tablolar, referans butunlugu ve atif yerinde mi."""
    core = os.path.join(directory, schema.CORE_DB)
    text = os.path.join(directory, schema.l2_db(l2))
    results = []

    core_ids = _ids(core, "SELECT item_id FROM items")
    text_ids = _ids(text, "SELECT item_id FROM item_text")
    results.append(CheckResult("core.db bos degil", bool(core_ids),
                               f"{len(core_ids)} oge"))
    results.append(CheckResult(f"{schema.l2_db(l2)} her ogeye metin tasiyor",
                               core_ids == text_ids,
                               f"core {len(core_ids)}, metin {len(text_ids)}"))
    results.append(CheckResult(
        f"{schema.l2_db(l2)} bos gloss icermiyor",
        not _ids(text, "SELECT item_id FROM item_text WHERE TRIM(gloss) = ''")))

    if l1:
        i18n = os.path.join(directory, schema.l1_db(l1))
        l1_ids = _ids(i18n, "SELECT item_id FROM item_gloss")
        results.append(CheckResult(f"{schema.l1_db(l1)} core ile ortusuyor",
                                   l1_ids == core_ids,
                                   f"core {len(core_ids)}, {l1} {len(l1_ids)}"))

    version = _meta_value(core, "schema_version")
    results.append(CheckResult("meta.schema_version guncel",
                               version == materialize.SCHEMA_VERSION,
                               f"dosyada {version}, beklenen {materialize.SCHEMA_VERSION}"))
    attribution = _meta_value(core, "shippable_sources")
    results.append(CheckResult("lisans atifi verinin yaninda",
                               _is_nonempty_json_list(attribution)))
    return results


def _is_nonempty_json_list(value: str | None) -> bool:
    """Atif alani gecerli ve dolu bir JSON dizisi mi."""
    if not value:
        return False
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list) and bool(parsed)
