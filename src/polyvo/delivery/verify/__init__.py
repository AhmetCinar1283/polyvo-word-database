"""
Sevkiyat dogrulamasi — uretilen dosyalara DISARIDAN bakar.

`gate.py` yazmadan ONCE kaynagi denetler; buradaki kontroller yazildiktan
SONRA sonucu denetler. Ikisi ayni sey degildir: kapi "bu icerik gidebilir mi"
sorusunu, dogrulama "giden sey butun mu" sorusunu sorar.
"""

from polyvo.delivery.verify.checks import CheckResult, run_checks

__all__ = ["CheckResult", "run_checks"]
