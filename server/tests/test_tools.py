"""End-to-end MCP tests: an in-process FastMCP client exercises every tool
and the widget resource, exactly as a host would."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastmcp import Client

from server import tools as tools_mod
from server.storage import PresetStore

GOLDEN_DIR = Path(__file__).parents[2] / "core" / "tests" / "golden"
FULL_PRESET = json.loads((GOLDEN_DIR / "full.json").read_text())
FULL_PROMPT = (GOLDEN_DIR / "full.txt").read_text()


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(tools_mod, "_store", PresetStore(tmp_path / "t.db"))


@pytest.fixture()
async def client():
    async with Client(tools_mod.mcp) as c:
        yield c


async def test_tools_are_registered(client: Client) -> None:
    names = {t.name for t in await client.list_tools()}
    assert names == {
        "open_preset_editor",
        "compile_preset",
        "save_preset",
        "list_presets",
        "get_preset",
        "delete_preset",
        "get_preset_options",
    }


async def test_open_editor_declares_widget_template(client: Client) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "open_preset_editor")
    assert tool.meta["openai/outputTemplate"] == tools_mod.WIDGET_URI


async def test_widget_resource_is_self_contained(client: Client) -> None:
    res = await client.read_resource(tools_mod.WIDGET_URI)
    html = res[0].text
    assert "PresetCompiler" in html  # compiler inlined
    assert "PresetLayouts" in html  # thumbnails inlined
    assert "#app" in html  # styles inlined
    assert "src=" not in html.split("<body")[1]  # no external scripts


async def test_compile_matches_golden(client: Client) -> None:
    result = await client.call_tool("compile_preset", {"preset": FULL_PRESET})
    assert result.structured_content["prompt"] == FULL_PROMPT


async def test_compile_rejects_invalid_preset(client: Client) -> None:
    bad = {**FULL_PRESET, "layout": "nope"}
    with pytest.raises(Exception, match="Invalid preset"):
        await client.call_tool("compile_preset", {"preset": bad})


async def test_save_list_get_delete_cycle(client: Client) -> None:
    saved = await client.call_tool(
        "save_preset", {"name": "promo dark", "preset": FULL_PRESET}
    )
    assert saved.structured_content["saved"] is True

    listed = await client.call_tool("list_presets", {})
    assert [p["name"] for p in listed.structured_content["presets"]] == ["promo dark"]

    got = await client.call_tool("get_preset", {"name_or_id": "promo dark"})
    assert got.structured_content["prompt"] == FULL_PROMPT
    assert got.structured_content["preset"]["layout"] == "diagonal"

    opened = await client.call_tool(
        "open_preset_editor", {"preset_name": "promo dark"}
    )
    assert opened.structured_content["prompt"] == FULL_PROMPT

    deleted = await client.call_tool("delete_preset", {"name_or_id": "promo dark"})
    assert deleted.structured_content["deleted"] == "promo dark"

    empty = await client.call_tool("list_presets", {})
    assert empty.structured_content["presets"] == []


async def test_open_editor_unknown_preset_errors(client: Client) -> None:
    with pytest.raises(Exception, match="No preset named"):
        await client.call_tool("open_preset_editor", {"preset_name": "ghost"})


async def test_get_preset_options(client: Client) -> None:
    result = await client.call_tool("get_preset_options", {})
    options = result.structured_content
    assert "diagonal" in options["layouts"]
    assert "center" in options["zones"]
    assert "no_watermarks" in options["restriction_presets"]
