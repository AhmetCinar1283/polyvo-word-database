"""
Google Colab adapter — Colab'da kosan Ollama'ya tunel uzerinden baglanir
(guclu GPU/VRAM icin; notebook: `tools/colab/ollama_tunnel.ipynb`).

`OllamaProvider`dan turer (protokol ayni, sadece uzaklik farkli): retry
acik (tunel blip'i gecicidir), timeout uzun (600 sn).

ETIKET BILEREK `"local:"` — `ollama` ile AYNI onbellek ad alanini paylasir,
cunku ayni model adi ayni agirliklar demektir; `"colab:"` yapmak binlerce
onceden odenmis cagriyi iskalatirdi.
"""

from __future__ import annotations

import urllib.error

from polyvo.core.env import resolve_setting
from polyvo.core.llm.base import LLMUnavailable
from polyvo.core.llm.providers.ollama import OllamaProvider, is_ollama_running
from polyvo.core.llm.registry import register

_SETUP_HINT = (
    "    1. tools/colab/ollama_tunnel.ipynb dosyasini Colab'a yukleyip hucreleri sirayla calistirin.\n"
    "    2. Son hucrenin bastigi https://....trycloudflare.com adresini alin.\n"
    "    3. Ya .env dosyasina 'COLAB_URL=https://...' yazin, ya da --base-url ile verin."
)


@register
class ColabProvider(OllamaProvider):
    """Ollama API'sini bir Colab tuneli uzerinden kullanan saglayici."""
    name = "colab"
    label_prefix = "local:"  # BILEREK ollama ile ayni (modul docstring'i)
    default_model = "qwen3:14b"
    env_keys = ()
    needs_api_key = False
    menu_note = "(Colab tuneli — once notebook'u calistirip COLAB_URL'i verin)"

    default_max_retries = 4  # tunel blip'leri GECICIDIR (yereldeki 0'in tersi)
    request_timeout = 600  # F6'nin 2000 token'lik istegi + tunel gecikmesi

    def __init__(self, model: str | None = None, *, base_url: str | None = None, think: bool = False, **opts):
        """Tunel adresini coz (varsayilansiz — bkz. asagidaki not) ve kaydet."""
        # OllamaProvider.__init__ atlanir: onun localhost varsayilanina
        # dusup "Colab kullaniyorum" yanilgisi yaratmasin diye.
        super(OllamaProvider, self).__init__(model, base_url=base_url, **opts)
        self.host = resolve_setting("colab", "base_url", ("COLAB_URL",), explicit=base_url)
        if self.host:
            self.host = self.host.rstrip("/")
        self.think = think

    def preflight(self) -> None:
        """Tunel adresi tanimli ve ayakta mi kontrol eder; degilse acik hata."""
        if not self.host:
            raise LLMUnavailable(
                "Colab tunel adresi tanimli degil.\n" + _SETUP_HINT
            )
        if not is_ollama_running(self.host):
            raise LLMUnavailable(
                f"Colab tuneline ulasilamiyor: {self.host}\n"
                f"    Tunel olmus olabilir. Sirayla kontrol edin:\n"
                f"    - Colab sekmesi hala acik mi, tunel hucresi hala kosuyor mu?\n"
                f"    - Colab oturumu zaman asimina ugradi mi (bosta ~90 dk)?\n"
                f"    - URL degisti mi? Her yeni oturumda YENI bir adres uretilir.\n"
                f"    Kontrol: curl {self.host}/api/tags"
            )

    def _request(self, prompt: str, *, max_tokens: int, temperature: float) -> str:
        """Ollama istegini tunel host'una atar."""
        if not self.host:
            raise LLMUnavailable("Colab tunel adresi tanimli degil.\n" + _SETUP_HINT)
        return super()._request(prompt, max_tokens=max_tokens, temperature=temperature)

    def _wrap_error(self, exc: urllib.error.URLError) -> LLMUnavailable:
        """Yerelin aksine cogu hata GECICI sayilir (kopan genelde tunel).
        403'e ozel mesaj: cloudflared host-header bayragi eksikse olur."""
        if isinstance(exc, urllib.error.HTTPError):
            if exc.code == 403:
                return LLMUnavailable(
                    f"Colab tuneli 403 dondu ({self.host}). Neredeyse kesin sebep: tunel "
                    f"`--http-host-header \"localhost:11434\"` bayragi OLMADAN baslatilmis; "
                    f"Ollama yabanci bir Host basligini reddediyor. Notebook'taki tunel "
                    f"hucresini oldugu gibi calistirin."
                )
            retryable = exc.code == 429 or exc.code >= 500
            return LLMUnavailable(
                f"Colab tuneli HTTP {exc.code} dondu ({self.host}). Detay: {exc}",
                retryable=retryable,
            )
        return LLMUnavailable(
            f"Colab tuneline ulasilamadi ({self.host}) — Colab oturumu dusmus ya da "
            f"tunel kopmus olabilir. Detay: {exc}",
            retryable=True,
        )
