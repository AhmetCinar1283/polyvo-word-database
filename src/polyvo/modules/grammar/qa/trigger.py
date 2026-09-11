"""
TETIKLEYICI kapisi — bu isin EN GUCLU olculebilir kapisi (Is 6 §11).

Her kuralin `trigger`i cumlenin ICINDEN alinmis, BIREBIR, BITISIK bir parca
olmak ZORUNDADIR. Buyuk/kucuk harf ve bosluk normalize edilir, bunun disinda
tolerans YOKTUR — kural uydurmanin maliyeti boylece SIFIRA iner.
"""

from __future__ import annotations

import re


def _normalize(text: str) -> str:
    """Karsilastirma icin: kucuk harf + tek bosluk. Tetikleyicinin CUMLEDE
    GECIP GECMEDIGI sorusu bunun disinda hicbir esneklik TANIMAZ."""
    return re.sub(r"\s+", " ", text.strip().lower())


def check(sentences: list[dict], unit) -> tuple[str | None, list[str]]:
    """Her kuralin `trigger`i kendi cumlesinde GECIYOR MU? Gecmiyorsa TUM
    grup reddedilir — hangi cumlede oldugu red sebebine yazilir."""
    for s in sentences:
        haystack = _normalize(s["text"])
        for rule in s["rules"]:
            if _normalize(rule["trigger"]) not in haystack:
                return f"trigger_cumlede_yok: {s['ref']}", []
    return None, []
