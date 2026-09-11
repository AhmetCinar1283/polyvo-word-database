"""
Duzeltilebilir HER ALANIN hangi tabloya, hangi anahtarla gittigi — TEK harita.

`apply.py` bu haritayi okur, kendisi tablo bilgisi tasimaz (buyumesin diye).
`per_l1=True` olan alan `--l1 <kod>` gerektirir (`sense_id, l1` anahtari);
`per_l1=False` olan Ingilizce icindir (`sense_id` yeterli).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    """Bir alanin duzeltmesinin hangi tabloya (yalnizca rapor/mesaj icin
    okunakli ad) ve L1'e bagli olup olmadigina dair bilgisi."""

    table: str
    per_l1: bool


#: `record.EDITABLE_FIELDS`teki HER alan burada bir karsilik bulmali —
#: `apply.py` bilinmeyen alani zaten `record.py`de erkenden reddeder.
FIELD_TARGETS: dict[str, Target] = {
    "gloss_en": Target("sense_cards", per_l1=False),
    "register": Target("sense_cards", per_l1=False),
    "examples": Target("sense_examples", per_l1=False),
    "usage_note": Target("sense_usage_note", per_l1=False),
    "gloss_l1": Target("sense_gloss_l1", per_l1=True),
    "gloss_note_l1": Target("sense_gloss_l1_note", per_l1=True),
    "definition_l1": Target("sense_translation", per_l1=True),
    "usage_note_l1": Target("sense_translation", per_l1=True),
    "examples_l1": Target("sense_translation_examples", per_l1=True),
    # Is 4: cloze AYRI BIR DOSYADADIR (`data/stores/cloze.sqlite`). `apply.py`
    # onu ATTACH ederek ayni transaction'a alir — "sorunlu tek satirda hicbir
    # satir yazilmaz" sozu iki dosyada da gecerli kalsin diye.
    "cloze": Target("sense_cloze", per_l1=False),
    "cloze_l1": Target("sense_cloze_translation", per_l1=True),
    # Is 5: cloze'un USTUNE yazar (ayni dosya, ayri tablolar).
    "cloze_rationale": Target("sense_cloze_rationale", per_l1=False),
    "cloze_rationale_l1": Target("sense_cloze_rationale_translation",
                                 per_l1=True),
    # Is 6: grammar KENDI dosyasindadir (`data/stores/grammar.sqlite`).
    # `apply.py` bunu da ATTACH eder. Grammar'in cumleleri BUGUN yalnizca
    # `cloze`dan geldigi icin (owner="cloze" sabit varsayimi, bkz. `apply.py`)
    # anahtar burada da `stable_key`dir.
    "grammar": Target("sentence_grammar_rule", per_l1=False),
    "grammar_l1": Target("sentence_grammar_rule_l1", per_l1=True),
}

#: Cloze deposuna (ayri dosya) yazan alanlar — ATTACH bunlar varsa yapilir.
CLOZE_FIELDS: frozenset[str] = frozenset({
    "cloze", "cloze_l1", "cloze_rationale", "cloze_rationale_l1"})

#: Grammar deposuna (ayri dosya) yazan alanlar — ATTACH bunlar varsa yapilir.
#: Grammar'in cumle metni de `cloze`dan geldigi icin (bkz. `apply.py`), bu
#: alanlar cloze'un da ATTACH edilmesini GEREKTIRIR.
GRAMMAR_FIELDS: frozenset[str] = frozenset({"grammar", "grammar_l1"})

#: `sense_cards` satirina DOGRUDAN dokunan alanlar — tek UPDATE'te birlikte yazilir.
CARD_FIELDS: tuple[str, ...] = tuple(
    name for name, target in FIELD_TARGETS.items() if target.table == "sense_cards")
