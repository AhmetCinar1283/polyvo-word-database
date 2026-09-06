"""
LLM onbellegi — `data/cache/llm_cache.sqlite`.

Anahtar `sha256(model_name+prompt)`; build/tag/item_id GIRMEZ, bu yuzden
`builds/`/`workspace/` silinip yeniden uretilse de onbellek sicak kalir.
`cache/`da durur, `stores/`da DEGIL: para ile yeniden uretilebilir, insan
karari degil. Yalnizca basariyla parse edilmis cevap yazilir.
"""

import hashlib
import sqlite3

from polyvo.core import sqlite as db
from polyvo.core.paths import llm_cache_path

LLM_CACHE_DDL = """
    CREATE TABLE IF NOT EXISTS llm_cache (
        prompt_hash  TEXT PRIMARY KEY,
        model_name   TEXT NOT NULL,
        prompt       TEXT NOT NULL,
        response     TEXT NOT NULL,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
"""


def hash_prompt(model_name: str, prompt: str) -> str:
    """Onbellek anahtari — SOZLESME, degisirse tum onbellek iskalar
    (`tests/test_core_contracts.py` altin hash ile kilitler)."""
    signature = f"{model_name}\x1f{prompt}"
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:32]


def open_llm_cache_db(path: str | None = None) -> sqlite3.Connection:
    """Onbellek dosyasini acar; `llm_cache` tablosunu garanti eder."""
    return db.connect(path or llm_cache_path(), ddl=LLM_CACHE_DDL)


def get_cached(conn: sqlite3.Connection, prompt_hash: str) -> str | None:
    """Bir hash icin kayitli cevabi doner; yoksa `None`."""
    row = conn.execute(
        "SELECT response FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,)
    ).fetchone()
    return row[0] if row else None


def store_cached(conn: sqlite3.Connection, prompt_hash: str, model_name: str,
                 prompt: str, response: str) -> None:
    """Basariyla parse edilmis bir cevabi onbellege yazar (UPSERT)."""
    conn.execute(
        """
        INSERT INTO llm_cache (prompt_hash, model_name, prompt, response, created_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(prompt_hash) DO UPDATE SET
            model_name=excluded.model_name, prompt=excluded.prompt,
            response=excluded.response
        """,
        (prompt_hash, model_name, prompt, response),
    )
    conn.commit()


def count_rows(conn: sqlite3.Connection) -> int:
    """Onbellekteki toplam satir sayisi."""
    return conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
