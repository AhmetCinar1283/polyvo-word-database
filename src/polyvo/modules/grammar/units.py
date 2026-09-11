"""
Grammar isinin birimleri — `sentences.py::collect`in topladigi HER grup icin
bir birim. `Unit.key` `f"{owner}|{group_key}"` bicimindedir: `owner` KIMLIGIN
PARCASIDIR, iki app'in ayni `group_key`i ayni tabloda CAKISMAZ.
"""

from __future__ import annotations

from polyvo.core.cli.app import App
from polyvo.core.jobs.base import Unit
from polyvo.modules.grammar import fingerprint
from polyvo.modules.grammar.sentences import collect


def unit_key(owner: str, group_key: str) -> str:
    """Bir grubun depo anahtari — `store.py`/`review` da AYNI bicimi kullanir."""
    return f"{owner}|{group_key}"


def load_units(tag: str, l2: str, apps: list[App] | None = None) -> list[Unit]:
    """Her sahiplenilmis grup icin bir `Unit`. `apps` yalnizca testler icindir
    (bkz. `sentences.py::collect`)."""
    units: list[Unit] = []
    for owned in collect(tag, l2, apps=apps):
        group = owned.group
        sentences = [
            {
                "seq": seq,
                "ref": ref.ref,
                "text": ref.text,
                "cefr": ref.cefr,
                "focus_word": ref.focus_word,
                "focus_pos": ref.focus_pos,
            }
            for seq, ref in enumerate(group.sentences, start=1)
        ]
        if not sentences:
            continue                      # cumlesiz grup analiz edilemez
        units.append(Unit(
            key=unit_key(owned.owner, group.group_key),
            name=f"{owned.owner}:{group.group_key}",
            data={
                "owner": owned.owner,
                "group_key": group.group_key,
                "sentences": sentences,
                "source_sha256": fingerprint.source_sha256(
                    [s["text"] for s in sentences]),
            },
        ))
    return units
