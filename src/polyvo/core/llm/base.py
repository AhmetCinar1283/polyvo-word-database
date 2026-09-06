"""
Saglayici-agnostik LLM soyutlamasi. `LLMProvider` cache-first zarfi
(`complete_json`) TEK yerde tasir; alt siniflar sadece kendi HTTP istegini
(`_request`) uygular.

CACHE-KRITIK: `label_prefix` `prompt_hash`e girer (`sha256(label+prompt)`).
Degisirse o saglayicinin TUM onbellegi iskalar — DOKUNMA.
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
    """Saglayiciya erisilemiyor. `retryable=True` -> gecici (429/5xx), backoff
    ile yeniden denenir; varsayilan False -> kalici, hemen yukari firlar.
    `retry_after` verilirse backoff yerine sunucunun soyledigi sure beklenir."""

    def __init__(self, message: str, *, retryable: bool = False,
                 retry_after: float | None = None):
        """Hata mesaji + yeniden-denenebilirlik bayragini kaydeder."""
        super().__init__(message)
        self.retryable = retryable
        self.retry_after = retry_after


class LLMResult(NamedTuple):
    """`complete_json`'in dondurdugu 3'lu. `raw` parse edilemese bile
    deneme gunlugune yazilabilsin diye tutulur."""

    parsed: dict | None
    from_cache: bool
    raw: str


def _extract_json(raw_text: str) -> dict | None:
    """Ham metinden ilk `{...}` blogunu ayiklar; parse edilemezse `None`."""
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


class LLMProvider(ABC):
    """Bir LLM saglayicisi icin ince adapter; cache-first zarfi + retry burada,
    alt siniflar sadece `_request`i uygular."""

    name: str = ""
    label_prefix: str = ""
    default_model: str = ""
    env_keys: tuple[str, ...] = ()
    needs_api_key: bool = True

    #: Interaktif menude isim yaninda gorunecek kisa not (bos ise `needs_api_key`ten turetilir).
    menu_note: str = ""

    #: gecici hatalarda (429/5xx) kac kez daha denenecek. 0 = retry kapali.
    default_max_retries: int = 5
    retry_base_delay: float = 2.0
    #: Tek bir beklemenin ust siniri (saniye). `Retry-After` bunu asamaz.
    max_retry_delay: float = 60.0

    #: Interaktif menude numarali secenek olarak sunulacak bilinen modeller
    #: (canli liste CEKEMEYEN saglayicilar icin, orn. Cloudflare). Bos ise
    #: `list_models` `None` doner, kullanici serbest metin girer.
    known_models: tuple[str, ...] = ()

    def __init__(
        self,
        model: str | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int | None = None,
        **options,
    ):
        """Model/anahtar/retry ayarlarini kaydeder; kalani alt sinifa aittir."""
        self.model = model or self.default_model
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = self.default_max_retries if max_retries is None else max_retries
        self.options = options

    @property
    def label(self) -> str:
        """Cache anahtarina giren etiket, orn. 'local:qwen3:8b' — DOKUNMA."""
        return f"{self.label_prefix}{self.model}"

    def preflight(self) -> None:
        """Kosuya girmeden once saglayiciyi dogrular; varsayilan no-op."""
        return None

    def list_models(self) -> list[str] | None:
        """Interaktif model secici icin canli liste; desteklenmiyorsa
        `known_models`e duser, o da bossa None (serbest metin girisi)."""
        return list(self.known_models) or None

    def complete_json(
        self,
        prompt: str,
        cache_conn,
        *,
        max_tokens: int,
        temperature: float,
        pace_delay: float = 0.0,
    ) -> LLMResult:
        """Cache-first JSON cagrisi. Yalnizca parse edilebilen cevap cache'e
        yazilir; gecici hatada `max_retries` kadar backoff ile yeniden dener."""
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
        """`_request`i cagirir; gecici hatalarda exponential backoff ile yeniden dener."""
        attempt = 0
        while True:
            try:
                return self._request(prompt, max_tokens=max_tokens, temperature=temperature)
            except LLMUnavailable as exc:
                if not exc.retryable or attempt >= self.max_retries:
                    raise
                # Sunucunun soyledigi sure varsa ona uyulur (ama tavanlanir —
                # kota penceresi saatler surebilir, o zaman hata yukari firlar).
                delay = self.retry_base_delay * (2**attempt)
                if exc.retry_after is not None:
                    delay = min(max(exc.retry_after, delay), self.max_retry_delay)
                print(f"[{self.name}] gecici hata, {delay:.0f} sn bekleniyor "
                      f"(deneme {attempt + 1}/{self.max_retries}): {exc}", flush=True)
                time.sleep(delay)
                attempt += 1

    @abstractmethod
    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """Ham metin yaniti dondurur. Gecici hatada `retryable=True` yukselt."""
        raise NotImplementedError
