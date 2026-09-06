"""
LLM saglayici/model secimi icin ortak CLI bayraklari + cozum sirasi:
CLI bayragi > interaktif soru (stdin terminal ise) > varsayilan.

Secenekler `registry.provider_names()`den turer — yeni saglayici otomatik gorunur.
"""

from __future__ import annotations

import sys

from polyvo.core.llm import registry
from polyvo.core.llm.base import LLMProvider

__all__ = ["add_llm_args", "fail", "resolve_llm_settings"]


def add_llm_args(parser, *, default_provider: str, default_model: str | None = None) -> None:
    """Saglayici/model secim bayraklarini ekler.

    `default_model` yalnizca `default_provider` ile BIRLIKTE gecerlidir: kullanici
    baska bir saglayici secerse o saglayicinin KENDI varsayilani kullanilir —
    bir saglayicinin onerdigi model baskasina SIZMAZ."""
    parser.add_argument(
        "--provider", choices=registry.provider_names(), default=None,
        help=f"LLM saglayicisi (verilmezse interaktif terminalde sorulur, aksi halde '{default_provider}')",
    )
    parser.add_argument(
        "--model", default=None,
        help="Saglayici icindeki model adi (verilmezse interaktif terminalde sorulur, "
             f"aksi halde {default_model + ' — yalniz ' + default_provider + ' icin' if default_model else 'saglayicinin varsayilani'})",
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
    parser.add_argument(
        "--max-retries", type=int, default=None,
        help="Gecici hatada (429/5xx) kac kez yeniden denensin (verilmezse saglayici varsayilani)",
    )
    parser.add_argument(
        "--no-interactive", action="store_true",
        help="Bayrak verilmeyen sagl./model icin soru sormadan varsayilana dus",
    )


def _isatty() -> bool:
    """Stdin gercek bir terminal mi (etkilesimli secici icin)."""
    return bool(sys.stdin and sys.stdin.isatty())


def _prompt_provider(default_provider: str, default_model: str | None = None) -> str:
    """Etkilesimli saglayici secici. `default_model` yalnizca `default_provider`
    satirinda gorunur — o modeli ONERMEYEN bir saglayicinin yaninda yazilmaz."""
    names = registry.provider_names()
    print("\nHangi LLM saglayicisi kullanilsin?")
    for i, n in enumerate(names, start=1):
        cls = registry.get_provider_class(n)
        note = cls.menu_note or (
            "(yerel, API anahtari gerekmez)" if not cls.needs_api_key else "(API anahtari gerekir)"
        )
        model = default_model if (n == default_provider and default_model) else cls.default_model
        print(f"  [{i}] {n:<10} {note}  varsayilan model: {model}")

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


def _prompt_model(provider_name: str, default: str | None = None) -> str:
    """Etkilesimli model secici (saglayici destekliyorsa canli liste)."""
    cls = registry.get_provider_class(provider_name)
    default = default or cls.default_model
    models = None
    try:
        # Gecici ornek, sadece canli model listesi icin (Ollama'da calisir).
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


def resolve_llm_settings(args, *, default_provider: str,
                         default_model: str | None = None) -> LLMProvider:
    """Bayrak > interaktif > varsayilan sirasiyla saglayici+model karari verir,
    ornegini olusturur. `add_llm_args` ile eslesir."""
    interactive = not args.no_interactive and _isatty()

    provider_name = args.provider
    if provider_name is None:
        provider_name = (_prompt_provider(default_provider, default_model)
                         if interactive else default_provider)

    # `default_model` yalnizca cagiranin ONERDIGI saglayiciyla eslesirse
    # gecerlidir — kullanici baskasini sectiyse o saglayicinin kendi
    # varsayilanina donulur (colab secilince cloudflare'in qwen'i sizmasin).
    suggested_model = default_model if provider_name == default_provider else None
    fallback_model = suggested_model or registry.default_model(provider_name)
    model_name = args.model
    if model_name is None:
        model_name = _prompt_model(provider_name, suggested_model) if interactive else fallback_model

    # base_url saglayicidan BAGIMSIZ gecirilir; kullanmayan saglayicilar yok sayar.
    return registry.create(
        provider_name,
        model=model_name,
        api_key=args.api_key,
        base_url=args.base_url or getattr(args, "ollama_host", None),
        max_retries=args.max_retries,
    )


def fail(exc: Exception, label: str) -> None:
    """Saglayici hatasinda tek satirlik standart cikis."""
    print(f"[{label}] {exc}", file=sys.stderr)
    sys.exit(1)
