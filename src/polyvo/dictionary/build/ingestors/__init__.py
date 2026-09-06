"""
Ingestor kesfi — sabit liste yok, `core/cli/discovery.py` ile ayni desen.

Bu paketteki her modulde `INGESTOR` degiskeni aranir. Import hatasi YUTULMAZ:
bir ingestor import edilemiyorsa bu "o kaynak yok" demek degil, kirik bir
kurulum demektir (eski repoda bir refactor 22 modulu sessizce olu birakmisti).
"""

from __future__ import annotations

import importlib
import pkgutil

from polyvo.dictionary.build.ingestors.base import (
    Candidate, Evidence, FileIngestor, Ingestor,
)

__all__ = ["Candidate", "Evidence", "FileIngestor", "Ingestor", "find_ingestors"]


def find_ingestors() -> list[Ingestor]:
    """Bu paketteki tum `INGESTOR`'lari bulur; `sources.py` sirasina gore dizer."""
    from polyvo.dictionary import sources

    found: dict[str, Ingestor] = {}
    for mod in pkgutil.iter_modules(__path__):
        if mod.name in ("base",):
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        ing = getattr(module, "INGESTOR", None)
        if ing is not None:
            found[ing.source_name] = ing

    order = list(sources.SOURCES)
    return sorted(found.values(),
                  key=lambda i: order.index(i.source_name)
                  if i.source_name in order else len(order))
