"""
`polyvo.toml` — projenin TEK calisma-zamani konfigurasyonu.

Eski repoda ayni bilgi bes ayri yere dagilmisti: `.active_tag` dosyasi,
`workspace/<tag>/<l2>/source_config.json`, sekiz dosyada hardcode edilmis
`5000`, kod icinde sabit dizin adlari ve `.env`. Sonuc: "aktif tag ne" ya da
"evren kac kelime" sorusunun cevabi nereye bakildigina gore degisiyordu.

BU DOSYADA OLAN: yol semasi, aktif veri basligi, diller, evren hedefi,
varsayilan saglayici — yani KARARLAR.
BU DOSYADA OLMAYAN, ve bilerek:
  * gizli anahtarlar -> `.env` (repoya girmez; `core/env.py` okur)
  * model kalite siralamasi -> `model_quality.json` (kendi basina bir karar
    dosyasi; elle duzenlenir, repoya girer, `rank_for` onu okur)
  * bir build'in KANONIK KILIDI -> `data/workspace/<tag>/<l2>/source_config.json`
    (bu bir konfig degil, bir OLCUM sonucudur: hangi build dosyalari hangi
    satir sayilariyla kilitlendi. Konfige tasinamaz.)

YAZILABILIR TEK ALAN `project.active_tag`'dir (`write_active_tag`). Tek bir
skaler satir yerinde degistirilir; dosyanin geri kalanina, yorumlarina ve
siralamasina dokunulmaz — konfig insanin duzenledigi bir dosyadir, makinenin
yeniden serilestirdigi bir cikti degil.
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
    """Depo koku. Once `POLYVO_ROOT`, sonra bu dosyadan yukari dogru
    `polyvo.toml` aranir — cwd'ye GUVENILMEZ, cunku komutlar alt dizinlerden
    de calistirilir (eski repo `os.chdir` ile bunu maskeliyordu)."""
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
    return os.path.join(project_root(), CONFIG_FILENAME)


def _merge(base: dict, override: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


@lru_cache(maxsize=1)
def load() -> dict:
    path = config_path()
    if not os.path.exists(path):
        return _merge(DEFAULTS, {})
    with open(path, "rb") as f:
        return _merge(DEFAULTS, tomllib.load(f))


def reload() -> dict:
    load.cache_clear()
    return load()


def get(section: str, key: str, default=None):
    return load().get(section, {}).get(key, default)


# ── Sik kullanilan alanlar ────────────────────────────────────────────────

def default_l2() -> str:
    return str(get("project", "l2", "en"))


def default_l1_list() -> list[str]:
    value = get("project", "l1", ["tr"])
    return [value] if isinstance(value, str) else list(value)


def default_l1() -> str:
    langs = default_l1_list()
    return langs[0] if langs else "tr"


def universe_target_size() -> int:
    return int(get("universe", "target_size", 5000))


def default_provider() -> str:
    return str(get("llm", "default_provider", "ollama"))


def configured_tag() -> str:
    return str(get("project", "active_tag", "") or "")


def write_active_tag(tag: str) -> None:
    """`project.active_tag`'i yerinde gunceller. Anahtar yoksa `[project]`
    blogunun basina eklenir; blok da yoksa dosyanin sonuna eklenir."""
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
