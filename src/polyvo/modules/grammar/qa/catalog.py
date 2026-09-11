"""
KATALOG kapisi — model KAPALI SOZLUKTEN secer, katalogda olmayan bir
`rule_id` UYDURULAMAZ (Is 6 §9).

Bu, `merged_into` COZUMLEMESINDEN farklidir: birlestirilmis (ham) bir id
katalogda VARDIR, dolayisiyla burada GECER — cozumleme yalnizca OKUMA
aninda (panel/export) yapilir, yazma anindaki kapi yalnizca "bu id gercekten
katalogda mi" sorusunu sorar."""

from __future__ import annotations

from polyvo.modules.grammar.catalog import get


def check(sentences: list[dict], unit) -> tuple[str | None, list[str]]:
    """Her kuralin `rule_id`si katalogda VAR MI? Yoksa TUM grup reddedilir —
    modelin `candidates` alanina yazmasi gereken sey buydu, `rules`e degil."""
    for s in sentences:
        for rule in s["rules"]:
            if get(rule["rule_id"]) is None:
                return f"rule_id_katalogda_yok: {rule['rule_id']}", []
    return None, []
