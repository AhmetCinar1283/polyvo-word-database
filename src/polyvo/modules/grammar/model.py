"""
Bu app'in sabitleri — varsayilan saglayici/model + kural sayisi sozlesmesi.

`cloze/model.py` deseni: app'ler arasi import yasak oldugu icin kendi
varsayilanini ilan eder, baskasininkini import etmez.
"""

from __future__ import annotations

DEFAULT_PROVIDER = "cloudflare"
DEFAULT_MODEL = "@cf/qwen/qwen3-30b-a3b-fp8"

#: Cumle basina en cok/en az kural (Is 6 §10). `rank` 1..N BOSLUKSUZ olmali.
MAX_RULES_PER_SENTENCE = 3
MIN_RULES_PER_SENTENCE = 1

#: Cumleye ozel notun uzunluk bandi — kuralin GENEL tanimi DEGIL, yalnizca
#: "bu cumlede nasil gorundugu" (Is 6 §12). Cok kisa not bir sey acmaz, cok
#: uzun not katalogdaki `short_en`i tekrar yaziyor demektir.
NOTE_MIN_CHARS = 8
NOTE_MAX_CHARS = 240
