"""
Katkı seam'i testleri — AĞ ÇAĞRISI YOK.

Ölçülen şey İş 6'nın MİMARİ sınavıdır: `grammar` hiçbir kardeş `modules/*`
paketini import ETMEZ, cümleleri yalnızca `APP.sentences` seam'inden toplar.
SAHTE bir app tanımlanır ve `grammar` onu HİÇBİR dosya değişmeden işler —
bu, "beşinci bir soru tipi tek satır değiştirmez" sözünün kanıtıdır.
"""

from __future__ import annotations

import os

import pytest

from polyvo.core import paths
from polyvo.core.cli.app import App, SentenceGroup, SentenceRef, SentenceSource
from polyvo.core.cli.discovery import find_apps
from polyvo.modules.grammar import units as grammar_units
from polyvo.modules.grammar.sentences import collect


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))
    yield


def _fake_reading_groups(tag: str, l2: str) -> list[SentenceGroup]:
    """Cloze'u hic bilmeyen, uydurma bir icerik turu."""
    return [
        SentenceGroup(
            group_key="para-1",
            sentences=(
                SentenceRef(ref="para-1:1",
                            text="The museum opens at nine every morning.",
                            cefr="A2", focus_word="opens", focus_pos="verb"),
            ),
        ),
    ]


def _fake_app() -> App:
    """`APP.sentences` ilan eden SAHTE bir app — gercek agacta YOKTUR."""
    return App(name="reading", sentences=SentenceSource(
        owner="reading", loader=_fake_reading_groups))


def test_sahte_app_grammarda_tek_satir_degismeden_isleniyor():
    """Genelligin KANITI: `grammar/units.py` sahte app'i hicbir kosulda
    ozel olarak tanimaz, yine de birim uretir."""
    units = grammar_units.load_units("t", "en", apps=[_fake_app()])
    assert len(units) == 1
    unit = units[0]
    assert unit.key == "reading|para-1"
    assert unit.data["owner"] == "reading"
    assert [s["text"] for s in unit.data["sentences"]] == [
        "The museum opens at nine every morning."]


def test_apps_olmayan_sentence_kaynagi_atlanir():
    """`APP.sentences=None` olan bir app sessizce atlanir — hata degildir."""
    no_seam_app = App(name="quiet")
    units = grammar_units.load_units("t", "en", apps=[no_seam_app, _fake_app()])
    assert len(units) == 1


def test_collect_deterministik_sirali():
    """`(owner, group_key)` sirasi — ayni girdi ayni sirayi verir."""
    apps = [_fake_app()]
    first = collect("t", "en", apps=apps)
    second = collect("t", "en", apps=apps)
    assert [(o.owner, o.group.group_key) for o in first] == \
        [(o.owner, o.group.group_key) for o in second]


def test_gercek_find_apps_clozeun_kaynagini_buluyor():
    """Gercek kesif (`discovery.find_apps`) `cloze` app'inin `APP.sentences`
    ilanini buluyor — seam gercekten BAGLI, yalnizca testte degil."""
    apps = find_apps()
    cloze_app = next(a for a in apps if a.name == "cloze")
    assert cloze_app.sentences is not None
    assert cloze_app.sentences.owner == "cloze"


def test_grammar_hicbir_kardes_modulu_import_etmiyor():
    """AST denetimi: `modules/grammar` altinda `modules/cloze` (ya da baska
    bir kardes) icin STATIK bir import YOK. Bu, seam'in tembel/dolayli degil
    GERCEKTEN kullanildiginin kaniti."""
    import ast

    root = os.path.join("src", "polyvo", "modules", "grammar")
    violations = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name_ in names:
                    if name_.startswith("polyvo.modules.") and \
                            not name_.startswith("polyvo.modules.grammar"):
                        violations.append(f"{path}: {name_}")
    assert violations == [], violations
