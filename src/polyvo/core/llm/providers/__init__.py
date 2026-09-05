"""
Saglayici kayit noktasi — ACIK import listesi. Her satir bir saglayiciyi
`registry.py`ye kaydeder (`@register` dekoratoru modul-yukleme aninda calisir).

Yeni bir saglayici eklemek icin: `providers/<ad>.py` yaz, buraya bir import
satiri ekle. Baska hicbir dosyaya dokunma gerekmez.
"""

from polyvo.core.llm.providers import cloudflare as _cloudflare  # noqa: F401
from polyvo.core.llm.providers import colab as _colab  # noqa: F401
from polyvo.core.llm.providers import gemini as _gemini  # noqa: F401
from polyvo.core.llm.providers import ollama as _ollama  # noqa: F401
from polyvo.core.llm.providers import openai_compat as _openai_compat  # noqa: F401
