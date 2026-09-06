"""
`.env` yukleyici + LLM saglayicilari icin katmanli gizli-anahtar/ayar cozumu.

Proje kokunde `.env` arar, `KEY=VALUE` satirlarini `setdefault` ile yukler
(gercek ortam degiskeninin ustune YAZMAZ). Tum saglayicilar tek bu
yukleyiciden gecer — biri `.env`'i, digeri `os.environ`'u okumaz.
"""

from __future__ import annotations

import os

__all__ = ["load_dotenv", "resolve_secret", "resolve_setting"]

_DOTENV_LOADED = False


def load_dotenv() -> None:
    """`.env`'i bir kez okuyup `os.environ`'a yukler; tekrar cagri no-op."""
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
    """API anahtarini sirayla cozer: `explicit` > `LLM_API_KEY_<PROVIDER>` >
    `native_keys` (orn. GEMINI_API_KEY) > genel `LLM_API_KEY` yedek."""
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
