"""
BAYATLIK sozlesmesinin deterministik hash'leri — `cloze/rationale/
fingerprint.py` ile AYNI desen.

`source_sha256`: bir grubun cumlelerinin O ANKI metninden. `store.py::
load_existing` bunu YENIDEN hesaplayip depodakiyle karsilastirir; tutmayan
satir BAYATTIR ve donen sozluge hic konmaz — motora tek satir dokunulmaz.

`note_sha256`: cumleye ozel notun ceviri kaynagi (Ingilizce not metni).
`catalog_sha256`: katalog aciklamasinin ceviri kaynagi (`name_en`+`short_en`).
"""

from __future__ import annotations

import hashlib

from polyvo.core.text import qa as text_qa
from polyvo.modules.grammar.catalog import GrammarRule

#: Parcalari ayiran isaret — normalize metnin kendisinde gecmez.
_SEP = "␟"


def _digest(parts: list[str]) -> str:
    """Normalize edilmis parcalarin sha256'si, SABIT sirayla birlestirilmis."""
    return hashlib.sha256(_SEP.join(parts).encode("utf-8")).hexdigest()


def source_sha256(sentences: list[str]) -> str:
    """Bir grubun cumlelerinin (SABIT sirayla — cagiran verir) deterministik
    ozeti."""
    return _digest([text_qa.normalized_hash_text(s) for s in sentences])


def note_sha256(notes: list[tuple[str, int, str]]) -> str:
    """Bir grubun kural notlarinin ozeti — `(ref, rank, note)` ucluleri,
    `(ref, rank)`a gore SIRALANIR (cagiranin verdigi sira onemli degildir).
    Grup birden fazla cumle tasidigi icin `rank` TEK BASINA anahtar DEGILDIR
    (her cumle kendi 1..N sirasini tekrar eder)."""
    ordered = sorted(notes, key=lambda item: (item[0], item[1]))
    return _digest([text_qa.normalized_hash_text(note)
                    for _ref, _rank, note in ordered])


def catalog_sha256(rule: GrammarRule) -> str:
    """Bir katalog satirinin (isim + kisa aciklama) ceviri KAYNAGININ ozeti."""
    return _digest([text_qa.normalized_hash_text(rule.name_en),
                    text_qa.normalized_hash_text(rule.short_en)])
