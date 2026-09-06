"""
Insan duzeltmesinin BICIMI — satir basina bir JSON nesnesi (JSONL).

Burada uygulanan uc kural:
  * `tier`/`source`/`status` DOSYADAN OKUNMAZ. Yedekte ne yazarsa yazsin
    ice aktarma sabitleri kullanir (`apply.py`) — yoksa bir metin dosyasi
    kendini "insan karari" ilan edip yazma kapisini kandirirdi.
  * BULUNMAYAN alan dokunulmaz. Insan yalnizca gloss'u duzeltmek icin
    ornekleri yeniden yazmak zorunda kalmaz.
  * BILINMEYEN alan sessizce yok sayilmaz, satiri dusurur: `gloss_tr` diye
    bir yazim hatasi "hicbir sey olmadi"la sonuclanmamalidir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

#: Insanin degistirebilecegi alanlar. IPA ve seviye burada YOK: `item_phonetics`
#: tier sutunu tasimaz, yani yazma kapisi onu koruyamaz (v2).
EDITABLE_FIELDS: tuple[str, ...] = (
    "gloss_en", "register", "usage_note", "gloss_l1", "examples")

#: `null` yazilarak bosaltilabilen alanlar. Gloss'lar burada YOK — glosssuz
#: kart sevk edilemez, "bosalt" istegi bir duzeltme degil bir kayiptir.
NULLABLE_FIELDS: frozenset[str] = frozenset({"register", "usage_note"})

#: Dosyada bulunabilen ama KARARA GIRMEYEN alanlar (export baglam icin yazar,
#: yedek zaman damgasi ekler). Varliklari hata degildir; degerleri okunmaz.
IGNORED_FIELDS: frozenset[str] = frozenset({
    "tier", "source", "model", "status", "reject_reason",
    "item_id", "sense_id", "headword", "pos", "updated_at", "saved_at"})

KEY_FIELD = "stable_key"

#: Bir GUVEN alani degil, bir ADRES alani: `gloss_l1`in hangi dile ait oldugu.
#: Yedekte tasinir ki karisik dilli bir yedek geri oynatilabilsin.
L1_FIELD = "l1"


@dataclass
class Correction:
    """Tek bir satirin duzeltmesi: anahtar + yalnizca VERILEN alanlar."""

    stable_key: str
    values: dict[str, object] = field(default_factory=dict)
    #: Dosyada bulunup okunmayan alanlar — rapora girsin diye tutulur.
    ignored: tuple[str, ...] = ()
    #: `gloss_l1`in dili (yalnizca adres; verilmezse cagiranin dili kullanilir).
    l1: str | None = None

    def to_json(self, **extra) -> str:
        """Yedege/dosyaya yazilacak tek satirlik JSON."""
        row = {KEY_FIELD: self.stable_key, **self.values, **extra}
        return json.dumps(row, ensure_ascii=False, sort_keys=True)


def _check_value(field_name: str, value: object) -> str | None:
    """Bir alanin degerini dogrular; sorun varsa sebebini doner."""
    if value is None:
        if field_name in NULLABLE_FIELDS:
            return None
        return f"{field_name}_bos_birakilamaz"
    if field_name == "examples":
        if not isinstance(value, list) or not value:
            return "ornekler_liste_degil_ya_da_bos"
        for item in value:
            if not isinstance(item, str) or not item.strip():
                return "bos_ornek_cumle"
        return None
    if not isinstance(value, str):
        return f"{field_name}_metin_degil"
    if not value.strip():
        return f"{field_name}_bos"
    return None


def parse_line(line: str) -> tuple[Correction | None, str | None]:
    """Bir JSONL satirini `Correction`a cevirir; (kayit, sorun) doner."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None, None                      # bos satir/yorum: sessizce atlanir
    try:
        row = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"json_okunamadi: {exc.msg}"
    if not isinstance(row, dict):
        return None, "satir_bir_nesne_degil"

    key = row.get(KEY_FIELD)
    if not isinstance(key, str) or not key.strip():
        return None, f"{KEY_FIELD}_yok"

    l1 = row.get(L1_FIELD)
    if l1 is not None and (not isinstance(l1, str) or not l1.strip()):
        return None, "l1_gecersiz"

    values: dict[str, object] = {}
    ignored: list[str] = []
    for name, value in row.items():
        if name in (KEY_FIELD, L1_FIELD):
            continue
        if name in IGNORED_FIELDS:
            ignored.append(name)               # okunmaz — tier/source sabittir
            continue
        if name not in EDITABLE_FIELDS:
            return None, f"bilinmeyen_alan: {name}"
        problem = _check_value(name, value)
        if problem:
            return None, problem
        values[name] = ([v.strip() for v in value] if name == "examples"
                        else (value.strip() if isinstance(value, str) else value))

    if not values:
        return None, "duzeltilecek_alan_yok"
    return Correction(key.strip(), values, tuple(sorted(ignored)),
                      l1.strip() if isinstance(l1, str) else None), None


def parse_file(path: str) -> tuple[list[Correction], list[str]]:
    """Bir JSONL dosyasini bastan sona okur; (kayitlar, sorunlar) doner."""
    corrections: list[Correction] = []
    problems: list[str] = []
    with open(path, encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            correction, problem = parse_line(line)
            if problem:
                problems.append(f"satir {lineno}: {problem}")
            elif correction is not None:
                corrections.append(correction)
    return corrections, problems
