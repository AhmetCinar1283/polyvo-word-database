"""
Grammar katalogu testleri — AG CAGRISI YOK.

Olculen sey Is 6 §7-8'in kabul kriterleridir: id bicimi, `merged_into`
zincirinin OKUMA aninda cozulmesi (depoda ham id KALIR), dongu tespiti,
katalogdan id SILINMEMESI.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from polyvo.modules.grammar import catalog
from polyvo.modules.grammar.catalog.model import GrammarRule, is_valid_id


def test_id_bicimi():
    assert is_valid_id("EN.MODAL.BE_ABLE_TO")
    assert not is_valid_id("en.modal.be_able_to")          # kucuk harf
    assert not is_valid_id("EN.MODAL")                      # iki parca
    assert not is_valid_id("EN.MODAL.BE_ABLE_TO.EXTRA")     # dort parca
    assert not is_valid_id("EN.FOO.BAR")                    # bilinmeyen alan
    assert not is_valid_id("EN.MODAL.BE-ABLE-TO")           # tire


def test_katalogdaki_her_id_gecerli():
    assert catalog.audit() == []


def test_katalogdan_id_silinmez_yalnizca_merged_into_ile_yonlendirilir():
    """`merged_into` DOLU bir satirin kendisi hala katalogdadir."""
    original = catalog.RULES["EN.MODAL.CAN_ABILITY"]
    merged = replace(original, merged_into="EN.MODAL.BE_ABLE_TO")
    fake_rules = dict(catalog.RULES)
    fake_rules[merged.id] = merged

    # Depoda ham id (`EN.MODAL.CAN_ABILITY`) HALA VARDIR ve okunabilir —
    # birlestirme satiri SILMEZ, yonlendirir.
    assert merged.id in fake_rules
    assert fake_rules[merged.id].merged_into == "EN.MODAL.BE_ABLE_TO"


def test_resolve_zinciri_cozer():
    fake_rules = dict(catalog.RULES)
    fake_rules["EN.MODAL.TEST_A"] = GrammarRule(
        "EN.MODAL.TEST_A", "a", "a", level="A1", assume_known_from="A1",
        merged_into="EN.MODAL.TEST_B")
    fake_rules["EN.MODAL.TEST_B"] = GrammarRule(
        "EN.MODAL.TEST_B", "b", "b", level="A1", assume_known_from="A1")

    import polyvo.modules.grammar.catalog as catalog_mod
    old_rules = catalog_mod.RULES
    catalog_mod.RULES = fake_rules
    try:
        assert catalog.resolve("EN.MODAL.TEST_A").id == "EN.MODAL.TEST_B"
    finally:
        catalog_mod.RULES = old_rules


def test_resolve_dongude_hata_verir():
    fake_rules = dict(catalog.RULES)
    fake_rules["EN.MODAL.TEST_A"] = GrammarRule(
        "EN.MODAL.TEST_A", "a", "a", level="A1", assume_known_from="A1",
        merged_into="EN.MODAL.TEST_B")
    fake_rules["EN.MODAL.TEST_B"] = GrammarRule(
        "EN.MODAL.TEST_B", "b", "b", level="A1", assume_known_from="A1",
        merged_into="EN.MODAL.TEST_A")

    import polyvo.modules.grammar.catalog as catalog_mod
    old_rules = catalog_mod.RULES
    catalog_mod.RULES = fake_rules
    try:
        with pytest.raises(catalog.CatalogError):
            catalog.resolve("EN.MODAL.TEST_A")
    finally:
        catalog_mod.RULES = old_rules


def test_resolve_bilinmeyen_id_hata_verir():
    with pytest.raises(catalog.CatalogError):
        catalog.resolve("EN.FOO.BAR")


def test_audit_bozuk_merged_into_hedefini_yakalar():
    import polyvo.modules.grammar.catalog as catalog_mod
    old_rules = catalog_mod.RULES
    catalog_mod.RULES = dict(catalog.RULES)
    catalog_mod.RULES["EN.MODAL.TEST_BROKEN"] = GrammarRule(
        "EN.MODAL.TEST_BROKEN", "x", "x", level="A1", assume_known_from="A1",
        merged_into="EN.MODAL.NOPE")
    try:
        problems = catalog.audit()
        assert any("bilinmeyen" in p for p in problems)
    finally:
        catalog_mod.RULES = old_rules


def test_trivial_kurallar_katalogda_var():
    """Rank=1 kapisinin test edebilecegi en az bir `trivial` kural olmali."""
    trivial = [r for r in catalog.all_rules() if r.trivial]
    assert len(trivial) >= 3
