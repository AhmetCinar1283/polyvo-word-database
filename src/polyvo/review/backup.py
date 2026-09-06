"""
`data/human/corrections.jsonl` — insan emeginin TASINABILIR yedegi.

Neden var: `stores/` kutsaldir ama dokunulmaz degildir; kimlik uzayi yeniden
kurulabilir, depo bozulabilir. Yedek, ice aktarilan HER duzeltmeyi ekleme
kipinde saklar; `review restore` onu ayni kapidan geri oynatir.

Yedek `tier`/`source` TASIMAZ — o alanlar sabittir ve yalnizca `apply.py`
tarafindan konur. Yedekten okunan bir tier, kapiyi kandirmanin en kolay
yolu olurdu.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from polyvo.core import paths
from polyvo.review import record

BACKUP_FILENAME = "corrections.jsonl"


def backup_path() -> str:
    """`data/human/corrections.jsonl` tam yolu."""
    return os.path.join(paths.human_dir(), BACKUP_FILENAME)


def append(corrections: list[record.Correction], *, l1: str | None) -> str:
    """Duzeltmeleri yedege EKLER (uzerine yazmaz) ve dosya yolunu doner."""
    path = backup_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    saved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        for correction in corrections:
            extra = {"saved_at": saved_at}
            # Satirin KENDI dili varsa o yazilir — karisik dilli bir yedek
            # geri oynatildiginda gloss'lar yanlis dile dusmesin.
            row_l1 = correction.l1 or l1
            if row_l1:
                extra["l1"] = row_l1
            handle.write(correction.to_json(**extra) + "\n")
    return path


def read() -> tuple[list[record.Correction], list[str]]:
    """Yedegi bastan sona okur; dosya yoksa bos doner."""
    path = backup_path()
    if not os.path.exists(path):
        return [], []
    return record.parse_file(path)
