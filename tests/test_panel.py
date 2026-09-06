"""
`panel` testleri — host'un iki sozu olculur:

  1. Panel SAYFA LISTESI TUTMAZ: sayfalar app kesfinden gelir, `APP.panel`i
     olmayan app panelde gorunmez, olan app hicbir host dosyasi degismeden
     gorunur.
  2. Bir app'in eksigi ya da hatasi PANELI DUSURMEZ (router yok -> 501,
     patlayan router -> 500, ikisi de kabukla birlikte).

Soket acilmaz: `dispatch` saf bir fonksiyondur, testler onu cagirir.
"""

from __future__ import annotations

import os

import pytest

from polyvo.core import paths
from polyvo.core.cli.app import App, PanelPage
from polyvo.curriculum import schema as curriculum_schema
from polyvo.modules.lexicon_card import schema as lexicon_schema
from polyvo.modules.lexicon_card.panel import views
from polyvo.panel import dispatch, pages

WORDS = [("run", "verb", "approved", "to move fast"),
         ("gibberish", "noun", "rejected", None)]


@pytest.fixture(autouse=True)
def isolated_data_root(tmp_path, monkeypatch):
    """Tum yollari tmp'ye cevirir — gercek `data/` dizinine ASLA yazilmaz."""
    monkeypatch.setattr(paths, "data_root", lambda: str(tmp_path))


def _seed(words=WORDS):
    """Panelin okuyacagi kimlik + odenmis depoyu kurar."""
    identity = curriculum_schema.open_identity_db()
    with identity:
        identity.executemany(
            "INSERT INTO items (item_id, l2, headword, pos, stable_key)"
            " VALUES (?,?,?,?,?)",
            [(i, "en", head, pos, f"en:{head}:{pos}")
             for i, (head, pos, *_rest) in enumerate(words, start=1)])
    identity.close()

    store = lexicon_schema.open_lexicon_db()
    with store:
        for i, (head, pos, status, gloss) in enumerate(words, start=1):
            sense_id = 1000 + i
            store.execute(
                "INSERT INTO sense_cards (sense_id, item_id, stable_key,"
                " gloss_en, register, usage_note, tier, status, reject_reason,"
                " source, model) VALUES (?,?,?,?,'neutral','',3,?,?,'llm','m')",
                (sense_id, i, f"en:{head}:{pos}", gloss, status,
                 None if status == "approved" else "gloss_en_kisa"))
            if status != "approved":
                continue
            store.execute(
                "INSERT INTO sense_gloss_l1 (sense_id, l1, gloss, tier, source)"
                " VALUES (?,'tr',?,3,'llm')", (sense_id, f"{head}-tr"))
            store.execute(
                "INSERT INTO sense_examples (sense_id, seq, text, tier, source)"
                " VALUES (?,1,?,3,'llm')", (sense_id, f"{head} ornek."))
            store.execute(
                "INSERT INTO item_phonetics (item_id, variant, ipa, source)"
                " VALUES (?,'us',?,'dictionary_seed')", (i, f"/{head}/"))
    store.close()


def _page(prefix="/demo", **kwargs):
    """Test icin tek sayfali bir app listesi uretir."""
    return [App(name=kwargs.pop("app_name", "demo"),
                panel=PanelPage(prefix=prefix, title="Demo", **kwargs))]


def _get(page_list, path):
    """`dispatch`i cagirip (status, tip, metin) doner."""
    status, ctype, body = dispatch.dispatch(page_list, path)
    return status, ctype, body.decode("utf-8", "replace")


# --- Sayfa kesfi ---------------------------------------------------------

def test_sayfalar_app_kesfinden_gelir():
    """Host'ta sabit liste yok: sayfa `APP.panel`den gelir."""
    found = pages.mounted_pages()
    prefixes = [p.prefix for p in found]
    assert "/lexicon-card" in prefixes
    page = next(p for p in found if p.prefix == "/lexicon-card")
    assert page.app_name == "lexicon-card" and page.connected


def test_panel_sayfasi_olmayan_app_gorunmez():
    apps = [App(name="sessiz", help="panelsiz app")]
    assert pages.mounted_pages(apps) == []


def test_ayni_onek_iki_app_tarafindan_istenemez():
    apps = _page() + _page(app_name="digeri")
    with pytest.raises(pages.PrefixConflict):
        pages.mounted_pages(apps)


def test_sayfalar_order_sirasina_gore_dizilir():
    apps = _page(prefix="/b", order=5) + _page(prefix="/a", app_name="a", order=1)
    assert [p.prefix for p in pages.mounted_pages(apps)] == ["/a", "/b"]


# --- Yonlendirme ---------------------------------------------------------

def test_kok_sayfa_sayfalari_listeler():
    found = pages.mounted_pages()
    status, ctype, body = _get(found, "/")
    assert status == 200 and ctype.startswith("text/html")
    assert "Sozluk kartlari" in body and "/lexicon-card" in body


def test_bilinmeyen_yol_kabukla_birlikte_404_doner():
    status, _ctype, body = _get(pages.mounted_pages(), "/olmayan")
    assert status == 404 and "<nav>" in body


def test_router_getirmeyen_sayfa_paneli_dusurmez():
    """`router=None` bir hata degil, bir DURUM — 501 + aciklama."""
    found = pages.mounted_pages(_page())
    status, _ctype, body = _get(found, "/demo")
    assert status == 501 and "router" in body


def test_patlayan_router_paneli_dusurmez():
    """Bir app'in hatasi tum paneli degil, kendi sayfasini bozar."""
    def kirik(_path, _query):
        raise RuntimeError("bilerek patladi")

    found = pages.mounted_pages(_page(router=kirik))
    status, _ctype, body = _get(found, "/demo")
    assert status == 500 and "demo" in body and "RuntimeError" in body
    # Kok sayfa hala calisiyor.
    assert _get(found, "/")[0] == 200


def test_html_disi_govde_kabuga_SARILMAZ():
    """App JSON dondurebilir; panel ciktisini yeniden yorumlamaz."""
    def json_router(_path, _query):
        return 200, "application/json", '{"a": 1}'

    found = pages.mounted_pages(_page(router=json_router))
    status, ctype, body = _get(found, "/demo")
    assert status == 200 and ctype == "application/json"
    assert body == '{"a": 1}' and "<nav>" not in body


def test_statik_dosya_servis_edilir_ve_disari_cikis_engellenir(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "x.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "gizli.txt").write_text("sizmamali", encoding="utf-8")

    found = pages.mounted_pages(_page(router=lambda p, q: (200, "text/html", "x"),
                                      static_dir=str(static)))
    status, ctype, body = _get(found, "/demo/static/x.css")
    assert status == 200 and ctype == "text/css" and body == "body{}"

    status, _ctype, body = _get(found, "/demo/static/../gizli.txt")
    assert status == 404 and "sizmamali" not in body


def test_sondaki_egik_cizgi_ayni_sayfaya_gider():
    found = pages.mounted_pages()
    assert _get(found, "/lexicon-card/")[0] == _get(found, "/lexicon-card")[0]


# --- lexicon_card sayfasi ------------------------------------------------

def test_kart_listesi_depodan_okur():
    _seed()
    found = pages.mounted_pages()
    status, _ctype, body = _get(found, "/lexicon-card")
    assert status == 200
    assert "run" in body and "to move fast" in body
    assert "approved: 1" in body and "rejected: 1" in body


def test_reddedilen_kart_listede_sebebiyle_gorunur():
    """Icerigi olmayan satir bos gorunmemeli — sebebi kaybolmamali."""
    _seed()
    _status, _ctype, body = _get(pages.mounted_pages(), "/lexicon-card")
    assert "gloss_en_kisa" in body


def test_durum_filtresi_calisir():
    _seed()
    found = pages.mounted_pages()
    _status, _ctype, body = _get(found, "/lexicon-card?status=rejected")
    assert "gibberish" in body and "to move fast" not in body


def test_kart_ayrintisi_butun_parcalari_gosterir():
    _seed()
    found = pages.mounted_pages()
    status, _ctype, body = _get(found, "/lexicon-card/card?key=en%3Arun%3Averb")
    assert status == 200
    assert "to move fast" in body and "run ornek." in body
    assert "run-tr" in body and "/run/" in body


def test_olmayan_kart_404_doner():
    _seed()
    status, _ctype, _body = _get(pages.mounted_pages(),
                                 "/lexicon-card/card?key=en:yok:noun")
    assert status == 404


def test_baslik_html_olarak_YORUMLANMAZ():
    """Depodan gelen metin sayfaya ham gomulmez (XSS kapisi)."""
    _seed(words=[("<script>x</script>", "noun", "approved", "zararsiz")])
    _status, _ctype, body = _get(pages.mounted_pages(), "/lexicon-card")
    assert "<script>x</script>" not in body and "&lt;script&gt;" in body


def test_sayfa_paneli_import_ETMEZ():
    """Demir kural: modul katmani panel katmanini import edemez."""
    source = open(views.__file__, encoding="utf-8").read()
    assert "polyvo.panel" not in source
    assert os.path.basename(views.__file__) == "views.py"
