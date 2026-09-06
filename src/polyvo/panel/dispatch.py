"""
Yolun hangi sayfaya gidecegine karar veren SAF fonksiyon — soket yok, HTTP
sinifi yok. Testler burayi cagirir; `http.py` yalnizca bunu sunucuya baglar.

Kural: `content_type` "text/html" ise app'in dondurdugu govde bir PARCADIR
ve kabuga sarilir. Diger tipler (JSON, CSV, statik dosya) oldugu gibi gecer —
panel app'in ciktisini yeniden yorumlamaz.
"""

from __future__ import annotations

import mimetypes
import os
from urllib.parse import parse_qs, urlsplit

from polyvo.panel import pages as pages_mod
from polyvo.panel import shell

HTML = "text/html"
HTML_UTF8 = "text/html; charset=utf-8"

#: Statik dosyalarin sayfa onegine gore yolu.
STATIC_SEGMENT = "/static/"


def _body(text: str) -> bytes:
    """Metni bayta cevirir (bayt geldiyse dokunmaz)."""
    return text.encode("utf-8") if isinstance(text, str) else text


def _page_html(pages, page, title: str, body: str, status: int = 200):
    """Bir parcayi kabuga sarip yanit uclusune cevirir."""
    prefix = page.prefix if page is not None else None
    return status, HTML_UTF8, _body(shell.render(pages, prefix, title, body))


def _static(page, rest: str):
    """Sayfanin `static_dir`inden dosya servis eder; disari cikis engellenir."""
    root = os.path.abspath(page.static_dir)
    target = os.path.abspath(os.path.join(root, rest[len(STATIC_SEGMENT):]))
    if not target.startswith(root + os.sep) or not os.path.isfile(target):
        return None
    ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
    with open(target, "rb") as handle:
        return 200, ctype, handle.read()


def dispatch(pages: list, raw_path: str):
    """`(status, content_type, body_bytes)` doner. Istisna FIRLATMAZ."""
    split = urlsplit(raw_path)
    path = split.path or "/"
    if len(path) > 1:
        path = path.rstrip("/") or "/"
    query = parse_qs(split.query)

    if path == "/":
        return _page_html(pages, None, "Panel", shell.index(pages))

    page = pages_mod.match(pages, path)
    if page is None:
        return _page_html(pages, None, "Bulunamadi",
                          f"<p>Bu yolu getiren bir app yok: "
                          f"<code>{shell.escape(path)}</code></p>", status=404)

    rest = path[len(page.prefix):] or "/"

    if page.static_dir and rest.startswith(STATIC_SEGMENT):
        found = _static(page, rest)
        if found is not None:
            return found
        return _page_html(pages, page, page.title,
                          "<p>Statik dosya bulunamadi.</p>", status=404)

    if not page.connected:
        # Sayfa kendini ilan etmis ama router'ini henuz getirmemis: bu bir
        # hata degil, bir DURUMDUR — app'in geri kalani panelden bagimsiz.
        return _page_html(pages, page, page.title,
                          f"<p>'{shell.escape(page.app_name)}' bu sayfayi ilan "
                          f"ediyor ama henuz bir router getirmiyor.</p>",
                          status=501)

    try:
        status, ctype, body = page.router(rest, query)
    except Exception as exc:                       # noqa: BLE001
        # Bir app'in hatasi PANELI dusurmez; hangi app oldugu yazilir.
        return _page_html(pages, page, page.title,
                          f"<p>'{shell.escape(page.app_name)}' sayfasi hata verdi: "
                          f"<code>{shell.escape(type(exc).__name__)}: "
                          f"{shell.escape(exc)}</code></p>", status=500)

    if ctype == HTML:
        return _page_html(pages, page, page.title, body, status=status)
    return status, ctype, _body(body)
