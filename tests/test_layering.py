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
            names.add(node.module)
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


def test_modules_do_not_import_each_other():
    """Iki app birbirini import edemez — birinin degismesi digerini
    kirmamali. Ortak ihtiyac varsa asagi, `core/`'a iner."""
    violations = []
    for path in _python_files():
        source = _module_name(path)
        if not source.startswith("polyvo.modules."):
            continue
        own = source.split(".")[2]
        for target in _imported_names(path):
            if target.startswith("polyvo.modules.") and target.split(".")[2] != own:
                violations.append(f"{source} -> {target}")
    assert not violations, "App'ler arasi import:\n  " + "\n  ".join(violations)


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
