"""Assembles the widget into ONE self-contained HTML document.

The Apps SDK iframe is sandboxed by CSP, so nothing can be fetched from a
CDN: styles and scripts are inlined at startup from widget/src/. No build
step, no stale artifacts — the source files are the build.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

WIDGET_SRC = Path(__file__).parents[1] / "widget" / "src"

_INLINE_ORDER = ("layouts.js", "compiler.js", "editor.js")


@lru_cache(maxsize=2)
def build_widget_html(dev: bool = False) -> str:
    html = (WIDGET_SRC / "index.html").read_text()

    css = (WIDGET_SRC / "styles.css").read_text()
    html = html.replace("/*__STYLES__*/", css)

    scripts = []
    if dev:
        mock = (WIDGET_SRC.parent / "dev" / "mock-openai.js").read_text()
        scripts.append(f"<script>\n{mock}\n</script>")
    for name in _INLINE_ORDER:
        scripts.append(f"<script>\n{(WIDGET_SRC / name).read_text()}\n</script>")
    return html.replace("<!--__SCRIPTS__-->", "\n".join(scripts))
