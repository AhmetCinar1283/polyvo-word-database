"""
LLM onbellegi — `data/cache/llm_cache.sqlite`.

ANAHTAR: `sha256(model_name + '\\x1f' + prompt)[:32]`. Build'e ozgu HICBIR
kimlik (tag, item_id, set_id, dosya yolu) anahtara girmez. Sonuc: `data/builds/`
ve `data/workspace/` defalarca silinip yeniden uretilse bile onbellek sicak
kalir; odenen her cagri bir kez odenir.

KONUM: `data/cache/` altinda, `data/stores/` altinda DEGIL. Ikisi arasindaki
fark "para" degil "yeniden uretilebilirlik": `cache/` para/GPU zamani odeyerek
yeniden uretilebilir, `stores/` icinde INSAN kararlari da bulunan ve yeniden
uretilemeyen katmandir.

YAZMA KURALI: buraya yalnizca basariyla parse edilmis, kullanilabilir cevaplar
yazilir. Parse hatasi veya API hatasiyla biten bir deneme cagiran kod tarafindan
buraya hic ulastirilmamalidir — aksi halde gecici bir hata kalici bir "cevap"
olarak onbellege yerlesir ve her yeniden kosuda bedavaya geri doner.
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
    """Onbellek anahtari. Bu fonksiyonun ciktisi bir SOZLESMEDIR: degisirse
    onbellekteki her satir erisilemez hale gelir, yani her cagri yeniden
    odenir. `tests/test_core_contracts.py` altin bir hash ile kilitler."""
    signature = f"{model_name}\x1f{prompt}"
    return hashlib.sha256(signature.encode("utf-8")).hexdigest()[:32]


def open_llm_cache_db(path: str | None = None) -> sqlite3.Connection:
    return db.connect(path or llm_cache_path(), ddl=LLM_CACHE_DDL)


def get_cached(conn: sqlite3.Connection, prompt_hash: str) -> str | None:
    row = conn.execute(
        "SELECT response FROM llm_cache WHERE prompt_hash = ?", (prompt_hash,)
    ).fetchone()
    return row[0] if row else None


def store_cached(conn: sqlite3.Connection, prompt_hash: str, model_name: str,
                 prompt: str, response: str) -> None:
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
    return conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
