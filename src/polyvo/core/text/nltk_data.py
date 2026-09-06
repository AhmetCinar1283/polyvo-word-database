"""
NLTK korpus verisini "zaten diskte varsa ASLA aga gitme" kuraliyla hazirlar.
`nltk.download(quiet=True)` veri diskte olsa bile her cagrida ag'a gidip
nltk.org'un hiz sinirine (429) takilabiliyor — once `nltk.data.find` ile
yerel diski kontrol edilir, yalnizca `LookupError`da indirilir.

TUZAK: nltk paketi acilmis dizin OLARAK da, acilmamis `.zip` OLARAK da kurulu
olabilir; `find` sadece birini gorur. Bu yuzden her ikisi de denenir.
"""

from __future__ import annotations

import nltk

# resource_id (nltk.download'a verilen ad) -> nltk.data.find yolu
_FIND_PATHS = {
    "wordnet": "corpora/wordnet",
    "names": "corpora/names",
    "stopwords": "corpora/stopwords",
    "omw-1.4": "corpora/omw-1.4",
    "swadesh": "corpora/swadesh",
}


def is_installed(resource_id: str, find_path: str | None = None) -> bool:
    """Paket YERELDE kurulu mu — sifir ag istegi (dizin ve `.zip` ikisi de denenir)."""
    path = find_path or _FIND_PATHS.get(resource_id, f"corpora/{resource_id}")
    for candidate in (path, f"{path}.zip"):
        try:
            nltk.data.find(candidate)
            return True
        except LookupError:
            continue
    return False


def ensure_nltk_data(resource_id: str, find_path: str | None = None, *, quiet: bool = True) -> bool:
    """`resource_id` yerelde yoksa indirir, varsa ag'a gitmez. Ag hatasinda
    `False` doner, raise ETMEZ."""
    if is_installed(resource_id, find_path):
        return True
    try:
        return bool(nltk.download(resource_id, quiet=quiet))
    except Exception:
        return False
