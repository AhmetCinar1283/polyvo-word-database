"""
Panelde gorunecek sayfalarin TEK toplama yeri — app kesfinden gelir.

Onek cakismasi sessizce gecmez: iki app ayni oneki isterse hangisinin
kazandigi tahmin edilemez olurdu, o yuzden hata olur.
"""

from __future__ import annotations

from dataclasses import dataclass

from polyvo.core.cli import discovery


@dataclass(frozen=True)
class MountedPage:
    """Bir app'in panele astigi sayfa + hangi app'ten geldigi."""

    app_name: str
    prefix: str
    title: str
    order: int
    router: object | None = None
    static_dir: str | None = None

    @property
    def connected(self) -> bool:
        """Sayfanin gercek bir router'i var mi (yoksa yer tutucu gosterilir)."""
        return self.router is not None


class PrefixConflict(RuntimeError):
    """Iki app ayni panel onekini istedi — kazanan TAHMIN EDILMEZ."""


def _normalize(prefix: str) -> str:
    """Oneki '/x' bicimine getirir (sondaki egik cizgi atilir)."""
    prefix = "/" + prefix.strip("/")
    return prefix


def mounted_pages(apps=None) -> list[MountedPage]:
    """Kesfedilen app'lerin panel sayfalarini `order`, sonra ada gore siralar."""
    apps = discovery.find_apps() if apps is None else apps
    pages: list[MountedPage] = []
    seen: dict[str, str] = {}
    for app in apps:
        page = getattr(app, "panel", None)
        if page is None:
            continue
        prefix = _normalize(page.prefix)
        if prefix in seen:
            raise PrefixConflict(
                f"'{prefix}' onekini iki app birden istiyor: "
                f"{seen[prefix]} ve {app.name}")
        seen[prefix] = app.name
        pages.append(MountedPage(
            app_name=app.name, prefix=prefix, title=page.title,
            order=page.order, router=page.router,
            static_dir=getattr(page, "static_dir", None)))
    return sorted(pages, key=lambda p: (p.order, p.title))


def match(pages: list[MountedPage], path: str) -> MountedPage | None:
    """Yolu tasiyan sayfayi bulur; en UZUN onek kazanir."""
    best: MountedPage | None = None
    for page in pages:
        if path == page.prefix or path.startswith(page.prefix + "/"):
            if best is None or len(page.prefix) > len(best.prefix):
                best = page
    return best
