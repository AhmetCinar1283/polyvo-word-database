"""
LLM saglayici kayit defteri (Factory). Kayit ACIK IMPORT ile (`providers/
__init__.py`), dinamik dizin taramasi YOK.

Yeni saglayici: `providers/<ad>.py`'de `LLMProvider` alt sinifi + `@register`,
`providers/__init__.py`'ye import satiri. Baska dosyaya dokunulmaz.
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
    """Bir saglayici sinifini adiyla kayit defterine ekler."""
    if not cls.name:
        raise ValueError(f"{cls.__name__}.name bos olamaz")
    _REGISTRY[cls.name] = cls
    return cls


def provider_names() -> list[str]:
    """Kayitli tum saglayici adlari."""
    return sorted(_REGISTRY)


def get_provider_class(name: str) -> type[LLMProvider]:
    """Adiyla saglayici sinifini bulur; yoksa hata."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(
            f"bilinmeyen provider: {name!r} (kayitli: {', '.join(provider_names())})"
        ) from None


def create(name: str, model: str | None = None, **opts) -> LLMProvider:
    """Adiyla bir saglayici ORNEGI kurar."""
    return get_provider_class(name)(model=model, **opts)


def default_model(name: str) -> str:
    """Bir saglayicinin varsayilan model adi."""
    return get_provider_class(name).default_model


def label_for(name: str, model: str) -> str:
    """`model_label()`in registry karsiligi — cache anahtarindaki etiket."""
    return f"{get_provider_class(name).label_prefix}{model}"
