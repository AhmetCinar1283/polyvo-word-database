"""
Panel sayfasi — app kendi sayfasini KENDI getirir; host bir sayfa listesi
tutmaz. `router` panel katmanini import ETMEZ, ordek tiplemesiyle baglanir:

    router(path, query) -> (status, "text/html", govde_parcasi)
"""

from polyvo.core.cli.app import PanelPage
from polyvo.modules.cloze.panel import views

PAGE = PanelPage(prefix="/cloze", title="Cloze sorulari",
                 router=views.render, order=20)
