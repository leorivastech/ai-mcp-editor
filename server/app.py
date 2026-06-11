"""Entrypoint: streamable-HTTP MCP server (Cloud Run / Docker friendly).

The MCP endpoint is served at /mcp — that full URL (https://your-host/mcp)
is what you paste into ChatGPT when adding the connector.
"""

from __future__ import annotations

import os

from server.tools import mcp


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    mcp.run(transport="http", host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
