"""
Katman 0'in sozlesmeleri: onbellek anahtari, yol semasi, tag cozumlemesi,
sqlite kapisi, model siralamasi.

Buradaki her testin karsiligi eski repoda ODENMIS bir hatadir; hicbiri
"kod calisiyor mu" testi degil, "sozlesme hala gecerli mi" testidir.
"""

from __future__ import annotations

import ast
import os

import pytest

from polyvo.core import config, paths
from polyvo.core import sqlite as db
from polyvo.core.llm import cache, quality, registry


# ── Onbellek anahtari ─────────────────────────────────────────────────────

def test_hash_prompt_golden():
    """ALTIN HASH. Bu deger degisirse onbellekteki HER satir erisilemez olur,
    yani odenmis her cagri yeniden odenir. Fonksiyonu degistirmek bilincli bir
    karar olmali; bu testin kirilmasi o kararin gorunur hali."""
    assert cache.hash_prompt("local:qwen3:8b", "merhaba") == \
        "226a4f27f98f244ae2189340e8647955"


def test_hash_prompt_separates_model_from_prompt():
    """Model adi ile prompt arasinda ayirici olmasaydi ('ab'+'c' ile
    'a'+'bc') iki farkli cagri ayni anahtara duserdi."""
    assert cache.hash_prompt("ab", "c") != cache.hash_prompt("a", "bc")


def test_cache_roundtrip(tmp_path):
    conn = cache.open_llm_cache_db(str(tmp_path / "llm_cache.sqlite"))
    key = cache.hash_prompt("m", "p")
    assert cache.get_cached(conn, key) is None
    cache.store_cached(conn, key, "m", "p", '{"ok": true}')
    assert cache.get_cached(conn, key) == '{"ok": true}'
    assert cache.count_rows(conn) == 1
    conn.close()


# ── Yol semasi ────────────────────────────────────────────────────────────

def test_global_dirs_have_no_tag():
    """KURAL: kimlik ve onbellek katmani TAG'DEN BAGIMSIZ. Bu dizinlerin
    yolunda bir tag gecerse her yeni veri basligi icin her karar yeniden
    odenir."""
    for path in (paths.raw_dir(), paths.cache_dir(),
                 paths.stores_dir(), paths.human_dir()):
        rel = os.path.relpath(path, paths.data_root())
        assert os.sep not in rel, f"{rel}: global dizin duz olmali"


def test_projection_dirs_are_tag_plural():
    """KURAL: izdusum katmani TAG'E GORE COGUL. Tek yuvali olsaydi ikinci bir
    veri basligi birincisinin ciktisini sessizce ezerdi."""
    a = paths.workspace_dir("tag_a", "en")
    b = paths.workspace_dir("tag_b", "en")
    assert a != b and "tag_a" in a
    assert paths.dist_dir("tag_a", "en") != paths.dist_dir("tag_b", "en")
    assert paths.build_dir("tag_a", "01_build") != paths.build_dir("tag_b", "01_build")


def test_no_stage_name_is_hardcoded_in_paths():
    """Asama adi `build_dir`'a PARAMETRE olarak gelir; paths.py hicbir asama
    adi BILMEZ (asama kayit defteri katman 1'in isidir). Docstring'ler
    disarida: orada ornek vermek serbest, kodda yazmak degil."""
    tree = ast.parse(open(paths.__file__, encoding="utf-8").read())
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    literals = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings
    ]
    for stage in ("01_build", "02_enriched", "03_embedded", "04_content"):
        assert not any(stage in text for text in literals),             f"{stage} paths.py'de KODDA gecmemeli"


# ── Tag cozumlemesi ───────────────────────────────────────────────────────

def test_resolve_tag_prefers_explicit(monkeypatch):
    monkeypatch.setenv("POLYVO_DATA_TITLE", "from_env")
    assert paths.resolve_tag("explicit") == "explicit"


def test_resolve_tag_env_beats_config(monkeypatch):
    monkeypatch.setenv("POLYVO_DATA_TITLE", "from_env")
    assert paths.resolve_tag() == "from_env"


def test_resolve_tag_refuses_to_guess(monkeypatch, tmp_path):
    """Birden fazla aday varsa TAHMIN YOK — 'en yenisini sec' sezgisi
    eklenmemeli. Yanlis tag'e yazmak hic yazmamaktan pahalidir."""
    monkeypatch.delenv("POLYVO_DATA_TITLE", raising=False)
    monkeypatch.setattr(config, "configured_tag", lambda: "")
    monkeypatch.setattr(paths, "list_tags", lambda: ["v6", "v7"])
    with pytest.raises(SystemExit) as exc:
        paths.resolve_tag()
    assert "v6" in str(exc.value) and "v7" in str(exc.value)


def test_resolve_tag_single_candidate(monkeypatch):
    monkeypatch.delenv("POLYVO_DATA_TITLE", raising=False)
    monkeypatch.setattr(config, "configured_tag", lambda: "")
    monkeypatch.setattr(paths, "list_tags", lambda: ["v7"])
    assert paths.resolve_tag() == "v7"


# ── SQLite kapisi ─────────────────────────────────────────────────────────

def test_busy_timeout_is_not_zero(tmp_path):
    """Ayni DOSYAYA yazan iki komut paralel kosabilir; varsayilan 0 ile ikincisi
    beklemeden `database is locked` ile olur."""
    conn = db.connect(str(tmp_path / "x.sqlite"))
    assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == db.BUSY_TIMEOUT_MS
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    conn.close()


def test_row_counts_survives_a_corrupt_file(tmp_path):
    """`sqlite3.connect()` actigi dosyayi DOGRULAMAZ. Korumasiz bir olcum
    yardimcisi, saatlerce suren bir kosuyu is bittikten SONRA dusurur."""
    bad = tmp_path / "bozuk.db"
    bad.write_text("bu bir sqlite dosyasi degil", encoding="utf-8")
    assert db.row_counts(str(bad)) is None
    assert db.row_counts(str(tmp_path / "yok.db")) is None


def test_backup_copy_keeps_uncheckpointed_rows(tmp_path):
    """WAL modunda ham dosya kopyasi commit edilmis ama checkpoint edilmemis
    satirlari dusurur; backup API dusurmemeli."""
    src = str(tmp_path / "src.sqlite")
    conn = db.connect(src, ddl="CREATE TABLE t (x INTEGER);")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    dst = str(tmp_path / "dst.sqlite")
    db.backup_copy(src, dst)
    conn.close()
    assert db.row_counts(dst) == {"t": 1}


# ── Model siralamasi ──────────────────────────────────────────────────────

def test_every_registered_provider_default_model_is_ranked():
    """Siralanmamis bir model SESSIZCE 'en kotu' olur ve hicbir onarim
    yapamaz; bunun fark edilmesi gereken yer burasi."""
    unranked = []
    for name in registry.provider_names():
        model = registry.default_model(name)
        if model is None:
            continue
        label = registry.label_for(name, model)
        if label not in quality.load_model_quality().ranks:
            unranked.append(label)
    assert not unranked, "model_quality.json'da siralanmamis: " + ", ".join(unranked)


def test_unknown_model_is_worst_not_average():
    """'Bilinmiyor' = EN KOTU. 'Ortalama' olsaydi taninmayan bir model bir
    onarimi sessizce engelleyebilirdi."""
    unknown = quality.rank_for("kesinlikle:olmayan-model-xyz")
    known = quality.rank_for("local:qwen3:8b")
    assert unknown >= known
