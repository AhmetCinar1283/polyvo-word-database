"""
Panel sayfasi — app kendi sayfasini KENDI getirir; host bir sayfa listesi
tutmaz. `router` panel katmanini import ETMEZ, ordek tiplemesiyle baglanir:

    router(path, query) -> (status, "text/html", govde_parcasi)
"""

from polyvo.core.cli.app import PanelPage
from polyvo.modules.lexicon_card.panel import views

PAGE = PanelPage(prefix="/lexicon-card", title="Sozluk kartlari",
                 router=views.render, order=10)
