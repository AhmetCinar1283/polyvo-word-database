"""
Panel sunucusunu kurup calistirir.

Varsayilan adres BILEREK `127.0.0.1`: panel odenmis depoyu ve heniz sevk
edilmemis icerigi gosterir, ag uzerine acilmasi ACIK bir karar olmalidir.
"""

from __future__ import annotations

from polyvo.panel import http as http_mod
from polyvo.panel import pages as pages_mod

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> int:
    """Sayfalari kesfeder, sunucuyu acar ve Ctrl+C'ye kadar calistirir."""
    pages = pages_mod.mounted_pages()
    server = http_mod.make_server(pages, host, port)
    actual = server.server_address[1]

    print(f"Panel calisiyor: http://{host}:{actual}/")
    if not pages:
        print("  (hicbir app panel sayfasi getirmiyor)")
    for page in pages:
        state = "" if page.connected else "  (router yok)"
        print(f"  {page.prefix:<18} {page.title}  [{page.app_name}]{state}")
    print("  Durdurmak icin Ctrl+C")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel durduruldu.")
    finally:
        server.server_close()
    return 0
