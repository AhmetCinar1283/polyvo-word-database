"""
`.env` yukleyici + LLM saglayicilari icin katmanli gizli-anahtar/ayar cozumu.

YER (2026-08-16 refactor): `.env` okuyucusu daha once sadece
`src/stages/embedding/search.py` icindeydi ve yalnizca Cloudflare yolundan
cagriliyordu. `src/core/llm/gemini.py` ise `os.environ`'u DOGRUDAN okuyordu,
hicbir dotenv yukleyicisi cagirmadan — yani `.env` dosyasina sadece
`GEMINI_API_KEY=...` eklemek yetmiyordu, degiskenin once kabukta export
edilmis olmasi gerekiyordu (CLAUDE.md § Key design decisions, "does not work
out of the box"). Bu modul o ayrimi kapatir: tum LLM saglayicilari artik ayni
tek yukleyiciden geciyor.

`search.py`'deki `_load_dotenv()` ile davranissal olarak AYNI: proje kokunde
`.env` arar, `KEY=VALUE` satirlarini `os.environ.setdefault` ile yukler (zaten
tanimli gercek ortam degiskenlerinin USTUNE YAZMAZ).
"""

from __future__ import annotations

import os

__all__ = ["load_dotenv", "resolve_secret", "resolve_setting"]

_DOTENV_LOADED = False


def load_dotenv() -> None:
    """Proje kokundeki `.env` dosyasini bir kez okuyup `os.environ`'a yukler.

    Tekrar cagrilirsa no-op (dosya bir kez okunur; ayni surec icinde birden
    fazla saglayici ayni `.env`'i defalarca parse etmesin diye).
    """
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True

    from polyvo.core.config import project_root
    env_path = os.path.join(project_root(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def resolve_secret(provider: str, native_keys: tuple[str, ...], explicit: str | None = None) -> str | None:
    """Bir saglayicinin API anahtarini katmanli sirayla cozer:

        1. `explicit`             — cagiran tarafin verdigi deger (--api-key bayragi)
        2. `LLM_API_KEY_<PROVIDER>` — saglayici-ozel genel ad, orn. LLM_API_KEY_DEEPSEEK
        3. `native_keys`          — saglayicinin kendi/eski adi, orn. GEMINI_API_KEY
        4. `LLM_API_KEY`          — genel yedek

    Adim 3 adim 4'ten ONCE gelir: ikisi de tanimliysa spesifik olan kazanir —
    aksi halde birden fazla saglayici kullanan biri hangisinin devrede
    oldugunu kestiremez.
    """
    load_dotenv()

    if explicit:
        return explicit

    scoped = os.environ.get(f"LLM_API_KEY_{provider.upper()}")
    if scoped:
        return scoped

    for key in native_keys:
        val = os.environ.get(key)
        if val:
            return val

    generic = os.environ.get("LLM_API_KEY")
    if generic:
        return generic

    return None


def resolve_setting(
    provider: str,
    name: str,
    native_keys: tuple[str, ...] = (),
    explicit: str | None = None,
    default: str | None = None,
) -> str | None:
    """`resolve_secret` ile ayni katmanli mantik, gizli-olmayan ayarlar icin
    (orn. base_url/host). `LLM_<NAME>_<PROVIDER>` -> `native_keys` -> `default`."""
    load_dotenv()

    if explicit:
        return explicit

    scoped = os.environ.get(f"LLM_{name.upper()}_{provider.upper()}")
    if scoped:
        return scoped

    for key in native_keys:
        val = os.environ.get(key)
        if val:
            return val

    return default
