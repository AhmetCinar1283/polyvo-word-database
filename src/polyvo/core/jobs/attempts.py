"""
Deneme gunlugu — INSERT-ONLY. Neyin nicin reddedildiginin tek kaydi.

Her LLM denemesi (onaylanan da, reddedilen de, parse edilemeyen de) buraya
bir satir birakir ve o satir BIR DAHA GUNCELLENMEZ. Sebep: depo yalnizca
KAZANAN cevabi tutar; bir promptun neden uc kez reddedildigini gosteren
tek yer burasidir. `UPDATE` olsaydi bir onarim kosusu tam da o kaniti
silerdi.

`raw_response` parse edilemeyen cevaplar icin de doldurulur — LLM onbellegi
yalnizca BASARIYLA parse edilenleri sakladigi icin (bkz. `core/llm/cache.py`)
bozuk ciktinin baska bir kaydi yok.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

#: Bir denemenin sonucu. `error` = cevap JSON'a cevrilemedi (model hatasi),
#: `rejected` = cevap geldi ama QA'dan gecmedi. Ikisini ayirmak sart:
#: birincisi saglayici/prompt sorunu, ikincisi icerik sorunudur.
STATUSES = ("approved", "rejected", "error")


def new_run_id() -> str:
    """Bir kosuyu tanimlayan zaman damgasi (`20260905-143012`)."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def record(conn: sqlite3.Connection, *, run_id: str, family: str, kind: str,
           l2: str, stable_key: str, attempt: int, status: str,
           l1: str = "", variant: str = "", model_label: str | None = None,
           prompt_version: str | None = None, from_cache: bool = False,
           reject_reason: str | None = None,
           raw_response: str | None = None) -> None:
    """Tek bir denemeyi gunluge yazar. Commit cagirana aittir."""
    conn.execute(
        """INSERT INTO job_attempts
             (run_id, family, kind, l2, l1, variant, stable_key, model_label,
              prompt_version, attempt, from_cache, status, reject_reason,
              raw_response)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, family, kind, l2, l1 or "", variant or "", stable_key,
         model_label, prompt_version, attempt, int(from_cache), status,
         reject_reason, raw_response),
    )


def reject_reasons(conn: sqlite3.Connection, run_id: str) -> dict[str, int]:
    """Bir kosudaki red sebeplerinin dokumu — QA red oraninin raporlanmasi icin."""
    rows = conn.execute(
        """SELECT COALESCE(reject_reason, '(sebep yok)') AS reason, COUNT(*) AS n
             FROM job_attempts WHERE run_id = ? AND status != 'approved'
            GROUP BY reason ORDER BY n DESC""",
        (run_id,),
    )
    return {r["reason"]: int(r["n"]) for r in rows}
