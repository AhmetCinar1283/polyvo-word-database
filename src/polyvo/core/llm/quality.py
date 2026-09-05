"""
Model kalite siralamasi — hangi modelin kararinin hangisini EZEBILECEGI.

NEDEN VAR: `src/core/stores.py::_should_write` "daha guvenilir kaynak yazar"
kuralini `tier` uzerinden uygular (`human=0 < lang_db=1 < lang_db_llm=2 <
llm=3`). Ama TUM LLM sonuclari tek bir duz `tier=3`'e dusuyordu: Gemini ile
`qwen3:8b` ayirt edilemiyordu, dolayisiyla guclu bir model zayif bir modelin
BOZUK satirini duzeltemiyordu. Olculen durum (2026-08-17): sense store'da
1.862 satir `local:qwen3:8b`, 138 satir `local:qwen3:14b` — hepsi `tier=3`.

Bu modul `tier`'in ALTINA ikinci bir siralama ekler. Karsilastirma artik
`(tier, model_rank)` sozluk sirasi: `lang_db` hala her LLM'in ustundedir,
insan hala dokunulmazdir, ama ayni tier icinde modeller arasinda sira vardir.

--------------------------------------------------------------------------
ANAHTAR: `label`, YENI BIR KIMLIK DEGIL
--------------------------------------------------------------------------
Siralama `label` ile anahtarlanir (`label_prefix + model`, ornegin
`local:qwen3:8b`) — cunku bu deger:

  * depolarda `model_name` sutununda ZATEN sakli (uc depo, `paragraphs` dahil),
  * LLM onbellek anahtarinin da parcasi (`cache.py::hash_prompt`).

Yani yeni bir kimlik kavrami icat edilmiyor; var olan ve zaten yazilan deger
okunuyor. `ollama` ile `colab` ayni `local:` onekini BILEREK paylasir
(`providers/colab.py` docstring'i) — ayni agirliklar, ayni kalite, ayni rank.

--------------------------------------------------------------------------
SUTUN YOK, BACKFILL YOK
--------------------------------------------------------------------------
Rank hicbir tabloya YAZILMAZ; okuma aninda `model_name`'den turetilir. Iki
sebep:

  1. Config'i elle duzenlemek ANINDA her yerde gecerli olur. Rank bir sutuna
     yazilsaydi, siralamayi degistiren her duzenlemeden sonra tum depolarin
     yeniden etiketlenmesi gerekirdi.
  2. `model_name`'e bakip tier/rank YAZAN bir migration tehlikeli olurdu:
     olculdu (2026-08-17) — `translation_store`'da 5 INSAN ONAYLI (`tier=0`)
     satir `model_name='local:qwen3:8b'` tasiyor. Boyle bir migration o
     onaylari makine satiri sanip bozardi.

--------------------------------------------------------------------------
DOSYA TEK DOGRULUK KAYNAGI
--------------------------------------------------------------------------
Desen `src/stages/content/stoplist.py`ten alindi: dosya yoksa varsayilan BIR
KEZ yazilir, sonrasinda elle duzenlenebilir ve dosya kazanir. Gizli bilgi
degil, bir KARAR oldugu icin proje kokunde durur ve git'e girer.
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

# Config'de adi gecmeyen her label bu rank'e duser — yani "bilmiyorum" EN KOTU
# demektir, "ortalama" degil. Bilinmeyen bir model sessizce iyi sayilip
# Gemini'nin duzeltmesini engellemesin.
DEFAULT_RANK = 90

# Kucuk = daha guvenilir. 10'luk bosluklar BILEREK: araya yeni bir model
# girdiginde mevcut hicbir numara degismesin (numaralar depoda saklanmiyor,
# ama config'i elle duzenleyen insan icin de ayni kolaylik gecerli).
#
# AYNI RANK = BIRBIRINI EZMEZ (ilk yazan kalir). Bu kasitli: esit kalitede iki
# model arasinda gidip gelmek sadece bosa API harcamasi olurdu.
DEFAULT_RANKS: dict[str, int] = {
    "gemini:gemini-2.5-pro": 10,
    # Gemini 2.5 Flash ile Cloudflare'in 70B'si BILEREK ayni seviyede:
    # aralarindaki farki tahmin etmek yerine `content-review stats`in model
    # kirilimiyla olcup gerekirse sonra ayirmak icin.
    "gemini:gemini-2.5-flash": 20,
    "cloudflare:@cf/meta/llama-3.3-70b-instruct-fp8-fast": 20,
    "openai:gpt-4o-mini": 20,
    # DeepSeek olculmeden Flash sinifina ALINMIYOR: yanlis varsayim halinde
    # Gemini onun ciktisini artik duzeltemez hale gelirdi (ayni rank ezmez).
    "deepseek:deepseek-chat": 30,
    # `local:` oneki ollama ve colab tarafindan PAYLASILIR — ayni model etiketi
    # ayni agirliklar demek, dolayisiyla ayni rank (bkz. providers/colab.py).
    "local:qwen3:14b": 40,
    "local:qwen3:8b": 50,
    "cloudflare:@cf/meta/llama-3.1-8b-instruct": 50,
}

# Saglayici seviyesi yedek. "Yeni model ekleyince config'e eklensin" isteginin
# yumusak hali: config'e girmemis bir `gemini:gemini-3-flash` en kotuye degil,
# Gemini bandina duser. Yine de `verify_pipeline` §9 her kayitli saglayicinin
# VARSAYILAN modelinin acikca listelenmis olmasini sart kosar.
DEFAULT_PREFIX_RANKS: dict[str, int] = {
    "gemini:": 20,
    "openai:": 20,
    "cloudflare:": 30,
    "deepseek:": 30,
    "local:": 50,
}


@dataclass(frozen=True)
class ModelQuality:
    ranks: dict[str, int]
    prefix_ranks: dict[str, int]
    default_rank: int

    def rank(self, label: str | None) -> int:
        """Bir label'in kalite rank'i. ASLA raise etmez.

        Sira: LLM'siz satir -> birebir eslesme -> en UZUN prefix eslesmesi ->
        `default_rank`.

        `None`/bos icin 0 doner: bu satiri hicbir LLM uretmedi (`lang_db`,
        `single_sense` ya da insan yolu). 0 "en iyi" demek gibi gorunur ama
        etkisi yoktur — o satirlarin `tier`'i zaten daha dusuktur ve
        karsilastirma once `tier`'e bakar. Buraya `default_rank` koymak, bir
        sozluk satirini "bilinmeyen model" gibi gosterip zayif bir LLM'in onu
        ezmesine izin verirdi.
        """
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
    return ModelQuality(
        ranks=dict(DEFAULT_RANKS),
        prefix_ranks=dict(DEFAULT_PREFIX_RANKS),
        default_rank=DEFAULT_RANK,
    )


def _normalize(raw: dict) -> ModelQuality:
    """Diskteki sekli mevcut sekle tasir + dogrular.

    `src/core/paths.py::_normalize` deseni: her yuklemede kosar, boylece eski
    bir dosya sekli calismaya devam eder. Bozuk/eksik alanlar VARSAYILANA
    duser — elle duzenlenen bir dosyadaki tek bir yazim hatasi tum boru
    hattini durdurmasin.
    """
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
    """Config'i yukler; yoksa varsayilani BIR KEZ yazip onu doner.

    Surec icinde bir kez cache'lenir (`reset_cache()` ile bosaltilabilir —
    yalnizca testler/verify icin).
    """
    global _CACHED
    if _CACHED is not None and path is None:
        return _CACHED

    target = path or quality_config_path()
    if os.path.exists(target):
        try:
            with open(target, encoding="utf-8") as f:
                config = _normalize(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            # Bozuk dosya yuzunden pahali bir kosu DUSMEZ; ama sessiz de
            # kalmaz, cunku siralama artik varsayilana donmus demektir.
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
        # Yazilamazsa (salt-okunur checkout, izin) kosu DEVAM eder: bellekteki
        # varsayilanlar zaten dogru siralamayi verir.
        print(f"[model-quality] {target} yazilamadi ({exc}) — varsayilan siralama bellekten kullaniliyor.")


def rank_for(label: str | None) -> int:
    """Kisayol: `load_model_quality().rank(label)`."""
    return load_model_quality().rank(label)


def reset_cache() -> None:
    """Surec-ici cache'i bosaltir. Sadece testler / verify_pipeline icin."""
    global _CACHED
    _CACHED = None
