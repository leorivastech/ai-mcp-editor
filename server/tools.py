"""The MCP surface: 6 tools + the widget resource.

Apps SDK conventions used here:
- A tool whose result should render the widget carries
  meta["openai/outputTemplate"] pointing at the widget resource URI.
- ToolResult.structured_content is visible to BOTH the model and the widget
  (window.openai.toolOutput) — the compiled prompt goes there so ChatGPT can
  generate the image from it.
- ToolResult.meta is visible ONLY to the widget — editor-internal payloads go
  there without spending model context.
- meta["openai/widgetAccessible"] = True lets the widget itself invoke the
  tool through window.openai.callTool (Save button → save_preset).
"""

from __future__ import annotations

import os
from typing import Any, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools.tool import ToolResult
from pydantic import ValidationError

from core.compiler import compile_preset
from core.constants import (
    ART_STYLES,
    LAYOUTS,
    LIGHTING_STYLES,
    RESTRICTION_PRESETS,
    SIZE_PRESETS,
    ZONES,
)
from core.schema import Preset
from server.storage import PresetStore
from server.widget_resource import build_widget_html

WIDGET_URI = "ui://widget/preset-editor.html"

mcp = FastMCP(
    name="AI Image Preset Editor",
    instructions=(
        "Visual preset editor for AI image prompts.\n\n"
        "WORKFLOW: When the user wants to compose/design an image, call "
        "open_preset_editor — they build the preset visually (size, layout, "
        "texts, style, palette, restrictions) and the compiled prompt updates "
        "live inside the widget. The compiled prompt is deterministic: the "
        "same preset always produces the exact same prompt.\n\n"
        "GENERATING: When the user asks to generate the image (or the widget "
        "sends a follow-up message), use the compiled prompt VERBATIM with "
        "your image generation tool — do not rewrite, summarize or embellish "
        "it; determinism is the whole point.\n\n"
        "PRESETS: save_preset stores by name ('save it as promo dark'); "
        "list_presets supports natural recall ('the one I used yesterday' → "
        "sort=last_used); open_preset_editor with preset_name re-opens the "
        "editor pre-loaded for editing. If you need to build or modify a "
        "preset JSON yourself, get_preset_options lists every valid value."
    ),
)

_store: Optional[PresetStore] = None


def get_store() -> PresetStore:
    global _store
    if _store is None:
        _store = PresetStore()
    return _store


def _validate(preset: dict[str, Any]) -> Preset:
    try:
        return Preset.model_validate(preset)
    except ValidationError as exc:
        issues = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise ToolError(f"Invalid preset: {issues}") from exc


# --- widget resource ---------------------------------------------------------


@mcp.resource(
    WIDGET_URI,
    mime_type="text/html+skybridge",
    meta={
        "openai/widgetDescription": (
            "Interactive editor that composes a deterministic AI image prompt: "
            "pick size, layout, place texts on a 3x3 grid, choose style, "
            "palette and restrictions, and watch the prompt build live."
        ),
        "openai/widgetPrefersBorder": True,
        # The widget is fully self-contained (everything inlined), so the CSP
        # allows no external connections or resources at all.
        "openai/widgetCSP": {
            "connect_domains": [],
            "resource_domains": [],
        },
        "openai/widgetDomain": os.environ.get(
            "WIDGET_DOMAIN", "https://leorivastech.github.io"
        ),
    },
)
def preset_editor_widget() -> str:
    return build_widget_html()


# --- output schemas (shape of structured_content, host-facing) ---------------

_PRESET_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "description": "A preset (see get_preset_options for valid values)",
}

_PRESET_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"},
        "last_used_at": {"type": "string"},
        "layout": {"type": ["string", "null"]},
        "size": {"type": ["object", "null"]},
    },
    "required": ["id", "name", "created_at", "updated_at", "last_used_at"],
}


# --- tools -------------------------------------------------------------------


@mcp.tool(
    meta={
        "openai/outputTemplate": WIDGET_URI,
        "openai/toolInvocation/invoking": "Opening the preset editor…",
        "openai/toolInvocation/invoked": "Preset editor ready",
        "openai/widgetAccessible": True,
    },
    output_schema={
        "type": "object",
        "properties": {
            "loaded_preset_name": {
                "type": ["string", "null"],
                "description": "Name of the pre-loaded preset, if any",
            },
            "prompt": {
                "type": ["string", "null"],
                "description": "Compiled prompt of the pre-loaded preset",
            },
        },
        "required": ["loaded_preset_name", "prompt"],
    },
)
def open_preset_editor(preset_name: Optional[str] = None) -> ToolResult:
    """Open the visual preset editor in the conversation. Optionally pass
    preset_name to open it pre-loaded with a saved preset for editing."""
    preset_data: Optional[dict[str, Any]] = None
    prompt: Optional[str] = None
    if preset_name:
        record = get_store().get(preset_name)
        if record is None:
            raise ToolError(
                f"No preset named '{preset_name}'. Use list_presets to see "
                "what is saved."
            )
        preset_data = record["preset"]
        prompt = compile_preset(preset_data)

    text = (
        f"Editor opened with preset '{preset_name}' loaded."
        if preset_data
        else "Editor opened. The user composes the preset visually; the "
        "compiled prompt updates live inside the widget."
    )
    return ToolResult(
        content=text,
        structured_content={
            "loaded_preset_name": preset_name,
            "prompt": prompt,
        },
        meta={"preset": preset_data},
    )


@mcp.tool(
    name="compile_preset",
    annotations={"readOnlyHint": True},
    output_schema={
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The deterministic compiled image prompt",
            }
        },
        "required": ["prompt"],
    },
)
def compile_preset_tool(preset: dict[str, Any]) -> ToolResult:
    """Compile a preset (JSON) into its deterministic image prompt. The same
    preset always yields the exact same prompt."""
    validated = _validate(preset)
    prompt = compile_preset(validated)
    return ToolResult(content=prompt, structured_content={"prompt": prompt})


@mcp.tool(
    meta={"openai/widgetAccessible": True},
    output_schema={
        "type": "object",
        "properties": {
            "saved": {"type": "boolean"},
            "id": {"type": "string"},
            "name": {"type": "string"},
            "updated_at": {"type": "string"},
        },
        "required": ["saved", "id", "name", "updated_at"],
    },
)
def save_preset(name: str, preset: dict[str, Any]) -> ToolResult:
    """Save (or update) a preset under a name, e.g. 'promo dark'. Saved
    presets can be re-opened later with open_preset_editor or get_preset."""
    validated = _validate(preset)
    record = get_store().save(name, validated.model_dump(exclude_none=True))
    return ToolResult(
        content=f"Preset '{record['name']}' saved.",
        structured_content={
            "saved": True,
            "id": record["id"],
            "name": record["name"],
            "updated_at": record["updated_at"],
        },
    )


@mcp.tool(
    annotations={"readOnlyHint": True},
    output_schema={
        "type": "object",
        "properties": {
            "presets": {"type": "array", "items": _PRESET_SUMMARY_SCHEMA}
        },
        "required": ["presets"],
    },
)
def list_presets(
    query: Optional[str] = None,
    sort: str = "last_used",
    limit: int = 20,
) -> ToolResult:
    """List saved presets. sort: last_used (default — 'the one I used
    yesterday'), created, updated or name. query filters by name."""
    records = get_store().list(query=query, sort=sort, limit=limit)
    if not records:
        text = "No presets saved yet." if not query else f"No presets match '{query}'."
    else:
        lines = [
            f"- {r['name']} ({r['layout']}, last used {r['last_used_at']})"
            for r in records
        ]
        text = "Saved presets:\n" + "\n".join(lines)
    return ToolResult(content=text, structured_content={"presets": records})


@mcp.tool(
    annotations={"readOnlyHint": True},
    output_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "preset": _PRESET_OBJECT_SCHEMA,
            "prompt": {"type": "string"},
        },
        "required": ["name", "preset", "prompt"],
    },
)
def get_preset(name_or_id: str) -> ToolResult:
    """Fetch a saved preset and its compiled prompt. To edit it visually,
    call open_preset_editor with its name instead."""
    record = get_store().get(name_or_id)
    if record is None:
        raise ToolError(f"No preset named '{name_or_id}'.")
    prompt = compile_preset(record["preset"])
    return ToolResult(
        content=f"Preset '{record['name']}':\n\n{prompt}",
        structured_content={
            "name": record["name"],
            "preset": record["preset"],
            "prompt": prompt,
        },
    )


@mcp.tool(
    output_schema={
        "type": "object",
        "properties": {"deleted": {"type": "string"}},
        "required": ["deleted"],
    },
)
def delete_preset(name_or_id: str) -> ToolResult:
    """Delete a saved preset by name or id. Ask the user to confirm first."""
    deleted = get_store().delete(name_or_id)
    if deleted is None:
        raise ToolError(f"No preset named '{name_or_id}'.")
    return ToolResult(
        content=f"Preset '{deleted}' deleted.",
        structured_content={"deleted": deleted},
    )


@mcp.tool(annotations={"readOnlyHint": True})
def get_preset_options() -> dict[str, Any]:
    """Reference of every valid preset value: layouts, zones, restriction
    presets, suggested art styles, lighting and size presets."""
    return {
        "layouts": LAYOUTS,
        "zones": list(ZONES),
        "restriction_presets": RESTRICTION_PRESETS,
        "art_styles": list(ART_STYLES),
        "lighting_styles": list(LIGHTING_STYLES),
        "size_presets": list(SIZE_PRESETS),
    }
