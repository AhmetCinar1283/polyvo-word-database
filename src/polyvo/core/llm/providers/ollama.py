"""
Ollama (yerel) adapter — `LLMProvider` sozlesmesinin Ollama uygulamasi.

Bu dosya, onceden `src/core/llm/ollama.py`'de duran `call_ollama_json`'in
HTTP/protokol kismini tasir; cache-first zarfi artik `base.py`de tek yerde.

KORUNAN AYRINTILAR (davranis degismemeli):
  - `format: "json"`  — Ollama'nin grammar-constrained ciktisi, kucuk
    modellerde bozuk/yari JSON riskini azaltir.
  - `think: false`     — BULGU (2026-08-13): Qwen3 gibi "hybrid thinking"
    modeller varsayilan olarak yanit vermeden once uzun bir <think> blogu
    uretiyor, `num_predict` butcesi bu blok tarafindan tuketilip JSON cevap
    hic gelmeden kesiliyordu. Gorevimiz basit siniflandirma, akil yurutmeye
    ihtiyac yok.
  - `timeout=120`, `options.num_predict = max_tokens`.
  - varsayilan `temperature=0.1` (kucuk model + siniflandirma gorevi icin).

Etiket oneki "local:" — DEGISTIRME, cache anahtarina giriyor.

UZAK KOSUM ICIN ACILIM (2026-08-16): `request_timeout` ve `_wrap_error`
sinif duzeyinde ezilebilir, cunku ayni Ollama PROTOKOLU uzak bir makinede de
konusulabiliyor (bkz. `providers/colab.py` — Colab'daki Ollama'ya tunel).
Protokol ayni, ama UZAKLIK iki varsayimi bozar: (1) 120 sn yerelde bol, tunel
uzerinden 2000 token'lik bir istekte yetmez; (2) yerelde bir baglanti hatasi
"servis kapali" demektir ve beklemenin anlami yoktur (`default_max_retries=0`),
uzakta ise ayni hata gecici bir tunel blip'i olabilir. Bu iki degeri sabit
birakip alt sinifta ezilemez yapmak, uzak adapterin `_request`i BASTAN
KOPYALAMASINI gerektirirdi — tam da `base.py`nin ortadan kaldirdigi ikilemenin
aynisi. Ollama'nin kendi davranisi burada AYNEN korunur.
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
    name = "ollama"
    label_prefix = "local:"
    default_model = "qwen3:8b"
    env_keys = ()
    needs_api_key = False
    default_max_retries = 0  # yerel servis; olduyse beklemenin anlami yok

    #: `/api/generate` istek zaman asimi (sn). Yerelde 120 bol; uzak kosumda
    #: alt sinif buyutur (bkz. modul docstring'i).
    request_timeout: int = 120

    def __init__(self, model: str | None = None, *, base_url: str | None = None, think: bool = False, **opts):
        super().__init__(model, base_url=base_url, **opts)
        self.host = resolve_setting("ollama", "base_url", ("OLLAMA_HOST",), explicit=base_url, default=DEFAULT_HOST)
        self.think = think

    def preflight(self) -> None:
        if not is_ollama_running(self.host):
            raise LLMUnavailable(
                f"Ollama'ya ulasilamiyor: {self.host}\n"
                f"    Once Ollama'yi baslatin ('ollama serve' ya da Ollama uygulamasi),\n"
                f"    sonra bu komutu tekrar calistirin. Kontrol: curl {self.host}/api/tags"
            )

    def list_models(self) -> list[str] | None:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=3) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return [m["name"] for m in body.get("models", [])] or None
        except Exception:
            return None

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
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
        """HTTP/baglanti hatasini `LLMUnavailable`a cevirir.

        Yerelde her hata KALICI sayilir (`retryable=False`): baglanti kurulamadiysa
        servis kapalidir, beklemek bir sey degistirmez. Uzak adapterler bunu ezer."""
        return LLMUnavailable(
            f"Ollama'ya ulasilamadi ({self.host}) — servis calisiyor mu? "
            f"('ollama serve' / Ollama uygulamasi acik mi kontrol et). Detay: {exc}"
        )


def is_ollama_running(host: str = DEFAULT_HOST) -> bool:
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=3)
        return True
    except Exception:
        return False
