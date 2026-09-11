"""
`cloze`in İLAN EDİLMİŞ okuma yüzeyi — İş 6'nın katkı seam'i (`APP.sentences`)
üzerinden başka bir app'e (`grammar`) sunulan TEK şey.

`lexicon_card/public.py`nin ikizi: dışarıya SenseView yerine SentenceGroup
döner, `owner="cloze"` sabittir. Reddedilmiş ya da hiç üretilmemiş paketin
cümlesi HİÇ dönmez — yalnızca ONAYLI `sense_cloze` paketleri sunulur.

`ref = "<stable_key>:<seq>"`, `text` onaylı sorunun TAM cümlesidir (boşluk
gösterimde basılıdır, burada değil). `focus_word`/`focus_pos` hedef kelime
ve türüdür — kural seçimini yönlendirmez, yalnızca bağlam olarak taşınır.

SALT OKUNUR: burada yazma API'si YOKTUR.
"""

from __future__ import annotations

from polyvo.core.cli.app import SentenceGroup, SentenceRef, SentenceSource
from polyvo.modules.cloze.rationale import units as rationale_units

OWNER = "cloze"


def sentence_groups(tag: str, l2: str) -> list[SentenceGroup]:
    """Onaylı her cloze paketi için bir `SentenceGroup` (anlam başına üç
    cümle). `rationale/units.py::load_units` ile AYNI sorguyu kullanır —
    bu işin "hangi cümle onaylı" tanımı tek yerde kalsın diye."""
    groups: list[SentenceGroup] = []
    for unit in rationale_units.load_units(tag, l2):
        headword = unit.data["headword"]
        pos = unit.data["pos"]
        cefr = unit.data.get("cefr")
        refs = tuple(
            SentenceRef(
                ref=f"{unit.key}:{question['seq']}",
                text=question["sentence"],
                cefr=cefr,
                focus_word=headword,
                focus_pos=pos,
            )
            for question in unit.data["questions"]
        )
        groups.append(SentenceGroup(group_key=unit.key, sentences=refs))
    return groups


#: Diğer app'lerin `discovery.find_apps()` ile bulacağı ilan.
SENTENCES = SentenceSource(owner=OWNER, loader=sentence_groups)
