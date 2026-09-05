"""
OpenAI-uyumlu `/chat/completions` adapter — TEK sinif, BIRDEN COK kayit.

Bircok saglayici (OpenAI, DeepSeek, Groq, yerelde calisan LM Studio/vLLM)
ayni `/v1/chat/completions` sozlesmesini konusur: `Authorization: Bearer`,
`{"model", "messages", "response_format": {"type":"json_object"}}` govdesi.
Bu yuzden her biri icin ayri bir dosya yerine tek bir `OpenAICompatibleProvider`
tabani var; somut saglayicilar sadece `name`/`label_prefix`/`default_model`/
`base_url`/`env_keys` degerlerini gecen kucuk alt siniflar.

YENI BIR OpenAI-UYUMLU SAGLAYICI EKLEMEK icin (orn. Groq): asagidaki gibi 6
satirlik bir sinif + `providers/__init__.py`'ye bir import satiri yeter.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from polyvo.core.env import resolve_secret, resolve_setting
from polyvo.core.llm.base import LLMProvider, LLMUnavailable
from polyvo.core.llm.registry import register


class OpenAICompatibleProvider(LLMProvider):
    """Somut alt siniflar `name`/`label_prefix`/`default_model`/`default_base_url`/
    `env_keys`i tanimlar; bu sinif protokolu (istek/yanit/hata esleme) tasir."""

    default_base_url: str = ""
    needs_api_key: bool = True

    #: BULGU (2026-08-17): "hybrid thinking" modeller (Qwen3, DeepSeek-R1...)
    #: cevap vermeden ONCE uzun bir akil yurutme blogu uretir ve `max_tokens`
    #: butcesi bu blok tarafindan tuketilir — JSON cevap HIC gelmez.
    #: `ollama.py` bunu ta 2026-08-13'te `think: false` ile cozmustu; bu
    #: protokolde karsiligi `chat_template_kwargs.enable_thinking`.
    #: Olculen (@cf/qwen/qwen3-30b-a3b-fp8, max_tokens=100):
    #:   kapali degilken -> finish_reason=length, content=None, 3.4 neuron
    #:   kapaliyken      -> finish_reason=stop, gecerli JSON, 0.8 neuron
    #: Yani duzeltme sadece dogru degil, 4 KAT DA UCUZ. Dusunmeyen modelleri
    #: bozmaz (llama-3.3-70b'de cikti birebir ayni olculdu), ama gercek
    #: OpenAI/DeepSeek uc noktalari bilinmeyen govde alanini reddedebilir, o
    #: yuzden varsayilan KAPALI — saglayici acikca acar (bkz. cloudflare.py).
    disable_thinking: bool = False

    def __init__(self, model: str | None = None, *, api_key: str | None = None, base_url: str | None = None, **opts):
        super().__init__(model, api_key=api_key, base_url=base_url, **opts)
        self.api_key = resolve_secret(self.name, self.env_keys, explicit=api_key)
        self.base_url = resolve_setting(self.name, "base_url", explicit=base_url, default=self.default_base_url)

    def preflight(self) -> None:
        if self.needs_api_key and not self.api_key:
            raise LLMUnavailable(
                f"{self.name} icin API anahtari tanimli degil. "
                f"--api-key ile ya da LLM_API_KEY_{self.name.upper()} / {' / '.join(self.env_keys)} "
                f"ortam degiskenlerinden biriyle sagla."
            )

    def _wrap_http_error(self, code: int, detail: str, retryable: bool,
                         retry_after: float | None) -> LLMUnavailable:
        """HTTP hatasini `LLMUnavailable`a cevirir. Alt siniflar (Cloudflare)
        yalnizca MESAJI zenginlestirmek icin override eder — `colab.py`nin
        `_wrap_error` deseninin aynisi."""
        return LLMUnavailable(f"{self.name} API hatasi ({code}): {detail}",
                              retryable=retryable, retry_after=retry_after)

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        if self.needs_api_key and not self.api_key:
            raise LLMUnavailable(f"{self.name} icin API anahtari tanimli degil.")

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.disable_thinking:
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code == 429 or exc.code >= 500
            # 429'da sunucu genellikle `Retry-After` gonderir (saniye ya da
            # HTTP-date). Sayi degilse yok sayilir ve exponential backoff'a
            # dusulur — tarih ayristirmak icin bir bagimliligi hak etmiyor.
            retry_after = None
            if exc.code == 429:
                raw_after = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    retry_after = float(raw_after) if raw_after else None
                except ValueError:
                    retry_after = None
            raise self._wrap_http_error(exc.code, detail, retryable, retry_after) from exc
        except urllib.error.URLError as exc:
            raise LLMUnavailable(f"{self.name} API'ye ulasilamadi: {exc}", retryable=True) from exc
        except TimeoutError as exc:
            # Cikplak TimeoutError, URLError'in alt sinifi DEGIL (ozellikle
            # okuma zaman asiminda ssl/socket katmanindan direkt gelir), o
            # yuzden yukaridaki except'e girmez ve retry'siz cokerdi. Olculdu
            # 2026-08-21: buyuk modellerde (llama-3.3-70b) 120s'lik timeout
            # bazen yetmiyor — gecici sayilip retry'a birakiliyor.
            raise LLMUnavailable(f"{self.name} yanit zaman asimina ugradi (120s): {exc}", retryable=True) from exc

        try:
            choice = body["choices"][0]
            message = choice["message"]
            text = message.get("content") or message.get("reasoning_content") or ""
        except (KeyError, IndexError, TypeError, AttributeError):
            return json.dumps(body, ensure_ascii=False)[:2000]

        # `reasoning_content`e DUSMEK gerekiyor: Cloudflare, dusunme kapaliyken
        # bile Qwen3'un tek satirlik cevabini `content` yerine bu alana koyuyor
        # (olculdu 2026-08-17: content=None, reasoning_content='{"primary": 2...}').
        # Sadece `content`e bakan kod, dogru uretilmis bir cevabi bos sanardi.
        if text.strip():
            return text

        # Hic metin gelmedi. Bu bir MODEL YETERSIZLIGI DEGIL, bir yapilandirma
        # hatasidir ve HER ogede tekrar eder: 2026-08-17'de bu sessizlik, tek
        # bir kosuda 404 gloss + 92 sense cagrisini (~3.000 neuron) hicbir uyari
        # vermeden yakti ve depoya 254 uydurma satir yazdi. Beklemek bir sey
        # degistirmeyecegi icin retryable DEGIL: hemen, sebebini soyleyerek dur.
        raise LLMUnavailable(
            f"{self.name} bos yanit dondurdu (finish_reason="
            f"{choice.get('finish_reason')!r}, model={self.model}).\n"
            f"  En olasi sebep: model cevaptan once akil yurutuyor ve "
            f"max_tokens={max_tokens} butcesi bu bloga gidiyor.\n"
            f"  Cozum: saglayici sinifinda disable_thinking = True "
            f"(bkz. providers/openai_compat.py) ya da daha yuksek max_tokens."
        )


@register
class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    label_prefix = "openai:"
    default_model = "gpt-4o-mini"
    default_base_url = "https://api.openai.com/v1"
    env_keys = ("OPENAI_API_KEY",)


@register
class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    label_prefix = "deepseek:"
    default_model = "deepseek-chat"
    default_base_url = "https://api.deepseek.com/v1"
    env_keys = ("DEEPSEEK_API_KEY",)
