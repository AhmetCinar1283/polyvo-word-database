"""
Katman 5 — PANEL HOST.

Burada SAYFA LISTESI YOKTUR. Host, `core/cli/discovery.py`nin buldugu her
app'in `APP.panel` alanina bakar; sayfayi app'in KENDISI getirir. Yeni bir
modul eklemek bu klasordeki hicbir dosyayi degistirmeyi gerektirmez —
mimarinin sinavi budur (MIGRATION-PLAN §7).

Sayfa sozlesmesi (ordek tiplemesi; modul bu katmani IMPORT ETMEZ):

    router(path: str, query: dict[str, list[str]]) -> (status, content_type, body)

`path` sayfanin kendi onekine GORE gorelidir ("/" ile baslar), `body` metin
ya da bayt olabilir. `content_type` "text/html" ise govde bir PARCADIR ve
host onu kabuga sarar; diger tipler oldugu gibi gecer.
"""
