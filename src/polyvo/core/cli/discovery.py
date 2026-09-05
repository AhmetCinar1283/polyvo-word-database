"""
App kesfi — merkezi liste YOK.

`polyvo` altindaki paketlerde `app.py` (icinde `APP`) arar. Bulunanlar hem
CLI'a hem panele beslenir; ikisi ayni kaynagi kullandigi icin "komutu ekledim
ama panelde gorunmedi" durumu YAPISAL OLARAK imkansiz.

Import HATASI YUTULMAZ. Bir app import edilemiyorsa bu sessizce "o app yok"
demek degil, kirik bir kurulum demektir; kesif bunu adiyla birlikte bildirir
ve `--strict` ile hata koduna cevirir. (Eski repoda tam tersi olmustu: bir
refactor'den sonra 22 modul import edilemez halde kalmis, hicbir komut sikayet
etmemisti — o yuzden `verify` bugun once import ediyor.)
"""

from __future__ import annotations

import importlib
import pkgutil
import sys

from polyvo.core.cli.app import App

#: Altinda app aranacak paketler. Katman sirasina gore: CLI yardim ciktisi da
#: bu sirayi izler, yani komut listesi mimariyi gosterir.
SEARCH_PACKAGES: tuple[str, ...] = (
    "polyvo.dictionary",
    "polyvo.curriculum",
    "polyvo.modules",
    "polyvo.delivery",
    "polyvo.review",
    "polyvo.panel",
)

_errors: list[tuple[str, BaseException]] = []


def _iter_candidate_modules() -> list[str]:
    names: list[str] = []
    for pkg_name in SEARCH_PACKAGES:
        try:
            pkg = importlib.import_module(pkg_name)
        except ModuleNotFoundError:
            continue                      # henuz tasinmamis katman — normal
        except BaseException as exc:      # noqa: BLE001 — SystemExit de sayilir
            _errors.append((pkg_name, exc))
            continue
        if hasattr(pkg, "APP"):
            names.append(pkg_name)
        for mod in pkgutil.iter_modules(getattr(pkg, "__path__", [])):
            if mod.ispkg:
                names.append(f"{pkg_name}.{mod.name}.app")
            elif mod.name == "app":
                names.append(f"{pkg_name}.app")
    return names


def find_apps(*, strict: bool = False) -> list[App]:
    _errors.clear()
    apps: list[App] = []
    seen: set[str] = set()
    for module_name in _iter_candidate_modules():
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue                      # alt paketin app.py'si yok — normal
        except BaseException as exc:      # noqa: BLE001
            _errors.append((module_name, exc))
            continue
        app = getattr(module, "APP", None)
        if isinstance(app, App) and app.name not in seen:
            seen.add(app.name)
            apps.append(app)

    if _errors:
        for name, exc in _errors:
            print(f"[polyvo] APP yuklenemedi: {name} -> "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
        if strict:
            raise SystemExit(1)
    return apps


def load_errors() -> list[tuple[str, BaseException]]:
    return list(_errors)
