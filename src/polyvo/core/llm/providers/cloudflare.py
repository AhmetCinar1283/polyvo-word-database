"""
Cloudflare Workers AI adapter — OpenAI-uyumlu `/ai/v1/chat/completions` uc
noktasi uzerinden metin/JSON uretimi.

NEDEN VAR: Cloudflare Workers AI zaten embedding tarafinda kullaniliyordu
(`embed-sync`/`embed-apply`, `CF_ACCOUNT_ID` + `CF_API_TOKEN` —
`src/stages/embedding/search.py`), ama metin uretimi (sense/gloss/generate/
cloze/translate) icin hic baglanmamisti. Workers AI'nin sohbet modelleri de
(Llama, Mistral, Qwen...) OpenAI'nin `/chat/completions` sozlesmesini
konusuyor, o yuzden yeni bir protokol yazmak yerine
`OpenAICompatibleProvider`den turer — tek fark hesap ID'sinin base_url'in
ICINE gomulmesi gerekmesi (`/accounts/<id>/ai/v1`), o yuzden `__init__`
kucuk bir override yapiyor.

AYNI ENV DEGISKENLERI: `CF_ACCOUNT_ID` / `CF_API_TOKEN`, embedding tarafiyla
birebir ayni — iki ayri Cloudflare kimlik bilgisi tutmaya gerek yok. Ikisi de
`.env` uzerinden `src/core/env.py::load_dotenv` ile okunur.
"""

from __future__ import annotations

from polyvo.core.env import resolve_setting
from polyvo.core.llm.base import LLMUnavailable
from polyvo.core.llm.providers.openai_compat import OpenAICompatibleProvider
from polyvo.core.llm.registry import register


@register
class CloudflareProvider(OpenAICompatibleProvider):
    name = "cloudflare"
    label_prefix = "cloudflare:"
    default_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    env_keys = ("CF_API_TOKEN",)
    menu_note = "(Cloudflare Workers AI — CF_ACCOUNT_ID + CF_API_TOKEN gerekir)"

    # Workers AI'de iki AYRI sinir var ve karistirilmasi kolay:
    #   (1) gunluk ucretsiz neuron kotasi  -> tukenirse beklemek COZUM DEGIL
    #   (2) model basina dakikalik istek hizi (RPM) -> 429, saniyeler icinde acilir
    # Olculen (2026-08-17): boru hatti frenlemeden istek attiginda hemen 429
    # aliniyor ve CF panosunda neuron tuketimi GORUNMUYOR, cunku istek hic
    # calistirilmadi. Yani "too many requests" bir kota sorunu degil, hiz
    # sorunudur — dogru cevap beklemek, durmak degil. Bu yuzden 5 -> 8.
    default_max_retries = 8
    retry_base_delay = 3.0

    # Workers AI katalogunda dusunen modeller var (`@cf/qwen/qwen3-*`,
    # `@cf/deepseek-ai/*`) ve F2'nin token butceleri kucuk (sense 100, gloss
    # 180) — akil yurutme acikken JSON cevap hic gelmiyor. Dusunmeyen
    # modellerde (llama-3.3-70b) cikti birebir ayni olculdu, o yuzden
    # saglayici genelinde acik. Bkz. openai_compat.disable_thinking.
    disable_thinking = True

    def _wrap_http_error(self, code, detail, retryable, retry_after):
        exc = super()._wrap_http_error(code, detail, retryable, retry_after)
        if code == 429:
            # 2026-09-04'e KADAR burasi HER 429'u kosulsuz RPM sayiyordu ("Bu
            # GUNLUK KOTA degil" mesaji SABIT metindi). Yanlisti: gercek gunluk
            # kota tukenmesi de 429 doner ve govdesinde AYIRT EDICI bir ifade
            # tasir ("daily free allocation", "code":4006) — o govdeyi hic
            # okumadan "kota degil, hiz siniri" demek, kullaniciyi tam olarak
            # yanlis yone (bekle/pace-delay koy) yonlendiriyordu, oysa GERCEK
            # kota bitince beklemenin/hiz dusurmenin HICBIR faydasi yok (sifirlanma
            # CF'nin kendi gunluk penceresi, "birkac saniye" degil). Govde metni
            # ayirt edici oldugunda dogru mesaj + retryable=False verilir; degilse
            # eski (RPM) yorum korunur.
            body = (detail or "")
            if "daily free allocation" in body or '"code":4006' in body:
                return LLMUnavailable(
                    f"Cloudflare GUNLUK NORON KOTASI tukendi (429, code 4006): {detail}\n"
                    f"  Bu bir hiz siniri DEGIL — beklemek/--pace-delay COZUM DEGIL. "
                    f"CF panosunda kota, hesabin gunluk sifirlanma saatinde acilir; "
                    f"o zamana kadar Workers AI'ye giden HER istek bu hatayi verir.",
                    retryable=False, retry_after=retry_after,
                )
            return LLMUnavailable(
                f"Cloudflare istek hizi siniri (429): {detail}\n"
                f"  Bu GUNLUK KOTA degil, dakikalik istek hizi — CF panosunda "
                f"neuron tuketimi gorunmemesi normaldir (istek hic calismadi).\n"
                f"  Cozum: --pace-delay 1.0 (ya da 2.0) ile aralik koy; "
                f"buyuk kosularda --rest-every 100 --rest-seconds 30 ekle.",
                retryable=True, retry_after=retry_after,
            )
        return exc

    def __init__(self, model: str | None = None, *, api_key: str | None = None, base_url: str | None = None, **opts):
        # OpenAICompatibleProvider.__init__ atlanir: o `default_base_url`i
        # oldugu gibi kullanir, ama Cloudflare'de hesap ID'si URL'in bir
        # PARCASI (`/accounts/<id>/ai/v1`) — once account_id cozulup base_url'e
        # gomulmesi, SONRA taban sinifa gecirilmesi gerekir.
        account_id = resolve_setting("cloudflare", "account_id", ("CF_ACCOUNT_ID",))
        self._account_id = account_id
        default_base = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
            if account_id else ""
        )
        super().__init__(model, api_key=api_key, base_url=base_url or default_base, **opts)

    def preflight(self) -> None:
        if not self._account_id:
            raise LLMUnavailable(
                "CF_ACCOUNT_ID tanimli degil. Cloudflare Workers AI icin "
                "CF_ACCOUNT_ID + CF_API_TOKEN gerekir (embed-sync/embed-apply ile "
                "AYNI ortam degiskenleri) — .env dosyasina ekleyin ya da ortamda export edin."
            )
        super().preflight()
