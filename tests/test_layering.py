"""
DEMIR KURAL testi: alt katman ust katmani import edemez.

Bu bir uslup tercihi degil. Eski repoda "ayrik" oldugu soylenen modul katmani
(`src/modules/kernel/engine.py`) asama katmanindan
(`src/stages/content/runner.py`) import ediyordu; sonuc, birbirinden bagimsiz
olmasi gereken iki katmanin tek bir dosyada kilitlenmesiydi. Kural yazili
degil OLCULU olsun diye bu test her adimda kosar.

Ayrica: her modul GERCEKTEN import edilebilmeli. Bu, bir refactor'dan sonra
kosulacak ilk kontroldur — eski repoda bir dosya tasima 22 modulu sessizce
olu birakmisti. `BaseException` yakalanir, cunku import aninda atilan bir
`SystemExit` de bir hatadir.
"""

from __future__ import annotations

import ast
import importlib
import os
import pkgutil

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "src", "polyvo")

#: Katman numarasi buyudukce yukari cikilir. Bir katman KENDINDEN BUYUK
#: numarali bir katmani import edemez.
LAYERS: dict[str, int] = {
    "core": 0,
    "dictionary": 1,
    "curriculum": 2,
    "modules": 3,
    "delivery": 4,
    "review": 4,
    "panel": 5,
}


def _layer_of(module_name: str) -> int | None:
    parts = module_name.split(".")
    if len(parts) < 2 or parts[0] != "polyvo":
        return None
    return LAYERS.get(parts[1])


def _python_files() -> list[str]:
    out = []
    for root, _dirs, files in os.walk(SRC):
        for name in files:
            if name.endswith(".py"):
                out.append(os.path.join(root, name))
    return out


def _module_name(path: str) -> str:
    rel = os.path.relpath(path, os.path.dirname(SRC))
    rel = rel[:-3] if rel.endswith(".py") else rel
    parts = rel.replace("\\", "/").split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_names(path: str) -> set[str]:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            # NITELIKLI ad: `from polyvo.modules.x import public` ile
            # `... import store` ayni ada dusmemeli, yoksa okuma yuzeyi
            # kurali olculemez.
            for alias in node.names:
                names.add(f"{node.module}.{alias.name}")
    return names


def test_no_upward_imports():
    violations = []
    for path in _python_files():
        source = _module_name(path)
        src_layer = _layer_of(source)
        if src_layer is None:
            continue
        for target in _imported_names(path):
            tgt_layer = _layer_of(target)
            if tgt_layer is not None and tgt_layer > src_layer:
                violations.append(f"{source} -> {target}")
    assert not violations, "Yukari dogru import (demir kural ihlali):\n  " + \
        "\n  ".join(violations)


#: Bir app'in disariya actigi TEK modul adi. Bir app baska bir app'ten
#: YALNIZCA `polyvo.modules.<app>.public` import edebilir; daha derin bir
#: import (`...store`, `...schema`) iki app'i tek dosyada kilitler.
PUBLIC_SURFACE = "public"

#: YON kurali: okuma yuzeyi tek yonludur. Yuzeyi ILAN EDEN app, onu TUKETEN
#: app'i hicbir kosulda import edemez — `public` istisnasi bu yone islemez,
#: yoksa dongu kurulur ve "yeni tur bir klasordur" sozu duser.
FORBIDDEN_APP_IMPORTS: frozenset[tuple[str, str]] = frozenset({
    ("lexicon_card", "cloze"),
})

#: Is 6: `grammar` HICBIR kardes app'i import EDEMEZ — `public` istisnasi
#: bile burada islemez (diger app'ler icin gecerli olan "public yuzeyden
#: okumak MESRU" kurali BURAYA UYGULANMAZ). Girdi `APP.sentences` KATKI
#: SEAM'inden gelir (`core/cli/app.py`), statik import DEGIL — beşinci bir
#: soru tipi eklendiginde grammar'da tek satir degismesin diye.
NO_SIBLING_IMPORT_APPS: frozenset[str] = frozenset({"grammar"})


def _app_of(module_name: str) -> str | None:
    """`polyvo.modules.<app>...` ise app adi, degilse `None`."""
    parts = module_name.split(".")
    if len(parts) >= 3 and parts[0] == "polyvo" and parts[1] == "modules":
        return parts[2]
    return None


def cross_app_violations(source_module: str, imported: set[str]) -> list[str]:
    """Bir dosyanin app'ler-arasi import ihlalleri (SAF fonksiyon).

    Testler bunu hem gercek kaynak agacinda hem UYDURMA bir import listesinde
    cagirir — bir kural, yakaladigi gosterilmeden yazili sayilmaz."""
    own = _app_of(source_module)
    if own is None:
        return []
    violations = []
    for target in sorted(imported):
        other = _app_of(target)
        if other is None or other == own:
            continue
        surface = f"polyvo.modules.{other}.{PUBLIC_SURFACE}"
        if own in NO_SIBLING_IMPORT_APPS:
            # `public` istisnasi bile islemez: bu app'ler icin HER kardes
            # importu bir ihlaldir.
            violations.append(
                f"{source_module} -> {target} (grammar hicbir kardes"
                " app'i import edemez)")
        elif (own, other) in FORBIDDEN_APP_IMPORTS:
            violations.append(f"{source_module} -> {target} (YON kurali)")
        elif not (target == surface or target.startswith(surface + ".")):
            violations.append(
                f"{source_module} -> {target} (yalnizca {surface})")
    return violations


def test_moduller_arasi_import_yalnizca_public_yuzeyden():
    """Iki app birbirinin ICINE giremez. Ortak ihtiyac ya asagi (`core/`)
    iner ya da ilan edilmis okuma yuzeyinden (`public.py`) gecer."""
    violations = []
    for path in _python_files():
        source = _module_name(path)
        if not source.startswith("polyvo.modules."):
            continue
        violations += cross_app_violations(source, _imported_names(path))
    assert not violations, ("App'ler arasi import:\n  " +
                            "\n  ".join(violations))


def test_lexicon_card_cloze_import_edemez():
    """YON kurali OLCULU olsun: denetleyici uydurma bir ihlali YAKALAR.

    Gercek agacta boyle bir satir yok; bu test kuralin kendisinin calistigini
    gosterir (yesil bir testin bos oldugu icin yesil olmadigini)."""
    tuketen = cross_app_violations(
        "polyvo.modules.cloze.units",
        {"polyvo.modules.lexicon_card.public"})
    assert tuketen == [], "public yuzeyden okumak MESRU olmaliydi"

    derin = cross_app_violations(
        "polyvo.modules.cloze.units",
        {"polyvo.modules.lexicon_card.store"})
    assert len(derin) == 1 and "public" in derin[0]

    ters = cross_app_violations(
        "polyvo.modules.lexicon_card.job",
        {"polyvo.modules.cloze.public"})
    assert len(ters) == 1 and "YON" in ters[0], (
        "lexicon_card -> cloze importu YAKALANMALIYDI")


def test_grammar_hicbir_kardes_app_import_edemez():
    """Kabul olcutu (Is 6): `grammar` icin `public` istisnasi bile ISLEMEZ.

    Denetleyici OLCULU olsun: uydurma bir `grammar -> cloze.public` importu
    YAKALANIR (diger app'ler icin MESRU olan bu yol grammar icin YASAKTIR),
    gercek agacta ise (`test_moduller_arasi_import_yalnizca_public_yuzeyden`
    zaten dogrular) hicbir ihlal yoktur."""
    uydurma = cross_app_violations(
        "polyvo.modules.grammar.units",
        {"polyvo.modules.cloze.public"})
    assert len(uydurma) == 1 and "grammar" in uydurma[0], (
        "grammar -> cloze.public importu YAKALANMALIYDI (public istisnasi"
        " grammar icin gecerli degil)")

    derin = cross_app_violations(
        "polyvo.modules.grammar.units", {"polyvo.modules.cloze.schema"})
    assert len(derin) == 1


def test_every_module_imports():
    failures = []
    for mod in pkgutil.walk_packages([SRC], prefix="polyvo."):
        try:
            importlib.import_module(mod.name)
        except BaseException as exc:            # noqa: BLE001 — SystemExit dahil
            failures.append(f"{mod.name}: {type(exc).__name__}: {exc}")
    assert not failures, "Import edilemeyen modul(ler):\n  " + "\n  ".join(failures)


def test_every_top_package_is_declared():
    """`src/polyvo/` altindaki her paket LAYERS'ta ilan edilmis olmali.
    Ilan edilmemis bir paket, yukaridaki iki testin sessizce ATLADIGI bir
    bosluktur — yani kural orada gecerli degildir ve kimse fark etmez."""
    undeclared = [
        name for name in sorted(os.listdir(SRC))
        if os.path.isdir(os.path.join(SRC, name))
        and not name.startswith(("_", "."))
        and name not in LAYERS
    ]
    assert not undeclared, (
        "Katman ilan edilmemis paket(ler): " + ", ".join(undeclared) +
        " — tests/test_layering.py::LAYERS icine ekleyin.")
