"""
Model kalite siralamasi — `tier`'in ALTINDA ikinci bir sira: ayni tier'daki
(orn. tier=3, hepsi LLM) modeller arasinda hangisi hangisini ezebilir.

Anahtar `label`'dir (`label_prefix+model`, orn. `local:qwen3:8b`) — depoda
zaten saklanan deger, yeni bir kimlik icat edilmez. Rank HICBIR tabloya
yazilmaz, her okumada `model_quality.json`'dan turetilir: config'i elle
duzenlemek aninda gecerli olsun, geriye donuk "hangi satir hangi modeldendi"
yeniden etiketlemesi (migration) hic gerekmesin.

`model_quality.json` yoksa varsayilanlarla BIR KEZ yazilir, sonra dosya
kazanir (elle duzenlenebilir, git'e girer).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

__all__ = [
    "DEFAULT_PREFIX_RANKS",
    "DEFAULT_RANK",
    "DEFAULT_RANKS",
    "ModelQuality",
    "load_model_quality",
    "quality_config_path",
    "rank_for",
    "reset_cache",
]

CONFIG_FILENAME = "model_quality.json"

# Bilinmeyen model bu rank'e duser: "bilmiyorum" EN KOTU demektir, ortalama degil.
DEFAULT_RANK = 90

# Kucuk = daha guvenilir. 10'luk bosluklar: araya yeni model eklenince mevcut
# numaralar degismesin. Ayni rank BIRBIRINI EZMEZ (ilk yazan kalir).
DEFAULT_RANKS: dict[str, int] = {
    "gemini:gemini-2.5-pro": 10,
    "gemini:gemini-2.5-flash": 20,
    "cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast": 20,
    "openai:gpt-4o-mini": 20,
    "deepseek:deepseek-chat": 30,
    "cloudflare:@cf/qwen/qwen3-30b-a3b-fp8": 40,
    # `local:` oneki ollama+colab arasinda PAYLASILIR (ayni model = ayni rank).
    "local:qwen3:14b": 40,
    "local:qwen3:8b": 50,
    "cloudflare:@cf/meta/llama-3.1-8b-instruct": 50,
}

# Config'e girmemis yeni bir model, en kotuye degil kendi saglayici bandina duser.
DEFAULT_PREFIX_RANKS: dict[str, int] = {
    "gemini:": 20,
    "openai:": 20,
    "cloudflare:": 30,
    "deepseek:": 30,
    "local:": 50,
}


@dataclass(frozen=True)
class ModelQuality:
    """Yuklenmis rank tablosu + `rank_for` aramasi."""
    ranks: dict[str, int]
    prefix_ranks: dict[str, int]
    default_rank: int

    def rank(self, label: str | None) -> int:
        """Sira: birebir eslesme -> en uzun prefix -> `default_rank`.
        `None`/bos icin 0 (LLM'siz satir; `tier` zaten onu korur)."""
        if not label:
            return 0
        if label in self.ranks:
            return self.ranks[label]
        best_prefix = ""
        for prefix in self.prefix_ranks:
            if label.startswith(prefix) and len(prefix) > len(best_prefix):
                best_prefix = prefix
        if best_prefix:
            return self.prefix_ranks[best_prefix]
        return self.default_rank


_CACHED: ModelQuality | None = None


def quality_config_path() -> str:
    """Config dosyasinin tam yolu. Cagri yerlerinde ASLA hardcode edilmez."""
    from polyvo.core.config import project_root
    return os.path.join(project_root(), CONFIG_FILENAME)


def _defaults() -> ModelQuality:
    """Kod-ici varsayilan siralamadan bir `ModelQuality` uretir."""
    return ModelQuality(
        ranks=dict(DEFAULT_RANKS),
        prefix_ranks=dict(DEFAULT_PREFIX_RANKS),
        default_rank=DEFAULT_RANK,
    )


def _normalize(raw: dict) -> ModelQuality:
    """Diskteki sekli dogrular; bozuk/eksik alan VARSAYILANA duser (tek
    yazim hatasi tum boru hattini durdurmasin)."""
    ranks = {
        str(k): int(v)
        for k, v in (raw.get("ranks") or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    prefix_ranks = {
        str(k): int(v)
        for k, v in (raw.get("prefix_ranks") or {}).items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    }
    default_rank = raw.get("default_rank")
    if not isinstance(default_rank, int) or isinstance(default_rank, bool):
        default_rank = DEFAULT_RANK
    return ModelQuality(
        ranks=ranks or dict(DEFAULT_RANKS),
        prefix_ranks=prefix_ranks or dict(DEFAULT_PREFIX_RANKS),
        default_rank=default_rank,
    )


def load_model_quality(path: str | None = None) -> ModelQuality:
    """Config'i yukler (surec-ici cache'li); yoksa varsayilani BIR KEZ yazar."""
    global _CACHED
    if _CACHED is not None and path is None:
        return _CACHED

    target = path or quality_config_path()
    if os.path.exists(target):
        try:
            with open(target, encoding="utf-8") as f:
                config = _normalize(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            # Bozuk dosyada kosu DUSMEZ, ama sessiz de kalmaz.
            print(f"[model-quality] {target} okunamadi ({type(exc).__name__}: {exc}) — "
                  f"varsayilan siralama kullaniliyor.")
            config = _defaults()
    else:
        config = _defaults()
        _write_defaults(target, config)

    if path is None:
        _CACHED = config
    return config


def _write_defaults(target: str, config: ModelQuality) -> None:
    """Varsayilan siralamayi dosyaya BIR KEZ yazar (elle duzenlenebilir)."""
    payload = {
        "_comment": (
            "Model kalite siralamasi. Kucuk sayi = daha guvenilir; ayni rank'teki iki "
            "model birbirinin satirini EZMEZ. Anahtar, saglayicinin 'label' degeridir "
            "(label_prefix + model) — depolardaki model_name sutununda saklanan degerin "
            "aynisi. Bu dosya elle duzenlenebilir ve duzenleme ANINDA gecerli olur; "
            "hicbir yeniden etiketleme (backfill) gerekmez."
        ),
        "default_rank": config.default_rank,
        "ranks": config.ranks,
        "prefix_ranks": config.prefix_ranks,
    }
    try:
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        # Yazilamazsa kosu DEVAM eder — bellekteki varsayilanlar yeterli.
        print(f"[model-quality] {target} yazilamadi ({exc}) — varsayilan siralama bellekten kullaniliyor.")


def rank_for(label: str | None) -> int:
    """Kisayol: `load_model_quality().rank(label)`."""
    return load_model_quality().rank(label)


def reset_cache() -> None:
    """Surec-ici cache'i bosaltir. Sadece testler / verify_pipeline icin."""
    global _CACHED
    _CACHED = None
