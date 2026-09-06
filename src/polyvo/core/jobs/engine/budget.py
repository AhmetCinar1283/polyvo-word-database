"""
Harcama tavani — `--max-new` ile kac YENI dis cagri yapilabilecegi.

Onbellekten donen cagrilar SAYILMAZ: butce paranin tavanidir, isin degil.
Bedava donen bir cevap butceyi tuketseydi, ikinci kosu ilk kosudan daha az
is yapardi ve artimlilik bozulurdu.

Tavan dolunca kosu HATA VERMEZ, durur: kalan birimlere dokunulmaz ve bu
durum kosu sonunda acikca yazilir (`reconcile.py`). Yarim kalmis bir kosu
bir hata degil, planlanmis bir duraktir.
"""

from __future__ import annotations


class Budget:
    """`max_new` yeni dis cagriya izin veren sayac. `None` = sinirsiz."""

    def __init__(self, max_new: int | None = None):
        """Sayaci sifirdan baslatir."""
        self.max_new = max_new
        self.spent = 0

    @property
    def exhausted(self) -> bool:
        """Tavan doldu mu?"""
        return self.max_new is not None and self.spent >= self.max_new

    def charge(self, from_cache: bool) -> None:
        """Bir cagriyi isler; yalnizca onbellekten GELMEYEN cagri harcar."""
        if not from_cache:
            self.spent += 1
