"""
Google Colab adapter — Colab'da kosan Ollama'ya tunel uzerinden baglanir.

NEDEN VAR: dizustunun VRAM'i qwen3:8b'de tikaniyor; Colab'in ucretsiz T4'u
16 GB veriyor, yani q4 bir 14B model (~9 GB) rahat siger. Notebook
(`tools/colab/ollama_tunnel.ipynb`) Colab'da Ollama'yi ayaga kaldirip
`cloudflared` hizli tuneliyle disari acar, buraya o https URL'i verilir.

PROTOKOL AYNI, UZAKLIK FARKLI. Konusulan sey birebir Ollama'nin `/api/generate`i
oldugu icin `OllamaProvider`dan turer — istek govdesi, `format: "json"`,
`think: false`, `num_predict` hepsi ORADAN gelir, burada kopyalanmaz. Sadece
uzak olmaktan dogan uc fark ezilir:

  1. `default_max_retries = 4` — yereldeki 0 degeri "baglanti yoksa servis
     kapalidir, beklemek bos" varsayimina dayanir. Tunelde ayni hata cloudflared'in
     anlik bir 502/504'u olabilir; tekrar denemek TAM OLARAK dogru davranistir.
  2. `request_timeout = 600` — F6 (`translation_sync`) `max_tokens=2000` istiyor.
     T4'te q4 bir 14B ~20 tok/sn uretir: tek basina ~100 sn, ustune tunel gecikmesi
     ve model yukleme. Yereldeki 120 sn burada yetmez.
  3. `preflight()` mesaji — yereldeki "'ollama serve' baslatin" tavsiyesi burada
     yanlis yonlendirir; gercek sebep hep "Colab hucresi kapandi / URL degisti"dir.

ETIKET BILEREK PAYLASILIYOR: `label_prefix = "local:"`, yani `ollama` ile AYNI
onbellek ad alani. Onbellek anahtari `sha256(label + prompt)` ve `label` model
adini da icerir; Ollama model etiketleri icerik-adresli (digest) oldugu icin
Colab'daki `qwen3:14b` ile dizustundeki `qwen3:14b` AYNI agirliklardir. Bu yuzden
Colab'da odenen bir cagri yerelde bedavaya gelmeli, tersi de. Cakisma yalnizca
"ayni model" durumunda olur — ki orada paylasmak dogrudur. Colab'da yerelde
olmayan bir model kosulursa etiket zaten farklidir (`local:qwen3:32b`).
"colab:" yapmak tutarli GORUNUR ama binlerce onceden odenmis cagriyi iskalatir;
bu yuzden karar `tools/verify_pipeline.py` §8'de kilitlidir.
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
    name = "colab"
    label_prefix = "local:"  # BILEREK ollama ile ayni — bkz. modul docstring'i
    default_model = "qwen3:14b"
    env_keys = ()
    needs_api_key = False
    menu_note = "(Colab tuneli — once notebook'u calistirip COLAB_URL'i verin)"

    default_max_retries = 4  # tunel blip'leri GECICIDIR (yereldeki 0'in tersi)
    request_timeout = 600  # F6'nin 2000 token'lik istegi + tunel gecikmesi

    def __init__(self, model: str | None = None, *, base_url: str | None = None, think: bool = False, **opts):
        # OllamaProvider.__init__ atlanir: o `default=DEFAULT_HOST` ile localhost'a
        # duser. Burada varsayilan OLMAMALI — URL verilmediginde sessizce yerel
        # Ollama'ya baglanip "Colab kullaniyorum" yanilgisi yaratmasin.
        super(OllamaProvider, self).__init__(model, base_url=base_url, **opts)
        self.host = resolve_setting("colab", "base_url", ("COLAB_URL",), explicit=base_url)
        if self.host:
            self.host = self.host.rstrip("/")
        self.think = think

    def preflight(self) -> None:
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
        if not self.host:
            raise LLMUnavailable("Colab tunel adresi tanimli degil.\n" + _SETUP_HINT)
        return super()._request(prompt, max_tokens=max_tokens, temperature=temperature)

    def _wrap_error(self, exc: urllib.error.URLError) -> LLMUnavailable:
        """Yerelin aksine cogu hata GECICI sayilir — tunelin diger ucunda calisan
        bir GPU var, kopan sey genelde aradaki yol.

        403 ozel olarak ele alinir: Colab notebook'u `cloudflared`i
        `--http-host-header "localhost:11434"` olmadan baslattiysa Ollama yabanci
        `Host` basligini reddeder. Tunel KURULUR, her istek 403 alir — mesaj
        bunu soylemezse teshis edilmesi cok zor bir arizadir."""
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
