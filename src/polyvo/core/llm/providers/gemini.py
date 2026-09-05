"""
Google Gemini adapter — `LLMProvider` sozlesmesinin Gemini uygulamasi.

Bu dosya, onceden `src/core/llm/gemini.py`'de duran `call_gemini_json`'in
HTTP/protokol kismini tasir; cache-first zarfi artik `base.py`de tek yerde.

KORUNAN AYRINTILAR (davranis degismemeli):
  - `responseMimeType: "application/json"` — JSON-constrained cikti.
  - `timeout=120`, varsayilan `temperature=0.7`.
  - Engellenmis/bos yanitta ham govde 2000 karaktere kirpilip `raw` olarak
    dondurulur ki cagiran taraf deneme gunlugune yazabilsin (parse zaten None
    donecek).
  - API anahtari SADECE `polyvo.core.env.resolve_secret` uzerinden okunur —
    onceden `os.environ`'u dogrudan okuyup hicbir `.env` yukleyicisi
    cagirmiyordu (bkz. CLAUDE.md "does not work out of the box" maddesi);
    artik ayni zincir Cloudflare ile paylasiliyor.
  - Gecici hatalar (429/5xx) `retryable=True` ile isaretlenir — `base.py`
    bunlari exponential backoff ile yeniden dener (Cloudflare'daki
    `search.py::_cf_run` desenin ayni sekilde: `CF_RETRY_BASE_DELAY * 2**attempt`).

Etiket oneki "gemini:" — DEGISTIRME, cache anahtarina giriyor.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from polyvo.core.env import resolve_secret
from polyvo.core.llm.base import LLMProvider, LLMUnavailable
from polyvo.core.llm.registry import register

DEFAULT_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


@register
class GeminiProvider(LLMProvider):
    name = "gemini"
    label_prefix = "gemini:"
    default_model = "gemini-2.5-flash"
    env_keys = ("GEMINI_API_KEY",)
    needs_api_key = True

    def __init__(self, model: str | None = None, *, api_key: str | None = None, **opts):
        super().__init__(model, api_key=api_key, **opts)
        self.api_key = resolve_secret("gemini", self.env_keys, explicit=api_key)

    def preflight(self) -> None:
        if not self.api_key:
            raise LLMUnavailable(
                "GEMINI_API_KEY ortam degiskeni tanimli degil. aistudio.google.com'dan "
                "bir API anahtari alip .env dosyasina GEMINI_API_KEY=... olarak ekle."
            )

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            raise LLMUnavailable(
                "GEMINI_API_KEY ortam degiskeni tanimli degil. aistudio.google.com'dan "
                "bir API anahtari alip .env dosyasina GEMINI_API_KEY=... olarak ekle."
            )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        url = f"{DEFAULT_API_BASE}/{self.model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code == 429 or exc.code >= 500
            raise LLMUnavailable(f"Gemini API hatasi ({exc.code}): {detail}", retryable=retryable) from exc
        except urllib.error.URLError as exc:
            raise LLMUnavailable(f"Gemini API'ye ulasilamadi: {exc}", retryable=True) from exc

        raw_text = ""
        try:
            candidates = body.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                raw_text = "".join(p.get("text", "") for p in parts)
        except (AttributeError, IndexError, KeyError):
            raw_text = ""

        if not raw_text:
            # engellenmis/bos yanit (guvenlik filtresi, MAX_TOKENS'a carpma vb.)
            # — ham govdeyi (kucultulmus) raw_text olarak birak ki cagiran taraf
            # denem gunlugune yazabilsin; parse None donecek zaten.
            raw_text = json.dumps(body, ensure_ascii=False)[:2000]

        return raw_text


def is_gemini_configured() -> bool:
    return bool(resolve_secret("gemini", ("GEMINI_API_KEY",)))
