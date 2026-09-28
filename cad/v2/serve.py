#!/usr/bin/env python3
"""Static server for the CAD viewer, plus POST /snap?name=x to save a canvas PNG into out/snaps/."""
import base64
import http.server
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(ROOT), **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path != "/snap":
            self.send_error(404)
            return
        name = urllib.parse.parse_qs(u.query).get("name", ["snap"])[0].replace("/", "_")
        body = self.rfile.read(int(self.headers["Content-Length"])).decode()
        d = ROOT / "out/snaps"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.png").write_bytes(base64.b64decode(body.split(",", 1)[1]))
        self.send_response(204)
        self.end_headers()

    def log_message(self, *a):
        pass


http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1]) if len(sys.argv) > 1 else 8123), Handler).serve_forever()
