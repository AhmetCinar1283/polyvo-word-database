"""
`dispatch`i `http.server`a baglayan ince katman — burada KARAR YOKTUR.

Yalnizca GET islenir: panel ODENMIS DEPOYU OKUR, yazmaz. Duzeltme yolu
`review` app'idir (export -> duzelt -> import); ikinci bir yazma yolu
acmamak bilincli bir karardir.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from polyvo.panel import dispatch as dispatch_mod


def make_handler(pages: list):
    """Verilen sayfa listesini servis eden bir handler sinifi uretir."""

    class PanelHandler(BaseHTTPRequestHandler):
        """Tek istegi `dispatch`e devreden HTTP isleyicisi."""

        server_version = "PolyvoPanel/1.0"

        def do_GET(self) -> None:               # noqa: N802 — stdlib adi
            """GET istegini yanitlar."""
            status, ctype, body = dispatch_mod.dispatch(pages, self.path)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:              # noqa: N802 — stdlib adi
            """Panel yazmaz: duzeltme `polyvo review import` ile yapilir."""
            self.send_error(405, "Panel salt okunurdur (bkz. polyvo review)")

        def log_message(self, fmt: str, *args) -> None:
            """Istek gunlugunu tek satira indirir."""
            print(f"[panel] {self.address_string()} {fmt % args}")

    return PanelHandler


def make_server(pages: list, host: str, port: int) -> ThreadingHTTPServer:
    """Sayfalari servis eden HTTP sunucusunu kurar (henuz calistirmaz)."""
    return ThreadingHTTPServer((host, port), make_handler(pages))
