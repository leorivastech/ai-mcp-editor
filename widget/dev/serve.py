"""Local widget dev server: http://127.0.0.1:8001

Serves the SAME single-file HTML the MCP resource serves, plus the
window.openai mock injected first. Rebuilds from widget/src on every
request — edit, refresh, done.
"""

from __future__ import annotations

import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from server.widget_resource import build_widget_html  # noqa: E402


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        build_widget_html.cache_clear()
        body = build_widget_html(dev=True).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # quieter
        pass


if __name__ == "__main__":
    print("Widget dev server → http://127.0.0.1:8001 (Ctrl+C to stop)")
    HTTPServer(("127.0.0.1", 8001), Handler).serve_forever()
