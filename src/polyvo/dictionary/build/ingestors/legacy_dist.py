"""
Polyvo v6 sevkiyati — KANIT KOPRUSU (K4). Evren URETMEZ, `candidates`
uretmez; hicbir sey dogrudan ogrenciye gitmez (`shippable=False`).

`pos` kaniti K7 POS cozumlemesinde kullanilir (POS bir OLGUDUR); geri kalani
yalnizca LLM'e baglam. `core.db`+`en.db`'yi okur, `data/raw/legacy_dist/`
altina ELLE yerlestirilir.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Iterable

from polyvo.dictionary.build.ingestors.base import Evidence, FileIngestor

@dataclass
class LegacyDistIngestor(FileIngestor):
    """K4: eski sevkiyattan (`core.db`+`en.db`) kanit okuyan ingestor."""
    source_name: str = "legacy_dist"

    def _dbs(self) -> tuple[str, str]:
        """`(core.db, en.db)` tam yollari."""
        base = self.raw_path()
        return os.path.join(base, "core.db"), os.path.join(base, "en.db")

    def available(self) -> bool:
        """Iki dosya da yerinde mi?"""
        return all(os.path.exists(p) for p in self._dbs())

    def evidence(self) -> Iterable[Evidence]:
        """`item_text`+`items`'i JOIN'leyip pos/tanim/ipa/ornek/esanlamli/zitanlamli kaniti uretir."""
        if not self.available():
            return
        core_db, en_db = self._dbs()
        con = sqlite3.connect(f"file:{en_db}?mode=ro", uri=True)
        try:
            con.execute("ATTACH DATABASE ? AS core", (f"file:{core_db}?mode=ro",))
            rows = con.execute("""
                SELECT t.headword, i.part_of_speech, t.gloss, t.ipa,
                       t.examples_json, t.synonyms_json, t.antonyms_json
                  FROM item_text t
                  JOIN core.items i ON i.item_id = t.item_id
            """)
            for head, pos, gloss, ipa, ex_j, syn_j, ant_j in rows:
                if not head:
                    continue
                if pos:
                    yield Evidence(head, kind="pos", payload=pos, raw_pos=pos)
                if gloss:
                    yield Evidence(head, kind="definition", payload=gloss, raw_pos=pos)
                if ipa:
                    yield Evidence(head, kind="ipa", payload=ipa, raw_pos=pos)
                for raw, kind in ((ex_j, "example"), (syn_j, "synonym"),
                                  (ant_j, "antonym")):
                    for payload in _json_list(raw):
                        yield Evidence(head, kind=kind, payload=payload, raw_pos=pos)
        finally:
            con.close()


def _json_list(raw: str | None) -> list[str]:
    """`item_text` icindeki JSON dizi sutununu duz metin listesine cevirir."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


INGESTOR = LegacyDistIngestor()
