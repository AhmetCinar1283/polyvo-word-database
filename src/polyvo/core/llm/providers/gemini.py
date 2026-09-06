"""
Google Gemini adapter — `LLMProvider`in Gemini uygulamasi.

`responseMimeType: "application/json"` ile JSON-constrained cikti; 429/5xx
`retryable=True` isaretlenir (backoff `base.py`de). Engellenmis/bos yanitta
ham govde kirpilip `raw` olarak donuyor (deneme gunlugu icin).
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
    """Google Gemini API'sine istek atan saglayici."""
    name = "gemini"
    label_prefix = "gemini:"
    default_model = "gemini-2.5-flash"
    env_keys = ("GEMINI_API_KEY",)
    needs_api_key = True

    def __init__(self, model: str | None = None, *, api_key: str | None = None, **opts):
        """API anahtarini coz (arguman->env) ve kaydet."""
        super().__init__(model, api_key=api_key, **opts)
        self.api_key = resolve_secret("gemini", self.env_keys, explicit=api_key)

    def preflight(self) -> None:
        """API anahtari tanimli mi kontrol eder; degilse acik hata."""
        if not self.api_key:
            raise LLMUnavailable(
                "GEMINI_API_KEY ortam degiskeni tanimli degil. aistudio.google.com'dan "
                "bir API anahtari alip .env dosyasina GEMINI_API_KEY=... olarak ekle."
            )

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """Gemini `generateContent` uc noktasina istek atar."""
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
            # Engellenmis/bos yanit — kucultulmus ham govde deneme gunlugu icin.
            raw_text = json.dumps(body, ensure_ascii=False)[:2000]

        return raw_text


def is_gemini_configured() -> bool:
    """`GEMINI_API_KEY` tanimli mi (menude durum gostermek icin)."""
    return bool(resolve_secret("gemini", ("GEMINI_API_KEY",)))
