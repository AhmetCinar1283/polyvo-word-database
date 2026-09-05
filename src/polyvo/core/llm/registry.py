"""
LLM saglayici kayit defteri — Factory pattern.

Kayit ACIK IMPORT ile yapilir (`providers/__init__.py`), dinamik dizin
taramasi YOK: `tools/verify_pipeline.py` her modulu import ederken calisir
(`except BaseException`), bu yuzden import aninda is yapan/dosya sistemi
tarayan kod yasak (bkz. o dosyanin docstring'i).

YENI SAGLAYICI EKLEMEK: `providers/<ad>.py` icinde bir `LLMProvider` alt
sinifi yaz, `@register` ile isaretle, `providers/__init__.py`'ye bir import
satiri ekle. Baska hicbir dosyaya dokunulmaz — `--provider` secenekleri,
interaktif menu ve panel gosterimi otomatik kapsar.
"""

from __future__ import annotations

from polyvo.core.llm.base import LLMProvider

__all__ = [
    "create",
    "default_model",
    "get_provider_class",
    "label_for",
    "provider_names",
    "register",
]

_REGISTRY: dict[str, type[LLMProvider]] = {}


def register(cls: type[LLMProvider]) -> type[LLMProvider]:
    if not cls.name:
        raise ValueError(f"{cls.__name__}.name bos olamaz")
    _REGISTRY[cls.name] = cls
    return cls


def provider_names() -> list[str]:
    return sorted(_REGISTRY)


def get_provider_class(name: str) -> type[LLMProvider]:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"bilinmeyen provider: {name!r} (kayitli: {', '.join(provider_names())})"
        ) from None


def create(name: str, model: str | None = None, **opts) -> LLMProvider:
    return get_provider_class(name)(model=model, **opts)


def default_model(name: str) -> str:
    return get_provider_class(name).default_model


def label_for(name: str, model: str) -> str:
    """`model_label()`in registry karsiligi — cache anahtarindaki etiket."""
    return f"{get_provider_class(name).label_prefix}{model}"
