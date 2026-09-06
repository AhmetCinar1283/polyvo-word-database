"""
`polyvo.toml` — TEK calisma-zamani konfigurasyonu: yol semasi, aktif tag,
diller, evren hedefi, varsayilan saglayici.

BURADA OLMAYAN (bilerek): gizli anahtarlar (`.env`, `core/env.py` okur),
model kalite siralamasi (`model_quality.json`), build kilidi
(`source_config.json` — bir OLCUM sonucu, konfig degil).
Yazilabilir tek alan: `project.active_tag` (`write_active_tag`).
"""

from __future__ import annotations

import os
import re
import tomllib
from functools import lru_cache

CONFIG_FILENAME = "polyvo.toml"

DEFAULTS: dict = {
    "project": {"active_tag": "", "l2": "en", "l1": ["tr"]},
    "paths": {"data_root": "data"},
    "universe": {"target_size": 5000},
    "llm": {"default_provider": "ollama"},
}


def project_root() -> str:
    """Depo koku: once `POLYVO_ROOT`, sonra yukari dogru `polyvo.toml` aranir
    (cwd'ye guvenilmez — komutlar alt dizinlerden de calisir)."""
    env = os.environ.get("POLYVO_ROOT")
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.exists(os.path.join(here, CONFIG_FILENAME)):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    # Konfig bulunamadi: paket kokunun uc ustu (src/polyvo/core -> repo koku).
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def config_path() -> str:
    """`polyvo.toml` tam yolu."""
    return os.path.join(project_root(), CONFIG_FILENAME)


def _merge(base: dict, override: dict) -> dict:
    """Iki sozlugu tek seviye birlestirir (override kazanir)."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


@lru_cache(maxsize=1)
def load() -> dict:
    """Konfigi diskten okur ve varsayilanlarla birlestirir; surec ici cache'lenir."""
    path = config_path()
    if not os.path.exists(path):
        return _merge(DEFAULTS, {})
    with open(path, "rb") as f:
        return _merge(DEFAULTS, tomllib.load(f))


def reload() -> dict:
    """Cache'i bosaltip konfigi yeniden okur (testler icin)."""
    load.cache_clear()
    return load()


def get(section: str, key: str, default=None):
    """Bir bolum/anahtar degerini okur; yoksa `default` doner."""
    return load().get(section, {}).get(key, default)


# ── Sik kullanilan alanlar ────────────────────────────────────────────────

def default_l2() -> str:
    """Varsayilan hedef dil (L2)."""
    return str(get("project", "l2", "en"))


def default_l1_list() -> list[str]:
    """Yapilandirilmis tum ana dil (L1) kodlari."""
    value = get("project", "l1", ["tr"])
    return [value] if isinstance(value, str) else list(value)


def default_l1() -> str:
    """Ilk (birincil) L1 kodu."""
    langs = default_l1_list()
    return langs[0] if langs else "tr"


def universe_target_size() -> int:
    """Hedeflenen kelime evreni buyuklugu."""
    return int(get("universe", "target_size", 5000))


def default_provider() -> str:
    """Varsayilan LLM saglayicisinin adi."""
    return str(get("llm", "default_provider", "ollama"))


def configured_tag() -> str:
    """`polyvo.toml`'da yazili aktif tag; yoksa bos string."""
    return str(get("project", "active_tag", "") or "")


def write_active_tag(tag: str) -> None:
    """`project.active_tag`'i yerinde gunceller (blok yoksa olusturur)."""
    path = config_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'[project]\nactive_tag = "{tag}"\n')
        reload()
        return

    with open(path, encoding="utf-8") as f:
        text = f.read()

    pattern = re.compile(r'^(\s*active_tag\s*=\s*).*$', re.MULTILINE)
    if pattern.search(text):
        new_text = pattern.sub(lambda m: f'{m.group(1)}"{tag}"', text, count=1)
    elif re.search(r'^\[project\]\s*$', text, re.MULTILINE):
        new_text = re.sub(r'^(\[project\]\s*)$', rf'\1\nactive_tag = "{tag}"',
                          text, count=1, flags=re.MULTILINE)
    else:
        new_text = text.rstrip("\n") + f'\n\n[project]\nactive_tag = "{tag}"\n'

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    reload()
