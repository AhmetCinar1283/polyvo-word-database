"""
NLTK korpus verisini "zaten diskte varsa ASLA aga gitme" kuraliyla hazirlar.

NEDEN VAR: `nltk.download(pkg, quiet=True)` `quiet=True` olsa bile veri zaten
diskte olsa da her cagrida nltk.org'a bir HTTP istegi atar (index/manifest
kontrolu). word_cleaner.py bu cagriyi MODUL SEVIYESINDE (import aninda) dort
kez yapiyordu, ve `universe.py` uzerinden content pipeline'inin HER
komutu (`content-sense-sync`, `content-gloss-sync`, ...) bu modulu import
ediyor — yani her tek komut calistirmasi, hic ihtiyac olmasa bile nltk.org'a
4 istek atiyordu. Kisa surede art arda birkac komut/test kosusunda bu,
nltk.org'un kendi hiz sinirina takilip `HTTP Error 429: Too Many Requests`
veriyordu — Cloudflare kotasinda HICBIR sekilde gorunmeyen, kullanicinin
"kotam kullanilmamis gibi" gozlemini tam aciklayan bir hata kaynagi.

COZUM: once `nltk.data.find(find_path)` ile YEREL diski kontrol et — bulunursa
sifir ag istegi. Sadece `LookupError` (paket gercekten yok) durumunda
`nltk.download()` cagir. Bu, `stoplist.py`'nin zaten kullandigi desenin
genellestirilmis hali.

TUZAK (olculen 2026-08-17, ilk duzeltmeyi ETKISIZ birakmisti): nltk paketleri
diske ACILMIS dizin olarak da, ACILMAMIS `.zip` olarak da kurulabilir ve
`nltk.data.find("corpora/wordnet")` ZIP formunu GORMEZ — yalnizca
`corpora/wordnet.zip` bulunur. Bu makinede wordnet ve omw-1.4 tam olarak o
durumdaydi: paket kuruluydu ama `find` "yok" diyor, kod her koşuda yeniden
indirmeye kalkiyor, nltk.org 429 veriyordu. Bu yuzden ASLA tek bir yol
sorulmaz — her zaman hem dizin hem `.zip` formu denenir. (nltk'nin kendi
`LazyCorpusLoader`i da tam olarak bunu yapar.)
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
    """Paket YERELDE kurulu mu — sifir ag istegi.

    Hem acilmis dizin (`corpora/wordnet`) hem de acilmamis arsiv
    (`corpora/wordnet.zip`) formu denenir; ikisi de gecerli bir kurulumdur.
    """
    path = find_path or _FIND_PATHS.get(resource_id, f"corpora/{resource_id}")
    for candidate in (path, f"{path}.zip"):
        try:
            nltk.data.find(candidate)
            return True
        except LookupError:
            continue
    return False


def ensure_nltk_data(resource_id: str, find_path: str | None = None, *, quiet: bool = True) -> bool:
    """`resource_id` yerelde yoksa indirir; VARSA hicbir ag istegi atmaz.

    Donen deger: paket kullanima hazir mi (yerelde bulundu ya da indirme
    basarili oldu). Ag hatasi/429 durumunda False doner, raise ETMEZ — cagiran
    taraf zaten `except Exception` ile bu durumu ele aliyor.
    """
    if is_installed(resource_id, find_path):
        return True
    try:
        return bool(nltk.download(resource_id, quiet=quiet))
    except Exception:
        return False
