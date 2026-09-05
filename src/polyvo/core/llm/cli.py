"""
LLM saglayici/model secimi icin ortak CLI bayraklari + cozum sirasi.

SIRA HER ZAMAN: CLI bayragi > interaktif soru > mevcut varsayilan.

  - `--provider`/`--model` verildiyse dogrudan kullanilir, hic soru sorulmaz.
  - Verilmediyse VE stdin bir terminal ise (`isatty()`, boru/CI asla takilmaz
    — desen `src/stages/build/cli.py::interactive_menu` gate'inden) numarali
    bir menu ile sorulur; Enter = komutun varsayilan saglayicisi/modeli.
  - Terminal degilse (CI, `manage.py <cmd> --help`, `--no-interactive`) hic
    soru sormadan varsayilana duser.

Boylece her `content-*` komutu ayni bayrak setini ve ayni davranisi paylasir;
onceden `provider.py::add_provider_args` (cloze/translate) ile
`paragraph_gen.py`'nin elle kopyaladigi blok arasindaki ayrisma (sabit
`choices=["ollama","gemini"]` listesi) burada ortadan kalkar — secenekler
`registry.provider_names()`den turer, yeni bir saglayici otomatik gorunur.
"""

from __future__ import annotations

import sys

from polyvo.core.llm import registry
from polyvo.core.llm.base import LLMProvider

__all__ = ["add_llm_args", "fail", "resolve_llm_settings"]


def add_llm_args(parser, *, default_provider: str) -> None:
    parser.add_argument(
        "--provider", choices=registry.provider_names(), default=None,
        help=f"LLM saglayicisi (verilmezse interaktif terminalde sorulur, aksi halde '{default_provider}')",
    )
    parser.add_argument(
        "--model", default=None,
        help="Saglayici icindeki model adi (verilmezse interaktif terminalde sorulur, "
             "aksi halde saglayicinin varsayilani)",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="Saglayicinin sunucu adresi — self-hosted/uzak saglayicilar icin "
             "(orn. Colab tuneli: --base-url https://xxx.trycloudflare.com). "
             "Normalde ortam degiskeninden gelir (COLAB_URL, OLLAMA_HOST...)",
    )
    parser.add_argument(
        "--ollama-host", default=None,
        help="--base-url'in eski adi, geriye donuk uyumluluk icin korunuyor",
    )
    parser.add_argument("--api-key", default=None, help="Saglayici API anahtari (normalde ortam degiskeninden)")
    parser.add_argument("--pace-delay", type=float, default=0.0, help="Her YENI cagridan sonra beklenecek saniye")
    parser.add_argument(
        "--max-retries", type=int, default=None,
        help="Gecici hatada (429/5xx) kac kez yeniden denensin (verilmezse saglayici varsayilani)",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Bayrak verilmeyen sagl./model icin soru sormadan varsayilana dus",
    )


def _isatty() -> bool:
    return bool(sys.stdin and sys.stdin.isatty())


def _prompt_provider(default_provider: str) -> str:
    names = registry.provider_names()
    print("\nHangi LLM saglayicisi kullanilsin?")
    for i, n in enumerate(names, start=1):
        cls = registry.get_provider_class(n)
        note = cls.menu_note or (
            "(yerel, API anahtari gerekmez)" if not cls.needs_api_key else "(API anahtari gerekir)"
        )
        print(f"  [{i}] {n:<10} {note}  varsayilan model: {cls.default_model}")

    default_idx = names.index(default_provider) + 1 if default_provider in names else 1
    while True:
        choice = input(f"\n👉 Seciminiz [Enter = {default_provider}]: ").strip()
        if not choice:
            return default_provider
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        if choice in names:
            return choice
        print(f"⚠️ Gecersiz secim, tekrar deneyin (1-{len(names)} ya da isim).")
    return default_provider  # pragma: no cover — while True yukarida doner


def _prompt_model(provider_name: str) -> str:
    cls = registry.get_provider_class(provider_name)
    default = cls.default_model
    models = None
    try:
        # Modelleri sadece secim ANINDA canli listelemek icin gecici bir
        # ornek — API anahtari gerektirmeyen saglayicilarda (Ollama) calisir,
        # digerlerinde `list_models` None doner ve serbest metne dusulur.
        models = cls(model=default).list_models()
    except Exception:
        models = None

    if models:
        print(f"\n'{provider_name}' icin bulunan modeller:")
        for i, m in enumerate(models, start=1):
            print(f"  [{i}] {m}")
        choice = input(f"\n👉 Model [Enter = {default}]: ").strip()
        if not choice:
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(models):
            return models[int(choice) - 1]
        return choice

    choice = input(f"\nModel adi [Enter = {default}]: ").strip()
    return choice or default


def resolve_llm_settings(args, *, default_provider: str) -> LLMProvider:
    """Bayrak > interaktif > varsayilan sirasiyla saglayici+model karari verir,
    ornegini olusturur. `add_llm_args` ile eslesir."""
    interactive = not args.no_interactive and _isatty()

    provider_name = args.provider
    if provider_name is None:
        provider_name = _prompt_provider(default_provider) if interactive else default_provider

    model_name = args.model
    if model_name is None:
        model_name = _prompt_model(provider_name) if interactive else registry.default_model(provider_name)

    # `base_url` SAGLAYICIDAN BAGIMSIZ gecirilir. Onceden sadece `ollama` icin
    # geciriliyordu (`--ollama-host`); bu, Ollama disindaki her self-hosted/uzak
    # saglayicinin CLI'dan adres alamamasi demekti — Colab tuneli eklenirken
    # cikti (`providers/colab.py`). Her saglayicinin __init__'i degeri kendi
    # `resolve_setting(..., explicit=...)` zincirinden gecirir, adres kullanmayan
    # saglayicilar (Gemini) yok sayar.
    return registry.create(
        provider_name,
        model=model_name,
        api_key=args.api_key,
        base_url=args.base_url or getattr(args, "ollama_host", None),
        max_retries=args.max_retries,
    )


def fail(exc: Exception, label: str) -> None:
    """Saglayici hatasinda tek satirlik standart cikis (onceki `provider.fail`)."""
    print(f"[{label}] {exc}", file=sys.stderr)
    sys.exit(1)
