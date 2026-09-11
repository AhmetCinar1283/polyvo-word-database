"""
Butun dosya yollarinin TEK kaynagi + aktif tag cozumlemesi. Hicbir modul
kendi basina dizin adi yazmaz.

GLOBAL (tag'siz, semantik kimlikle anahtarli): `raw/` kaynaklar, `cache/`
pahali-ama-yeniden-uretilebilir, `stores/` KUTSAL kimlik+odenmis kararlar,
`human/` tier=0 yedek.
TAG'E GORE COGUL (bir build'in izdusumu): `builds/<tag>/`, `workspace/<tag>/
<l2>/`, `dist/<tag>/<l2>/`.

Tag cozumleme sirasi (tahmin YOK): --tag > POLYVO_DATA_TITLE > polyvo.toml >
`workspace/` altinda tek aday > SystemExit.
"""

from __future__ import annotations

import os

from polyvo.core import config

# ── Dil adlari (L1 secimi ve raporlar icin) ───────────────────────────────
LANGUAGE_NAMES: dict[str, str] = {
    "en": "English", "tr": "Turkish", "es": "Spanish", "de": "German",
    "fr": "French", "it": "Italian", "ru": "Russian", "pt": "Portuguese",
    "nl": "Dutch", "pl": "Polish", "ja": "Japanese", "ko": "Korean",
    "zh": "Chinese", "ar": "Arabic", "el": "Greek", "sv": "Swedish",
    "pt-BR": "Brazilian Portuguese",
}


def language_name(code: str) -> str:
    """Dil kodundan okunakli isim uretir; bilinmiyorsa kodu oldugu gibi doner."""
    return LANGUAGE_NAMES.get(code, code)


def _root(*parts: str) -> str:
    """Depo koku altinda bir yol birlestirir."""
    return os.path.join(config.project_root(), *parts)


def data_root() -> str:
    """`data/` dizininin tam yolu (konfigde tasinabilir)."""
    configured = str(config.get("paths", "data_root", "data"))
    if os.path.isabs(configured):
        return configured
    return _root(configured)


def _data(*parts: str) -> str:
    """`data_root()` altinda bir yol birlestirir."""
    return os.path.join(data_root(), *parts)


# ── GLOBAL katman (tag'siz) ───────────────────────────────────────────────

def raw_dir() -> str:
    """Indirilen kaynak dosyalar. Doluysa asla yeniden indirilmez."""
    return _data("raw")


def cache_dir() -> str:
    """Pahali ama YENIDEN URETILEBILIR makine ciktilari."""
    return _data("cache")


def stores_dir() -> str:
    """Kimlik + odenmis kararlar + insan duzeltmeleri. Yeniden uretilemez."""
    return _data("stores")


def human_dir() -> str:
    """tier=0 satirlarin tasinabilir yedegi. Repoya girmez."""
    return _data("human")


def llm_cache_path() -> str:
    """`data/cache/llm_cache.sqlite` tam yolu."""
    return os.path.join(cache_dir(), "llm_cache.sqlite")


def embedding_cache_path() -> str:
    """`data/cache/embedding_store.sqlite` tam yolu."""
    return os.path.join(cache_dir(), "embedding_store.sqlite")


def store_path(name: str) -> str:
    """`data/stores/<name>` — depo dosyalarinin tek adres ureticisi."""
    return os.path.join(stores_dir(), name)


# ── TAG'E GORE COGUL katman ───────────────────────────────────────────────

def builds_root() -> str:
    """`data/builds/` tam yolu."""
    return _data("builds")


def build_dir(tag: str, stage: str) -> str:
    """`data/builds/<tag>/<stage>/` — `stage` asama kayit defterinden gelir
    (`01_build`, `02_enriched`, …); burada hicbir asama adi hardcode DEGILDIR."""
    return _data("builds", tag, stage)


def workspace_dir(tag: str, l2: str | None = None) -> str:
    """`data/workspace/<tag>/<l2>/` tam yolu."""
    return _data("workspace", tag, l2 or config.default_l2())


def dist_dir(tag: str, l2: str | None = None) -> str:
    """`data/dist/<tag>/<l2>/` tam yolu."""
    return _data("dist", tag, l2 or config.default_l2())


def logs_dir(tag: str, l2: str | None = None) -> str:
    """Bir kosunun log dizini."""
    return os.path.join(workspace_dir(tag, l2), "logs")


def source_config_path(tag: str, l2: str | None = None) -> str:
    """Kanonik build kilidi. Bir KONFIG degil, bir OLCUM sonucudur — bu yuzden
    `polyvo.toml`'da degil, ait oldugu izdusumun yaninda durur."""
    return os.path.join(workspace_dir(tag, l2), "source_config.json")


def ensure_dirs() -> None:
    """Global veri dizinlerini olusturur. Tag'li dizinler olusturulmaz —
    onlari asama/izdusum komutlari kendi anlarinda yaratir."""
    for path in (raw_dir(), cache_dir(), stores_dir(), human_dir(), builds_root()):
        os.makedirs(path, exist_ok=True)


# ── Tag cozumlemesi ───────────────────────────────────────────────────────

def list_tags() -> list[str]:
    """`data/workspace/` altinda gecerli bir L2 alt dizini olan tag'ler."""
    base = _data("workspace")
    if not os.path.isdir(base):
        return []
    tags = []
    for entry in sorted(os.listdir(base)):
        full = os.path.join(base, entry)
        if not os.path.isdir(full):
            continue
        if any(sub in LANGUAGE_NAMES and os.path.isdir(os.path.join(full, sub))
               for sub in os.listdir(full)):
            tags.append(entry)
    return tags


def resolve_tag(explicit: str | None = None) -> str:
    """Aktif tag'i sirayla arguman->env->konfig->tek-workspace kurallarina gore cozer; belirsizse SystemExit."""
    if explicit:
        return explicit

    env = os.environ.get("POLYVO_DATA_TITLE")
    if env:
        return env

    configured = config.configured_tag()
    if configured:
        return configured

    tags = list_tags()
    if len(tags) == 1:
        return tags[0]
    if not tags:
        raise SystemExit(
            "[polyvo] Aktif veri basligi belirlenemedi: ne --tag, ne "
            "POLYVO_DATA_TITLE, ne polyvo.toml'da project.active_tag, ne de "
            "data/workspace/ altinda tek bir tag var."
        )
    raise SystemExit(
        "[polyvo] Birden fazla veri basligi adayi var, TAHMIN EDILMEYECEK: "
        + ", ".join(tags)
        + "\n    --tag <ad> ile acikca secin (ya da polyvo.toml -> project.active_tag)."
    )
