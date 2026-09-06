"""
Ingestor sozlesmesi — bir kaynak = bir dosya, merkezi liste yok. Yeni kaynak
eklemek: `sources.py`'ye bir satir + bu klasore bir dosya.

Bir ingestor IKI bagimsiz sey uretir: `candidates()` (evrene aday, tier=None
ise bos doner) ve `evidence()` (LLM'e kanit, ogrenciye dogrudan gitmez).
Ikisi de TEMBEL olmali (generator) — buyuk kaynaklar hep bellege alinmaz.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable, Protocol, runtime_checkable

from polyvo.core import paths
from polyvo.dictionary import sources


@dataclass
class Candidate:
    """Evrene aday bir `(headword, pos)` cifti.

    `pos` None olabilir (K7): NGSL/TSL/BSL/New Dolch POS tasimaz. `raw_pos`
    ham etiketi saklar — normalize edilemezse `unresolved` raporuna girer.
    """
    headword: str
    raw_pos: str | None = None
    cefr: str | None = None
    freq_rank: int | None = None


@dataclass
class Evidence:
    """LLM'e verilecek tek bir kanit parcasi."""
    headword: str
    kind: str                    # definition | example | synonym | antonym | ipa | form
    payload: str
    raw_pos: str | None = None


@runtime_checkable
class Ingestor(Protocol):
    """Bir kaynaktan aday + kanit uretmenin sozlesmesi."""
    #: `sources.SOURCES` icindeki anahtar.
    source_name: str

    def candidates(self) -> Iterable[Candidate]: ...  # aday satirlar (headword+pos+...)
    def evidence(self) -> Iterable[Evidence]: ...      # kanit satirlari (tanim/ornek/ipa/...)


@dataclass
class FileIngestor:
    """Tek bir `data/raw/` dosyasini okuyan ingestor'lar icin ortak taban."""
    source_name: str = ""
    _missing: list[str] = field(default_factory=list, init=False)

    @property
    def source(self) -> sources.Source:
        """Bu ingestor'un `sources.py`'deki kayit satiri."""
        return sources.get(self.source_name)

    def raw_path(self, filename: str | None = None) -> str:
        """`data/raw/<dosya>` tam yolu. `filename` verilmezse kaynagin
        kendi dosya adi kullanilir."""
        name = filename or self.source.filename
        if not name:
            raise ValueError(f"{self.source_name}: dosya adi tanimsiz")
        return os.path.join(paths.raw_dir(), name)

    def available(self) -> bool:
        """Kaynak dosyasi `data/raw/`'da var mi?"""
        return os.path.exists(self.raw_path())

    def candidates(self) -> Iterable[Candidate]:
        """Varsayilan: aday uretmez. Yalniz kanit veren kaynaklar bunu ezmez."""
        return ()

    def evidence(self) -> Iterable[Evidence]:
        """Varsayilan: kanit uretmez. Yalniz aday veren kaynaklar bunu ezmez."""
        return ()
