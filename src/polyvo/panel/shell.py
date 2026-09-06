"""
Panelin kabugu — gezinme cubugu SAYFALARDAN turer, elle yazilmaz.

Stil ve HTML burada bilerek kucuk tutuldu: panel bir urun yuzeyi degil,
odenmis deponun gozle bakilabilen halidir.
"""

from __future__ import annotations

import html

CSS = """
:root { color-scheme: light dark; }
body { margin: 0; font: 15px/1.5 system-ui, sans-serif; }
header { padding: .7rem 1rem; border-bottom: 1px solid #8883; display: flex;
         gap: 1rem; align-items: baseline; flex-wrap: wrap; }
header b { font-size: 1.05rem; }
nav a { margin-right: .9rem; text-decoration: none; }
nav a.active { font-weight: 600; text-decoration: underline; }
main { padding: 1rem; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #8883;
         vertical-align: top; }
th { font-weight: 600; white-space: nowrap; }
code, .key { font-family: ui-monospace, monospace; font-size: .9em; }
.muted { opacity: .65; }
.tag { border: 1px solid #8886; border-radius: 4px; padding: 0 .35rem;
       font-size: .8em; white-space: nowrap; }
form.filters { margin-bottom: 1rem; display: flex; gap: .5rem; flex-wrap: wrap; }
input, select { padding: .3rem .4rem; }
"""


def escape(value) -> str:
    """HTML'e guvenle gomulebilen metin (None -> bos)."""
    return html.escape("" if value is None else str(value))


def nav(pages, active_prefix: str | None) -> str:
    """Sayfa listesinden gezinme cubugunu uretir."""
    links = ['<a href="/"%s>Panel</a>' % (
        ' class="active"' if active_prefix is None else "")]
    for page in pages:
        classes = ' class="active"' if page.prefix == active_prefix else ""
        suffix = "" if page.connected else ' <span class="muted">(bagli degil)</span>'
        links.append(f'<a href="{escape(page.prefix)}"{classes}>'
                     f'{escape(page.title)}</a>{suffix}')
    return "<nav>" + "".join(links) + "</nav>"


def render(pages, active_prefix: str | None, title: str, body: str) -> str:
    """Tam sayfayi (kabuk + govde) uretir."""
    return (
        "<!doctype html><html lang=\"tr\"><head><meta charset=\"utf-8\">"
        f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{escape(title)} · Polyvo</title><style>{CSS}</style></head>"
        f"<body><header><b>Polyvo</b>{nav(pages, active_prefix)}</header>"
        f"<main>{body}</main></body></html>"
    )


def index(pages) -> str:
    """Kok sayfa: hangi app hangi sayfayi getirmis."""
    if not pages:
        return ("<p>Hicbir app panel sayfasi getirmiyor. Panel bir sayfa "
                "listesi TUTMAZ; sayfalar app'lerin <code>APP.panel</code> "
                "alanindan gelir.</p>")
    # Kacis dizisi f-string ifadesine GIRMEZ (3.11 uyumu): once degiskene alinir.
    cells = []
    for page in pages:
        state = "bagli" if page.connected else '<span class="muted">router yok</span>'
        cells.append(
            f'<tr><td><a href="{escape(page.prefix)}">{escape(page.title)}</a></td>'
            f'<td class="key">{escape(page.app_name)}</td>'
            f'<td class="key">{escape(page.prefix)}</td>'
            f'<td>{state}</td></tr>')
    rows = "".join(cells)
    return ("<p class=\"muted\">Bu liste app kesfinden gelir; panelde sabit "
            "sayfa listesi yoktur.</p>"
            "<table><tr><th>sayfa</th><th>app</th><th>onek</th><th>durum</th></tr>"
            f"{rows}</table>")
