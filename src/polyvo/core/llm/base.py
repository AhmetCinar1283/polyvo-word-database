"""
Saglayici-agnostik LLM soyutlamasi — Adapter (`LLMProvider` alt siniflari) +
Template Method (`LLMProvider.complete_json`).

Neden burada tek bir zarf: onceden cache-first mantigi (`hash_prompt` ->
`get_cached` -> istek -> sadece parse edilebileni `store_cached`) `ollama.py`
ve `gemini.py` icinde BIREBIR KOPYA olarak duruyordu — biri retry/pace-delay
gibi bir davranisi degistirdiginde digeri sessizce ayrisiyordu. Artik bu zarf
TEK yerde (`complete_json`); her saglayici sadece kendi HTTP istegini
(`_request`) uygular.

CACHE-KRITIK: `label_prefix` degeri `cache/llm_cache.sqlite` icindeki
`prompt_hash`e giriyor (`sha256(label + prompt)`). Bu deger DEGISIRSE o
saglayicinin TUM onbellegi iskalar (binlerce onceden odenmis LLM cagrisi
yeniden odenir). Mevcut degerler dondurulmustur: Ollama "local:", Gemini
"gemini:" — bkz. `src/core/llm/registry.py`.
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from typing import NamedTuple

from polyvo.core.llm.cache import get_cached, hash_prompt, store_cached

__all__ = ["LLMProvider", "LLMResult", "LLMUnavailable"]


class LLMUnavailable(RuntimeError):
    """Saglayiciya erisilemiyor (servis kapali / API anahtari yok / kalici hata).

    `retryable=True` ile yukseltilirse `complete_json` bunu gecici bir hata
    (429/5xx) sayar ve exponential backoff ile yeniden dener; varsayilan
    False (kalici hata — API anahtari yok, 4xx gibi — hemen yukari firlar).

    `retry_after`: sunucunun `Retry-After` basligiyla soyledigi bekleme suresi
    (saniye). Verildiginde exponential backoff'un YERINE gecer — 429'da tahmin
    etmek yerine sunucunun soyledigi sureyi beklemek hem daha hizli toparlanir
    hem de gereksiz bir istek daha atip limiti tazelemez."""

    def __init__(self, message: str, *, retryable: bool = False,
                 retry_after: float | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


class LLMResult(NamedTuple):
    """`complete_json`'in HER ZAMAN dondurdugu 3'lu. `raw`, parse edilemeyen
    denemelerin bile deneme gunlugune yazilabilmesi icin gerekli."""

    parsed: dict | None
    from_cache: bool
    raw: str


def _extract_json(raw_text: str) -> dict | None:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


class LLMProvider(ABC):
    """Bir LLM saglayicisi icin ince adapter. Alt siniflar sadece `_request`i
    ve (istege bagli) `preflight`/`list_models`i uygular; cache-first zarfi,
    retry ve pace-delay burada, HEPSI icin ortak."""

    name: str = ""
    label_prefix: str = ""
    default_model: str = ""
    env_keys: tuple[str, ...] = ()
    needs_api_key: bool = True

    #: Interaktif saglayici menusunde isim yaninda gorunecek kisa not. Bos
    #: birakilirsa `needs_api_key`ten turetilir (yerel / API anahtari gerekir).
    #: Bu ikili ayrim her saglayiciyi anlatmaya yetmiyor: Colab ne "yerel"dir
    #: (uzakta kosar) ne de API anahtari ister — kendini tarif edebilmeli.
    menu_note: str = ""

    #: gecici hatalarda (429/5xx) kac kez daha denenecek. 0 = retry kapali.
    default_max_retries: int = 5
    retry_base_delay: float = 2.0
    #: Tek bir beklemenin ust siniri (saniye). `Retry-After` bunu asamaz.
    max_retry_delay: float = 60.0

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int | None = None,
        **options,
    ):
        self.model = model or self.default_model
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = self.default_max_retries if max_retries is None else max_retries
        self.options = options

    @property
    def label(self) -> str:
        """Cache anahtarina giren etiket, orn. 'local:qwen3:8b'. DOKUNMA —
        degisirse bu saglayicinin tum onbellegi iskalar."""
        return f"{self.label_prefix}{self.model}"

    def preflight(self) -> None:
        """Koşuya girmeden ONCE saglayiciyi dogrula. Binlerce ogeye girip ilk
        cagrida patlamak yerine hemen net bir mesajla dur. Varsayilan no-op;
        erisim on-kontrolu olan saglayicilar (Ollama servis pingi, Gemini API
        anahtari) override eder."""
        return None

    def list_models(self) -> list[str] | None:
        """Interaktif model secici icin canli liste. Bilinmiyorsa/desteklenmiyorsa
        None (cagiran taraf serbest-metin girisine duser)."""
        return None

    def complete_json(
        self,
        prompt: str,
        cache_conn,
        *,
        max_tokens: int,
        temperature: float,
        pace_delay: float = 0.0,
    ) -> LLMResult:
        """Cache-first JSON cagrisi. `hash_prompt(self.label, prompt)` cache
        anahtarinin TEK uretim yeri budur — cagiran hicbir kod bu hash'i
        kendisi hesaplamamali.

        Sadece basariyla parse edilen cevaplar cache'e yazilir; parse hatasi
        kalici "cevap" olarak saklanmaz. Gecici hatalarda (429/5xx) alt siniftan
        gelen istisnalarda `self.max_retries` kadar exponential backoff ile
        yeniden denenir (`_is_retryable` ile isaretlenmis istisnalar icin).
        """
        prompt_hash = hash_prompt(self.label, prompt)
        cached_response = get_cached(cache_conn, prompt_hash)
        if cached_response is not None:
            return LLMResult(_extract_json(cached_response), True, cached_response)

        raw_text = self._request_with_retry(prompt, max_tokens=max_tokens, temperature=temperature)
        parsed = _extract_json(raw_text)

        if parsed is not None:
            store_cached(cache_conn, prompt_hash, self.label, prompt, raw_text)
        if pace_delay > 0:
            time.sleep(pace_delay)
        return LLMResult(parsed, False, raw_text)

    def _request_with_retry(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        attempt = 0
        while True:
            try:
                return self._request(prompt, max_tokens=max_tokens, temperature=temperature)
            except LLMUnavailable as exc:
                if not exc.retryable or attempt >= self.max_retries:
                    raise
                # Sunucu ne kadar bekleyecegimizi soylediyse ONA uyulur; aksi
                # halde exponential backoff. `retry_after`i tavanlamak gerekiyor:
                # bazi saglayicilar kota penceresinin SONUNU (dakikalar, hatta
                # saatler) bildiriyor ve o sureyi oldugu gibi beklemek kosuyu
                # asili birakirdi — o durumda hata yukari firlayip `--redo` ile
                # devam etmek dogru davranis.
                delay = self.retry_base_delay * (2**attempt)
                if exc.retry_after is not None:
                    delay = min(max(exc.retry_after, delay), self.max_retry_delay)
                print(f"[{self.name}] gecici hata, {delay:.0f} sn bekleniyor "
                      f"(deneme {attempt + 1}/{self.max_retries}): {exc}", flush=True)
                time.sleep(delay)
                attempt += 1

    @abstractmethod
    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """Ham metin yaniti dondurur (henuz JSON parse edilmemis). Gecici bir
        hata icin `LLMUnavailable(..., retryable=True)` yukselt; kalici bir
        hata (API anahtari yok, 4xx) icin `retryable=False` (varsayilan)."""
        raise NotImplementedError
