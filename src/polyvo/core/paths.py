"""
Butun dosya yollarinin TEK kaynagi + aktif veri basligi (tag) cozumlemesi.

Hicbir modul kendi basina bir dizin adi yazmaz. Sebep sadece duzen degil:
eski repoda tasinan bir dosyanin yolu iki yerde guncellenmedigi icin uc kez
sessiz veri kaybi yasandi (gorsel katalogu, embedding deposu, LLM onbellegi) —
uc seferinde de kod "basarili" raporlayip bos ciktiyla devam etti.

## Iki sinif dizin, ve aralarindaki fark neden kritik

  GLOBAL (tag'siz)  — anahtari SEMANTIK KIMLIK: synset, kelime, prompt hash.
      data/raw/     indirilen kaynaklar
      data/cache/   pahali AMA yeniden uretilebilir (LLM + embedding)
      data/stores/  KIMLIK + odenmis kararlar + insan duzeltmeleri. KUTSAL.
      data/human/   tier=0 tasinabilir yedek
    Bunlar tag'e gore bolunemez: bolunurse her yeni veri basligi icin her
    embedding/LLM/anlam/gloss/ceviri karari YENIDEN odenir.

  TAG'E GORE COGUL — bir build'in IZDUSUMU:
      data/builds/<tag>/<NN_stage>/
      data/workspace/<tag>/<l2>/
      data/dist/<tag>/<l2>/
    Bunlar tek yuvali olamaz: olurlarsa ikinci bir veri basligi birincisinin
    ciktisini sessizce ezer (eski repoda tam olarak bu oldu).

## Tag cozumleme (KURAL: tahmin yok)

    1. acik argüman            --tag / --data-title
    2. ortam degiskeni         POLYVO_DATA_TITLE
    3. polyvo.toml             project.active_tag
    4. data/workspace/ altinda TAM OLARAK BIR aday varsa -> o
    5. aksi halde              SystemExit, adaylari listeleyerek

4. adimda birden fazla aday varsa da durulur. "En yenisini sec" gibi bir
sezgi EKLENMEZ: yanlis tag'e yazmak, hic yazmamaktan pahalidir.
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
}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


def _root(*parts: str) -> str:
    return os.path.join(config.project_root(), *parts)


def data_root() -> str:
    configured = str(config.get("paths", "data_root", "data"))
    if os.path.isabs(configured):
        return configured
    return _root(configured)


def _data(*parts: str) -> str:
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
    return os.path.join(cache_dir(), "llm_cache.sqlite")


def embedding_cache_path() -> str:
    return os.path.join(cache_dir(), "embedding_store.sqlite")


def store_path(name: str) -> str:
    """`data/stores/<name>` — depo dosyalarinin tek adres ureticisi."""
    return os.path.join(stores_dir(), name)


# ── TAG'E GORE COGUL katman ───────────────────────────────────────────────

def builds_root() -> str:
    return _data("builds")


def build_dir(tag: str, stage: str) -> str:
    """`data/builds/<tag>/<stage>/` — `stage` asama kayit defterinden gelir
    (`01_build`, `02_enriched`, …); burada hicbir asama adi hardcode DEGILDIR."""
    return _data("builds", tag, stage)


def workspace_dir(tag: str, l2: str | None = None) -> str:
    return _data("workspace", tag, l2 or config.default_l2())


def dist_dir(tag: str, l2: str | None = None) -> str:
    return _data("dist", tag, l2 or config.default_l2())


def logs_dir(tag: str, l2: str | None = None) -> str:
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
