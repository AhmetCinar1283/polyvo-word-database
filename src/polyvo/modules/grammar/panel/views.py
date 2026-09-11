"""
Sayfanin HTML PARCASINI ureten router.

Panel katmanini IMPORT ETMEZ (demir kural: modules -> panel yukari dogrudur).
Sozlesme ordek tiplemesidir: `render(path, query) -> (status, tip, govde)`.

Iki gorunum: cumleye gore (`/`, `/sentence`) ve kurala gore (`/rules`,
`/rule`). Adaylar AYRI bir gorunumdedir (`/candidates`) ve "sevk edilmez"
etiketiyle gosterilir.

Salt okunur: burada tek bir yazma sorgusu yoktur. Depodan gelen metin HTML
olarak YORUMLANMAZ (`html.escape`).
"""

from __future__ import annotations

import html
from urllib.parse import quote

from polyvo.modules.grammar.panel import queries

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


def _status_options(status: str) -> str:
    """Durum filtresinin secenekleri."""
    out = []
    for value, label in (("", "hepsi"), ("approved", "approved"),
                         ("rejected", "rejected")):
        selected = " selected" if value == status else ""
        out.append(f'<option value="{_e(value)}"{selected}>{_e(label)}</option>')
    return "".join(out)


# --- Cumleye gore -------------------------------------------------------------

def _group_row(item: dict) -> str:
    """Liste sayfasinin (cumleye gore) tek satiri."""
    link = ("/grammar/sentence?owner=" + quote(item["owner"])
           + "&group_key=" + quote(item["group_key"]))
    stale = ' <span class="tag">BAYAT</span>' if item["stale"] else ""
    if item["status"] == "approved":
        note = (f'<span class="muted">{_e(item["warnings"])}</span>'
                if item["warnings"] else "")
    else:
        note = (f'<span class="muted">(reddedildi: '
                f'{_e(item["reject_reason"])})</span>')
    return (f'<tr><td><a href="{link}">{_e(item["owner"])} / '
            f'{_e(item["group_key"])}</a>{stale}</td>'
            f'<td>{item["rules"]}</td>'
            f'<td>{_e(item["status"])}</td><td>{note}</td>'
            f'<td>{_badge(item["tier"], item["source"])}</td></tr>')


def _list_page(query: dict) -> str:
    """Cumleye gore paket listesi sayfasi."""
    status = _first(query, "status")
    limit = _first(query, "limit", str(queries.DEFAULT_LIMIT))
    try:
        limit_value = int(limit)
    except ValueError:
        limit_value = queries.DEFAULT_LIMIT

    summary = " - ".join(f"{_e(name)}: {count}" for name, count in queries.counts())
    found = queries.list_groups(status=status or None, limit=limit_value)
    rows = [_group_row(item) for item in found] or [
        '<tr><td colspan="5" class="muted">Eslesen paket yok.</td></tr>']
    n_candidates = queries.candidate_count()

    return (
        f'<p class="muted">Depo: {summary or "bos"} — gosterilen {len(found)}. '
        f'{n_candidates} SEVK EDILMEYEN aday '
        f'(<a href="/grammar/candidates">gor</a>). '
        'Bu sayfa SALT OKUNURDUR; duzeltme icin '
        '<code>polyvo review export</code>.</p>'
        '<p><a href="/grammar/rules">kurala gore gorunum</a></p>'
        '<form class="filters" method="get" action="/grammar">'
        f'<select name="status">{_status_options(status)}</select>'
        f'<input name="limit" value="{_e(limit)}" size="4">'
        '<button type="submit">Filtrele</button></form>'
        '<table><tr><th>grup</th><th>kural</th><th>durum</th>'
        f'<th>not</th><th>kaynak</th></tr>{"".join(rows)}</table>')


def _rule_line(rule) -> str:
    """Tek bir katalog kuralinin ozet satiri (adi + seviye + trivial)."""
    trivial = ' <span class="tag">trivial</span>' if rule.trivial else ""
    return (f'<code>{_e(rule.id)}</code> {_e(rule.name_en)}'
            f' <span class="muted">({_e(rule.level)})</span>{trivial}')


def _sentence_block(seq: int, sentence: dict | None, rules: list[dict],
                    candidates: list[dict]) -> str:
    """Tek cumlenin ranklanmis kurallari + adaylari."""
    text = sentence["text"] if sentence else "(cumle metni bulunamadi)"
    items = "".join(
        f'<li>rank {r["rank"]}: {_rule_line(r["catalog"]) if r["catalog"] else _e(r["rule_id"])}'
        f'<div class="muted">tetikleyici: <code>{_e(r["trigger"])}</code> '
        f'— {_e(r["note"])}</div></li>'
        for r in sorted(rules, key=lambda r: r["rank"]))
    cand_items = "".join(
        f'<li><span class="tag">aday — sevk edilmez</span> '
        f'{_e(c["proposed_name"])}: <code>{_e(c["trigger"])}</code> '
        f'<div class="muted">{_e(c["rationale"])}</div></li>'
        for c in candidates)
    return (f'<h3>cumle {seq}</h3><p>{_e(text)}</p>'
            f'<ol>{items or "<li class=\"muted\">kural yok</li>"}</ol>'
            + (f'<p class="muted">Adaylar:</p><ul>{cand_items}</ul>'
               if cand_items else ""))


def _translations_table(translations: dict) -> str:
    """Ceviri dillerinin durum satirlari."""
    if not translations:
        return '<tr><td colspan="2" class="muted">-</td></tr>'
    rows = []
    for l1, info in sorted(translations.items()):
        rows.append(f'<tr><td>{_e(l1)}</td><td>{_e(info["status"])}</td></tr>')
    return "".join(rows)


def _sentence_detail_page(query: dict) -> tuple[int, str]:
    """Tek bir grubun paket sayfasi; (status, govde) doner."""
    owner = _first(query, "owner")
    group_key = _first(query, "group_key")
    if not owner or not group_key:
        return 400, ('<p>Anahtar verilmedi '
                     '(<code>?owner=cloze&amp;group_key=en:run:verb</code>).</p>')
    found = queries.sentence_package(owner, group_key)
    if found is None:
        return 404, (f'<p>Bu anahtarla grammar paketi yok: '
                     f'<code>{_e(owner)}/{_e(group_key)}</code></p>')

    stale = ' <span class="tag">BAYAT — cumle degisti</span>' if found["stale"] else ""
    rows = [
        ("grup", f'<code>{_e(found["owner"])} / {_e(found["group_key"])}</code>'),
        ("durum", f'{_e(found["status"])} '
                  f'{_badge(found["tier"], found["source"])}{stale}'),
        ("model", f'<code>{_e(found["model"] or "-")}</code>'),
        ("uyarilar", _e(found["warnings"]) or "-"),
        ("guncellenme", _e(found["updated_at"])),
    ]
    if found["reject_reason"]:
        rows.insert(2, ("red sebebi", f'<code>{_e(found["reject_reason"])}</code>'))
    table = "".join(f"<tr><th>{name}</th><td>{value}</td></tr>"
                    for name, value in rows)

    sentences = found["sentences"]
    if sentences:
        blocks = "".join(
            _sentence_block(
                s["seq"], s,
                found["rules_by_ref"].get(s["ref"], []),
                found["candidates_by_ref"].get(s["ref"], []))
            for s in sentences)
    else:
        by_ref = found["rules_by_ref"] or found["candidates_by_ref"]
        blocks = "".join(
            _sentence_block(i, None, found["rules_by_ref"].get(ref, []),
                            found["candidates_by_ref"].get(ref, []))
            for i, ref in enumerate(sorted(by_ref), start=1)) or (
            '<p class="muted">Cumle metni bulunamadi (seam su an bu grubu '
            'sunmuyor olabilir) ve kural yok.</p>')

    return 200, (
        f'<h2>{_e(found["owner"])} / {_e(found["group_key"])}</h2>'
        f'<table>{table}</table>'
        f'{blocks}'
        '<h3>Ceviriler</h3><table><tr><th>dil</th><th>durum</th></tr>'
        f'{_translations_table(found["translations"])}</table>'
        '<p><a href="/grammar">listeye don</a></p>')


# --- Kurala gore --------------------------------------------------------------

def _rule_row(item: dict) -> str:
    """Kurala gore listenin tek satiri."""
    rule = item["rule"]
    link = "/grammar/rule?id=" + quote(rule.id)
    trivial = ' <span class="tag">trivial</span>' if rule.trivial else ""
    return (f'<tr><td><a href="{link}"><code>{_e(rule.id)}</code></a>'
            f'{trivial}</td><td>{_e(rule.name_en)}</td>'
            f'<td>{_e(rule.level)}</td><td>{item["uses"]}</td></tr>')


def _rules_page() -> str:
    """Kurala gore gorunum: katalogdaki her kural + kullanim sayisi."""
    found = queries.list_rules()
    rows = "".join(_rule_row(item) for item in found)
    return (
        '<p class="muted">Katalogdaki her kural, onayli paketlerde KAC '
        'cumlede kullanildigi ile. Bu sayfa SALT OKUNURDUR.</p>'
        '<p><a href="/grammar">cumleye gore gorunum</a></p>'
        '<table><tr><th>id</th><th>ad</th><th>seviye</th>'
        f'<th>kullanim</th></tr>{rows}</table>')


def _rule_detail_page(query: dict) -> tuple[int, str]:
    """Tek bir katalog kuralinin KULLANILDIGI TUM cumleler."""
    rule_id = _first(query, "id")
    if not rule_id:
        return 400, '<p>Kural id verilmedi (<code>?id=EN.TENSE.PRESENT_SIMPLE</code>).</p>'
    found = queries.rule_usage(rule_id)
    if found is None:
        return 404, f'<p>Katalogda boyle bir kural yok: <code>{_e(rule_id)}</code></p>'

    rule = found["rule"]
    merged = (f'<p class="muted">Bu kural <code>{_e(rule.merged_into)}</code>ye '
             f'BIRLESTIRILMIS — okuma aninda oraya cozulur.</p>'
             if rule.merged_into else "")
    trivial = ('<p class="muted">TRIVIAL: rank=1de asla gorunemez.</p>'
              if rule.trivial else "")
    rows = "".join(
        '<tr><td><a href="/grammar/sentence?owner=' + quote(u["owner"])
        + '&group_key=' + quote(u["group_key"]) + '">'
        + _e(u["owner"]) + " / " + _e(u["group_key"]) + '</a></td>'
        f'<td>{u["rank"]}</td><td><code>{_e(u["trigger"])}</code></td>'
        f'<td>{_e(u["note"])}</td></tr>'
        for u in found["usages"])

    empty_row = ('<tr><td colspan="4" class="muted">'
                'Hicbir onayli cumlede kullanilmamis.</td></tr>')
    return 200, (
        f'<h2><code>{_e(rule.id)}</code> {_e(rule.name_en)}</h2>'
        f'<p>{_e(rule.short_en)}</p>'
        f'<p class="muted">Seviye: {_e(rule.level)} — '
        f'goze carpma esigi: {_e(rule.assume_known_from)}</p>'
        f'{merged}{trivial}'
        f'<p>Kullanildigi cumleler ({len(found["usages"])}):</p>'
        '<table><tr><th>grup</th><th>rank</th><th>tetikleyici</th>'
        f'<th>not</th></tr>{rows or empty_row}</table>'
        '<p><a href="/grammar/rules">listeye don</a></p>')


# --- Adaylar --------------------------------------------------------------

def _candidates_page(query: dict) -> str:
    """SEVK EDILMEYEN aday listesi — ayri gorunum."""
    limit = _first(query, "limit", str(queries.DEFAULT_LIMIT))
    try:
        limit_value = int(limit)
    except ValueError:
        limit_value = queries.DEFAULT_LIMIT
    found = queries.candidates(limit=limit_value)
    rows = "".join(
        f'<tr><td>{_e(c["owner"])} / {_e(c["ref"])}</td>'
        f'<td>{_e(c["proposed_name"])}</td>'
        f'<td><code>{_e(c["trigger"])}</code></td>'
        f'<td>{_e(c["rationale"])}</td><td>{_e(c["status"])}</td></tr>'
        for c in found) or (
        '<tr><td colspan="5" class="muted">Aday yok.</td></tr>')
    return (
        '<p class="muted">Bunlar katalogda KARSILIGI OLMAYAN, modelin '
        'kayda deger buldugu yapilar — SEVK EDILMEZLER, hicbir cumleye '
        'kural olarak baglanmazlar. Insan katalogda yer acarsa gelecek '
        'kosuda gercek bir kural olabilirler.</p>'
        '<p><a href="/grammar">cumleye gore gorunum</a></p>'
        '<table><tr><th>grup/ref</th><th>onerilen ad</th>'
        f'<th>tetikleyici</th><th>gerekce</th><th>durum</th></tr>{rows}</table>')


def render(path: str, query: dict) -> tuple[int, str, str]:
    """Sayfa sozlesmesi: yolu karsilar, HTML parcasi doner."""
    if path in ("/", ""):
        return 200, HTML, _list_page(query)
    if path == "/sentence":
        status, body = _sentence_detail_page(query)
        return status, HTML, body
    if path == "/rules":
        return 200, HTML, _rules_page()
    if path == "/rule":
        status, body = _rule_detail_page(query)
        return status, HTML, body
    if path == "/candidates":
        return 200, HTML, _candidates_page(query)
    return 404, HTML, f'<p>Bu sayfada boyle bir yol yok: <code>{_e(path)}</code></p>'
