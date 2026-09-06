"""
Cloudflare Workers AI adapter — `OpenAICompatibleProvider`den turer, tek
fark hesap ID'sinin base_url'in ICINE gomulmesi (`/accounts/<id>/ai/v1`).
"""

from __future__ import annotations

from polyvo.core.env import resolve_setting
from polyvo.core.llm.base import LLMUnavailable
from polyvo.core.llm.providers.openai_compat import OpenAICompatibleProvider
from polyvo.core.llm.registry import register


@register
class CloudflareProvider(OpenAICompatibleProvider):
    """Cloudflare Workers AI'ye (OpenAI-uyumlu) istek atan saglayici."""
    name = "cloudflare"
    label_prefix = "cloudflare:"
    default_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    #: Menude numarali secenek olarak gorunen modeller (qwen-30b: lexicon_card
    #: pilotunun sabit modeli, ilk sirada; 70b bilinen bir alternatif).
    known_models = (
        "@cf/qwen/qwen3-30b-a3b-fp8",
        "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    )
    env_keys = ("CF_API_TOKEN",)
    menu_note = "(Cloudflare Workers AI — CF_ACCOUNT_ID + CF_API_TOKEN gerekir)"

    # Workers AI'de iki AYRI 429 sinir var: gunluk neuron kotasi (beklemek
    # COZUM DEGIL) ve dakikalik istek hizi (bekleyip yeniden denemek dogru).
    default_max_retries = 8
    retry_base_delay = 3.0

    # Bazi modeller (qwen3, deepseek) dusunme acikken kucuk token butcesinde
    # JSON hic donmuyor; dusunmeyen modellerde etkisi yok, o yuzden acik.
    disable_thinking = True

    def _wrap_http_error(self, code, detail, retryable, retry_after):
        """Cloudflare'a ozel ipucuyla zenginlestirilmis `LLMUnavailable` uretir."""
        exc = super()._wrap_http_error(code, detail, retryable, retry_after)
        if code == 429:
            # Govde "daily free allocation"/code 4006 tasiyorsa GERCEK gunluk
            # kota tukenmesidir (beklemek/pace-delay COZUM DEGIL); tasimiyorsa
            # dakikalik hiz siniridir (retryable).
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
        """Hesap ID'sini base_url'e gomup taban sinifi kurar."""
        account_id = resolve_setting("cloudflare", "account_id", ("CF_ACCOUNT_ID",))
        self._account_id = account_id
        default_base = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
            if account_id else ""
        )
        super().__init__(model, api_key=api_key, base_url=base_url or default_base, **opts)

    def preflight(self) -> None:
        """Hesap/anahtar bilgisi tanimli mi kontrol eder; degilse acik hata."""
        if not self._account_id:
            raise LLMUnavailable(
                "CF_ACCOUNT_ID tanimli degil. Cloudflare Workers AI icin "
                "CF_ACCOUNT_ID + CF_API_TOKEN gerekir (embed-sync/embed-apply ile "
                "AYNI ortam degiskenleri) — .env dosyasina ekleyin ya da ortamda export edin."
            )
        super().preflight()
