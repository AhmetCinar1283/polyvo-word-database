"""
Sayfanin HTML PARCASINI ureten router.

Panel katmanini IMPORT ETMEZ (demir kural: modules -> panel yukari dogrudur).
Sozlesme ordek tiplemesidir: `render(path, query) -> (status, tip, govde)`.

Salt okunur: burada tek bir yazma sorgusu yoktur. Depodan gelen metin HTML
olarak YORUMLANMAZ (`html.escape`).
"""

from __future__ import annotations

import html
from urllib.parse import quote

from polyvo.modules.cloze.panel import queries

HTML = "text/html"


def _e(value) -> str:
    """HTML'e guvenle gomulebilen metin (None -> bos)."""
    return html.escape("" if value is None else str(value))


def _first(query: dict, name: str, default: str = "") -> str:
    """Sorgu dizesinden tek deger okur."""
    values = query.get(name) or []
    return values[0].strip() if values and values[0].strip() else default


def _badge(tier, source) -> str:
    """Satirin KIMDEN geldigini gosteren kucuk etiket."""
    who = "insan" if tier == 0 else ("model" if tier == 3 else "sozluk")
    return f'<span class="tag">{_e(who)} - tier {_e(tier)} - {_e(source)}</span>'


def _variety_line() -> str:
    """Tekduzelik ozeti — kac farkli acilis kalibi kullanilmis."""
    summary = queries.variety_summary()
    if not summary["sentences"]:
        return ""
    top = " - ".join(f"{_e(pattern or '(bos)')}: {count}"
                     for pattern, count in summary["top"])
    return (f'<p class="muted">Tekduzelik: {summary["sentences"]} cumle, '
            f'{summary["distinct_openings"]} farkli acilis kalibi. '
            f'En sik: {top}</p>')


def _status_options(status: str) -> str:
    """Durum filtresinin secenekleri."""
    out = []
    for value, label in (("", "hepsi"), ("approved", "approved"),
                         ("rejected", "rejected")):
        selected = " selected" if value == status else ""
        out.append(f'<option value="{_e(value)}"{selected}>{_e(label)}</option>')
    return "".join(out)


def _row(item: dict) -> str:
    """Liste sayfasinin tek satiri."""
    link = "/cloze/sense?key=" + quote(item["stable_key"])
    if item["status"] == "approved":
        note = (f'<span class="muted">{_e(item["warnings"])}</span>'
                if item["warnings"] else "")
    else:
        note = (f'<span class="muted">(reddedildi: '
                f'{_e(item["reject_reason"])})</span>')
    return (f'<tr><td><a href="{link}">{_e(item["headword"])}</a> '
            f'<span class="muted">{_e(item["pos"])}</span></td>'
            f'<td>{item["questions"]}</td>'
            f'<td>{_e(item["status"])}</td><td>{note}</td>'
            f'<td>{_badge(item["tier"], item["source"])}</td></tr>')


def _list_page(query: dict) -> str:
    """Paket listesi sayfasi."""
    status = _first(query, "status")
    search = _first(query, "q")
    limit = _first(query, "limit", str(queries.DEFAULT_LIMIT))
    try:
        limit_value = int(limit)
    except ValueError:
        limit_value = queries.DEFAULT_LIMIT

    summary = " - ".join(f"{_e(name)}: {count}" for name, count in queries.counts())
    found = queries.list_senses(status=status or None, search=search or None,
                                limit=limit_value)
    rows = [_row(item) for item in found] or [
        '<tr><td colspan="5" class="muted">Eslesen paket yok.</td></tr>']

    return (
        f'<p class="muted">Depo: {summary or "bos"} — gosterilen {len(found)}. '
        'Bu sayfa SALT OKUNURDUR; duzeltme icin '
        '<code>polyvo review export</code>.</p>'
        + _variety_line() +
        '<form class="filters" method="get" action="/cloze">'
        f'<select name="status">{_status_options(status)}</select>'
        f'<input name="q" value="{_e(search)}" placeholder="basliga gore ara">'
        f'<input name="limit" value="{_e(limit)}" size="4">'
        '<button type="submit">Filtrele</button></form>'
        '<table><tr><th>baslik</th><th>soru</th><th>durum</th>'
        f'<th>not</th><th>kaynak</th></tr>{"".join(rows)}</table>')


def _question_block(question: dict, rationale: dict | None) -> str:
    """Tek sorunun bosluklu cumlesi + siklari (dogru cevap isaretli).

    `rationale` varsa ipucu + sik basina aciklama da gosterilir; salt
    okunur — duzeltme yolu `review`dir."""
    seq = question["seq"]
    hint = (rationale or {}).get("hints", {}).get(seq)
    reasons = (rationale or {}).get("reasons", {}).get(seq, {})

    options = []
    for opt_seq, (text, is_answer) in enumerate(question["options"], start=1):
        mark = " (dogru)" if is_answer else ""
        body = f"<b>{_e(text)}{mark}</b>" if is_answer else _e(text)
        reason = reasons.get(opt_seq)
        note = (f'<div class="muted">{_e(reason)}</div>' if reason else "")
        options.append(f"<li>{body}{note}</li>")

    hint_line = (f'<p class="muted">ipucu: {_e(hint)}</p>' if hint else "")
    return (f'<h3>{_e(question["difficulty"])}</h3>'
            f'<p>{_e(question["blanked"])}</p>'
            f'{hint_line}'
            f'<ul>{"".join(options)}</ul>'
            f'<p class="muted">tam cumle: {_e(question["sentence"])}</p>')


def _rationale_summary(rationale: dict | None) -> str:
    """Ipucu/aciklama paketinin durum satiri; paket yoksa bos."""
    if rationale is None:
        return '<p class="muted">Ipucu/aciklama paketi yok.</p>'
    stale = ' <span class="tag">BAYAT — soru degisti</span>' if rationale["stale"] else ""
    if rationale["status"] != "approved":
        return (f'<p class="muted">Ipucu/aciklama reddedildi: '
                f'{_e(rationale["reject_reason"])}</p>')
    return (f'<p class="muted">Ipucu/aciklama: {_e(rationale["status"])} '
            f'{_badge(rationale["tier"], rationale["source"])}{stale}</p>')


def _rationale_translations(rationale: dict | None) -> str:
    """Ipucu/aciklama cevirilerinin dil basina durum satirlari."""
    if not rationale or not rationale["translations"]:
        return '<tr><td colspan="2" class="muted">-</td></tr>'
    rows = []
    for l1, info in sorted(rationale["translations"].items()):
        stale = ' <span class="tag">BAYAT</span>' if info["stale"] else ""
        rows.append(f'<tr><td>{_e(l1)}</td>'
                    f'<td>{_e(info["status"])}{stale}</td></tr>')
    return "".join(rows)


def _detail_page(query: dict) -> tuple[int, str]:
    """Tek anlamin paket sayfasi; (status, govde) doner."""
    key = _first(query, "key")
    if not key:
        return 400, '<p>Anahtar verilmedi (<code>?key=en:run:verb</code>).</p>'
    found = queries.package(key)
    if found is None:
        return 404, f'<p>Bu anahtarla cloze paketi yok: <code>{_e(key)}</code></p>'

    rows = [
        ("anahtar", f'<code>{_e(found["stable_key"])}</code>'),
        ("durum", f'{_e(found["status"])} {_badge(found["tier"], found["source"])}'),
        ("model", f'<code>{_e(found["model"] or "-")}</code>'),
        ("uyarilar", _e(found["warnings"]) or "-"),
        ("guncellenme", _e(found["updated_at"])),
    ]
    if found["reject_reason"]:
        rows.insert(2, ("red sebebi", f'<code>{_e(found["reject_reason"])}</code>'))
    table = "".join(f"<tr><th>{name}</th><td>{value}</td></tr>"
                    for name, value in rows)

    rationale = found["rationale"]
    blocks = "".join(_question_block(q, rationale) for q in found["questions"]) or (
        '<p class="muted">Soru yok (reddedilmis pakette icerik yazilmaz).</p>')

    translations = "".join(
        f'<tr><td>{_e(l1)}</td><td>{"<br>".join(_e(s) for s in sentences)}</td></tr>'
        for l1, sentences in sorted(found["translations"].items())) or (
        '<tr><td colspan="2" class="muted">-</td></tr>')

    return 200, (
        f'<h2>{_e(found["headword"])} '
        f'<span class="muted">{_e(found["pos"])}</span></h2>'
        f'<table>{table}</table>'
        f'{_rationale_summary(rationale)}'
        f'{blocks}'
        '<h3>Ceviriler</h3><table><tr><th>dil</th><th>cumleler</th></tr>'
        f'{translations}</table>'
        '<h3>Ipucu/aciklama cevirileri</h3>'
        '<table><tr><th>dil</th><th>durum</th></tr>'
        f'{_rationale_translations(rationale)}</table>'
        '<p><a href="/cloze">listeye don</a></p>')


def render(path: str, query: dict) -> tuple[int, str, str]:
    """Sayfa sozlesmesi: yolu karsilar, HTML parcasi doner."""
    if path in ("/", ""):
        return 200, HTML, _list_page(query)
    if path == "/sense":
        status, body = _detail_page(query)
        return status, HTML, body
    return 404, HTML, f'<p>Bu sayfada boyle bir yol yok: <code>{_e(path)}</code></p>'
