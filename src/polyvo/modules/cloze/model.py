"""
Bu app'in varsayilan saglayici/modeli — TEK yer.

`lexicon_card`in sabitini import ETMEK yerine kendi varsayilanini ilan eder:
app'ler arasi import yasak (bkz. `tests/test_layering.py`). Model kalite
siralamasi (`model_quality.json`) GLOBAL kalir; burada siralama yapilmaz,
yalnizca "bu kosu hangi modele sabit" sorusu yanitlanir.

Pilot BILEREK tek modele sabittir: iki farkli modelle yarim dolmus bir depo
reddetme oranini olculemez hale getirir.
"""

from __future__ import annotations

DEFAULT_PROVIDER = "cloudflare"
DEFAULT_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"
