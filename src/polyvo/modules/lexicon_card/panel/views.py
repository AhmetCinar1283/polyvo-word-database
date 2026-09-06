"""
Sayfanin HTML PARCASINI ureten router.

Panel katmanini IMPORT ETMEZ (demir kural: modules -> panel yukari dogrudur).
Sozlesme ordek tiplemesidir: `render(path, query) -> (status, tip, govde)`;
"text/html" donen govde bir parcadir, kabugu host giydirir.

Salt okunur: burada tek bir yazma sorgusu yoktur. Duzeltme `review` app'inin
isidir — panelde ikinci bir yazma yolu ACILMAZ.
"""

from __future__ import annotations

import html
from urllib.parse import quote

from polyvo.modules.lexicon_card.panel import queries

HTML = "text/html"


def _e(value) -> str:
    """HTML'e guvenle gomulebilen metin (None -> bos)."""
    return html.escape("" if value is None else str(value))


def _first(query: dict, name: str, default: str = "") -> str:
    """Sorgu dizesinden tek deger okur."""
    values = query.get(name) or []
    return values[0].strip() if values and values[0].strip() else default


def _badge(tier: int | None, source: str | None) -> str:
    """Satirin KIMDEN geldigini gosteren kucuk etiket."""
    who = "insan" if tier == 0 else ("model" if tier == 3 else "sozluk")
    return f'<span class="tag">{_e(who)} · tier {_e(tier)} · {_e(source)}</span>'


def _filters(status: str, search: str, limit: str) -> str:
    """Durum/arama/limit formu."""
    options = []
    for value, label in (("", "hepsi"), ("approved", "approved"),
                         ("rejected", "rejected")):
        selected = " selected" if value == status else ""
        options.append(f'<option value="{_e(value)}"{selected}>{_e(label)}</option>')
    return (
        '<form class="filters" method="get" action="/lexicon-card">'
        f'<select name="status">{"".join(options)}</select>'
        f'<input name="q" value="{_e(search)}" placeholder="basliga gore ara">'
        f'<input name="limit" value="{_e(limit)}" size="4">'
        '<button type="submit">Filtrele</button></form>')


def _list_page(query: dict) -> str:
    """Kart listesi sayfasi."""
    status = _first(query, "status")
    search = _first(query, "q")
    limit = _first(query, "limit", str(queries.DEFAULT_LIMIT))
    try:
        limit_value = int(limit)
    except ValueError:
        limit_value = queries.DEFAULT_LIMIT

    summary = " · ".join(f"{_e(name)}: {count}" for name, count in queries.counts())
    cards = queries.list_cards(status=status or None, search=search or None,
                               limit=limit_value)

    rows = []
    for card in cards:
        link = "/lexicon-card/card?key=" + quote(card["stable_key"])
        # Reddedilen kartin ICERIGI depoda yoktur (bilerek): gloss yerine
        # red sebebi gosterilir, yoksa satir bos gorunur ve sebebi kaybolur.
        if card["gloss_en"]:
            gloss_cell = _e(card["gloss_en"])
        elif card["reject_reason"]:
            gloss_cell = (f'<span class="muted">(reddedildi: '
                          f'{_e(card["reject_reason"])})</span>')
        else:
            gloss_cell = '<span class="muted">(yok)</span>'
        rows.append(
            f'<tr><td>{card["item_id"]}</td>'
            f'<td><a href="{link}">{_e(card["headword"])}</a> '
            f'<span class="muted">{_e(card["pos"])}</span></td>'
            f'<td>{gloss_cell}</td>'
            f'<td>{_e(card["status"])}</td>'
            f'<td>{_badge(card["tier"], card["source"])}</td></tr>')

    if not rows:
        rows.append('<tr><td colspan="5" class="muted">Eslesen kart yok.</td></tr>')

    return (
        f'<p class="muted">Depo: {summary or "bos"} — gosterilen {len(cards)}. '
        'Bu sayfa SALT OKUNURDUR; duzeltme icin '
        '<code>polyvo review export</code>.</p>'
        + _filters(status, search, limit) +
        '<table><tr><th>item</th><th>baslik</th><th>gloss (EN)</th>'
        f'<th>durum</th><th>kaynak</th></tr>{"".join(rows)}</table>')


def _detail_page(query: dict) -> tuple[int, str]:
    """Tek kartin ayrinti sayfasi; (status, govde) doner."""
    key = _first(query, "key")
    if not key:
        return 400, '<p>Anahtar verilmedi (<code>?key=en:run:verb</code>).</p>'
    card = queries.card(key)
    if card is None:
        return 404, f'<p>Bu anahtarla kart yok: <code>{_e(key)}</code></p>'

    ipa = ", ".join(f"{_e(ipa)} <span class=\"muted\">({_e(variant)}, "
                    f"{_e(source)})</span>"
                    for variant, ipa, source in card["phonetics"]) or "—"
    examples = "".join(
        f"<li>{_e(text)} {_badge(tier, source)}</li>"
        for _seq, text, tier, source in card["examples"]) or "<li>—</li>"
    glosses = "".join(
        f"<tr><td>{_e(l1)}</td><td>{_e(gloss)}</td>"
        f"<td>{_badge(tier, source)}</td></tr>"
        for l1, gloss, tier, source in card["glosses_l1"]) or (
        '<tr><td colspan="3" class="muted">—</td></tr>')
    level = card["level"]
    level_text = (f'{_e(level[0])} · sira {_e(level[1])} '
                  f'<span class="muted">({_e(level[2])})</span>') if level else "—"

    rows = [
        ("anahtar", f'<code>{_e(card["stable_key"])}</code>'),
        ("durum", f'{_e(card["status"])} {_badge(card["tier"], card["source"])}'),
        ("model", f'<code>{_e(card["model"] or "—")}</code>'),
        ("gloss (EN)", _e(card["gloss_en"]) or "—"),
        ("register", _e(card["register"]) or "—"),
        ("kullanim notu", _e(card["usage_note"]) or "—"),
        ("IPA", ipa),
        ("seviye", level_text),
        ("guncellenme", _e(card["updated_at"])),
    ]
    if card["reject_reason"]:
        rows.insert(2, ("red sebebi", f'<code>{_e(card["reject_reason"])}</code>'))

    table = "".join(f"<tr><th>{name}</th><td>{value}</td></tr>"
                    for name, value in rows)
    return 200, (
        f'<h2>{_e(card["headword"])} '
        f'<span class="muted">{_e(card["pos"])}</span></h2>'
        f'<table>{table}</table>'
        f'<h3>Ornekler</h3><ul>{examples}</ul>'
        f'<h3>L1 karsiliklari</h3><table><tr><th>dil</th><th>karsilik</th>'
        f'<th>kaynak</th></tr>{glosses}</table>'
        '<p><a href="/lexicon-card">← listeye don</a></p>')


def render(path: str, query: dict) -> tuple[int, str, str]:
    """Sayfa sozlesmesi: yolu karsilar, HTML parcasi doner."""
    if path in ("/", ""):
        return 200, HTML, _list_page(query)
    if path == "/card":
        status, body = _detail_page(query)
        return status, HTML, body
    return 404, HTML, f'<p>Bu sayfada boyle bir yol yok: <code>{_e(path)}</code></p>'
