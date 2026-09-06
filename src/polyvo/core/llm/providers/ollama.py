"""
Ollama (yerel) adapter — `LLMProvider`in Ollama uygulamasi.

`think: false`: hybrid-thinking modeller (Qwen3) yanittan once uzun bir
<think> blogu uretip `num_predict` butcesini tuketmesin diye kapali.
Etiket oneki "local:" — DEGISTIRME, cache anahtarina giriyor.

`request_timeout`/`_wrap_error` alt sinifta ezilebilir: ayni protokol uzak
bir Ollama'ya (tunel) da konusulabiliyor (bkz. `providers/colab.py`), ama
zaman asimi ve "hata=kalici mi" varsayimi uzakta degisir.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from polyvo.core.env import resolve_setting
from polyvo.core.llm.base import LLMProvider, LLMUnavailable
from polyvo.core.llm.registry import register

DEFAULT_HOST = "http://localhost:11434"


@register
class OllamaProvider(LLMProvider):
    """Yerel Ollama sunucusuna JSON istek atan saglayici."""
    name = "ollama"
    label_prefix = "local:"
    default_model = "qwen3:8b"
    env_keys = ()
    needs_api_key = False
    default_max_retries = 0  # yerel servis; olduyse beklemenin anlami yok

    #: `/api/generate` zaman asimi (sn); uzak kosumda alt sinif buyutur.
    request_timeout: int = 120

    def __init__(self, model: str | None = None, *, base_url: str | None = None, think: bool = False, **opts):
        """Host'u coz (arguman->env->varsayilan localhost) ve dusunme modunu kaydet."""
        super().__init__(model, base_url=base_url, **opts)
        self.host = resolve_setting("ollama", "base_url", ("OLLAMA_HOST",), explicit=base_url, default=DEFAULT_HOST)
        self.think = think

    def preflight(self) -> None:
        """Ollama servisi ayakta mi kontrol eder; degilse acik hata."""
        if not is_ollama_running(self.host):
            raise LLMUnavailable(
                f"Ollama'ya ulasilamiyor: {self.host}\n"
                f"    Once Ollama'yi baslatin ('ollama serve' ya da Ollama uygulamasi),\n"
                f"    sonra bu komutu tekrar calistirin. Kontrol: curl {self.host}/api/tags"
            )

    def list_models(self) -> list[str] | None:
        """Yerel Ollama'da yuklu model adlari; alinamazsa `None`."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in body.get("models", [])] or None
        except Exception:
            return None

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """`/api/generate`e istek atar, ham metni doner."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "think": self.think,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise self._wrap_error(exc) from exc

        return body.get("response", "") if isinstance(body, dict) else str(body)

    def _wrap_error(self, exc: urllib.error.URLError) -> LLMUnavailable:
        """HTTP/baglanti hatasini `LLMUnavailable`a cevirir; yerelde KALICI
        sayilir (`retryable=False`) — uzak adapterler bunu ezer."""
        return LLMUnavailable(
            f"Ollama'ya ulasilamadi ({self.host}) — servis calisiyor mu? "
            f"('ollama serve' / Ollama uygulamasi acik mi kontrol et). Detay: {exc}"
        )


def is_ollama_running(host: str = DEFAULT_HOST) -> bool:
    """Verilen host'ta Ollama'nin ayakta olup olmadigini yoklar."""
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=3)
        return True
    except Exception:
        return False
