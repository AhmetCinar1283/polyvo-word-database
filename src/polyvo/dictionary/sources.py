"""
Kaynak kayit defteri — lisans bilgisi VERININ YANINDA yasar. `shippable=False`
kaynaktan gelen metin `data/dist/`'e sizmamali; `delivery/` Adim 6'da bu
bayragi KAPI olarak kullanir (docs/SOURCES.md §4).

TIER: evren merdivenindeki basamak (§2.1). Kelime birden cok kaynaktaysa
EN DUSUK tier kazanir.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """Bir veri kaynaginin kimligi: dosya adi + lisans + `shippable` bayragi."""
    #: `evidence.source` / `candidates.source` alanlarina yazilan kimlik.
    name: str
    title: str
    #: Evren merdiveni basamagi (1 = cekirdek). None = evren uretmez, yalniz kanit.
    tier: int | None
    license: str
    attribution: str
    #: Bu kaynaktan gelen METIN `data/dist/`'e yazilabilir mi? Olgular
    #: (frekans, CEFR etiketi, IPA) her zaman yazilabilir; bu bayrak IFADE
    #: icindir — tanim, ornek cumle, aciklama.
    shippable: bool
    #: Indirme adresi. None = elle yerlestirilir (orn. legacy_dist).
    url: str | None = None
    #: `data/raw/` altindaki hedef dosya adi.
    filename: str | None = None


#: Kaynaklar. Yeni kaynak eklemek = buraya bir satir + bir ingestor dosyasi.
#: Merkezi bir "aktif kaynaklar" listesi YOKTUR; ingestor'lar kesifle bulunur.
SOURCES: dict[str, Source] = {
    "ngsl": Source(
        name="ngsl", title="New General Service List 1.01 (+NAWL)",
        tier=1, license="CC BY-SA 4.0",
        attribution="Browne, C., Culligan, B. & Phillips, J. — newgeneralservicelist.com",
        shippable=False,
        url="https://raw.githubusercontent.com/antdurrant/word.lists/master/"
            "data-raw/list_ngsl/NGSL+1.01+with+SFI.xlsx",
        filename="ngsl_1.01_with_sfi.xlsx",
    ),
    "new_dolch": Source(
        name="new_dolch", title="New Dolch List 1.0",
        tier=1, license="CC BY-SA 4.0",
        attribution="NGSL Project — newgeneralservicelist.com",
        shippable=False,
        url="https://raw.githubusercontent.com/antdurrant/word.lists/master/"
            "data-raw/list_new_dolch/NDL_1.0_lemmatized_for_research.csv",
        filename="new_dolch_1.0.csv",
    ),
    "cefrj": Source(
        name="cefrj", title="CEFR-J Vocabulary Profile 1.5",
        tier=2, license="Serbest kullanim (ticari dahil), atif sartli",
        attribution="Tono, Y., Tokyo University of Foreign Studies — CEFR-J",
        shippable=False,
        url="https://raw.githubusercontent.com/openlanguageprofiles/"
            "olp-en-cefrj/master/cefrj-vocabulary-profile-1.5.csv",
        filename="cefrj-vocabulary-profile-1.5.csv",
    ),
    "nawl": Source(
        name="nawl", title="New Academic Word List 1.2",
        tier=3, license="CC BY-SA 4.0",
        attribution="Browne, C., Culligan, B. & Phillips, J. — newgeneralservicelist.com",
        shippable=False,
        # NGSL calisma kitabinin icinde, ayri dosya yok.
        url=None, filename="ngsl_1.01_with_sfi.xlsx",
    ),
    "tsl": Source(
        name="tsl", title="TOEIC Service List 1.1",
        tier=3, license="CC BY-SA 4.0",
        attribution="Browne, C. & Culligan, B. — newgeneralservicelist.com",
        shippable=False,
        url="https://raw.githubusercontent.com/antdurrant/word.lists/master/"
            "data-raw/list_toeic/TSL_1.1_stats.csv",
        filename="tsl_1.1.csv",
    ),
    "bsl": Source(
        name="bsl", title="Business Service List 1.01",
        tier=3, license="CC BY-SA 4.0",
        attribution="Browne, C. & Culligan, B. — newgeneralservicelist.com",
        shippable=False,
        url="https://raw.githubusercontent.com/antdurrant/word.lists/master/"
            "data-raw/list_business/BSL_1.01_SFI_freq_bands.csv",
        filename="bsl_1.01.csv",
    ),
    "octanove": Source(
        name="octanove", title="Octanove Vocabulary Profile C1/C2 1.0",
        tier=3, license="CC BY-SA 4.0",
        attribution="Octanove Labs — github.com/openlanguageprofiles",
        shippable=False,
        url="https://raw.githubusercontent.com/openlanguageprofiles/"
            "olp-en-cefrj/master/octanove-vocabulary-profile-c1c2-1.0.csv",
        filename="octanove-vocabulary-profile-c1c2-1.0.csv",
    ),
    "legacy_dist": Source(
        name="legacy_dist", title="Polyvo v6 sevkiyati (kanit koprusu, K4)",
        # Evren URETMEZ. Yalnizca POS cozumlemesi ve kanit saglar; hicbir
        # kelime "legacy'de vardi" diye evrene giremez (docs/SOURCES.md §3).
        tier=None, license="Kendi verimiz",
        attribution="Polyvo", shippable=False,
        url=None, filename="legacy_dist",   # klasor: core.db + en.db
    ),
    "ipa_dict": Source(
        name="ipa_dict", title="ipa-dict en_US (CMUdict turevi)",
        tier=None, license="MIT",
        attribution="open-dict-data/ipa-dict",
        # IPA bir OLGU, ifade degil — sevk edilebilir.
        shippable=True,
        url="https://raw.githubusercontent.com/open-dict-data/ipa-dict/"
            "master/data/en_US.txt",
        filename="ipa_en_US.txt",
    ),
}


def get(name: str) -> Source:
    """`name` icin kayitli `Source`'u doner; yoksa taninan adlarla birlikte hata verir."""
    if name not in SOURCES:
        raise KeyError(
            f"Bilinmeyen kaynak: {name!r}. Tanimli olanlar: "
            + ", ".join(sorted(SOURCES)))
    return SOURCES[name]


def downloadable() -> list[Source]:
    """Indirilebilir (URL'si olan) tekil dosyalar."""
    seen: set[str] = set()
    out: list[Source] = []
    for src in SOURCES.values():
        if src.url and src.filename not in seen:
            seen.add(src.filename or "")
            out.append(src)
    return out


def attribution_lines() -> list[str]:
    """`dist/ATTRIBUTION.md` icin — Adim 6 bunu kullanir."""
    return [f"- {s.title} — {s.attribution} ({s.license})"
            for s in sorted(SOURCES.values(), key=lambda s: s.name)]
