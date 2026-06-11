# AI Image Preset Editor — MCP app for ChatGPT

**A visual editor inside ChatGPT that builds deterministic AI image prompts.**
Pick a size, a layout, place your texts, choose style, palette and restrictions — and watch the prompt compile live. Then just say *"generate the image"* and ChatGPT renders it. Save the result as a **preset** and reuse it forever: *"open my promo dark preset"*.

![CI](https://github.com/leorivastech/ai-mcp-editor/actions/workflows/ci.yml/badge.svg)

> Same preset in → same prompt out. **Always.**
> To be precise: the *prompt* is deterministic; image models are still stochastic. What you get is a structured, reproducible, versionable prompt instead of a hand-written one that's different every time.

## What it looks like

You: *"I want to compose an image"* → the editor opens **inside the chat**:

- **Size** — aspect ratio chips (1:1, 4:5, 9:16, 16:9, 3:2) or custom pixels
- **Layout** — 9 visual patterns: full bleed, vertical/horizontal split, **diagonal split**, **2×2 grid**, 3 columns, hero + bar, frame, overlay
- **Elements** — your exact texts (rendered verbatim) and subjects, each placed on a 3×3 position grid
- **Style** — art style, color palette, typography, lighting
- **Restrictions** — no watermarks, no extra text, no people… plus your own

The compiled prompt updates live with every click. Then:

- **Generate 🎨** — sends the prompt to ChatGPT, which generates the image natively
- **Save** — *"save it as promo dark"* works too, from the conversation
- Later: *"bring up the preset I used yesterday"* → the editor reopens pre-loaded

## Quickstart

### 1. Run your instance

This is a **self-hosted, single-user** server — your presets live in one SQLite file on your instance. No accounts, no tracking, no cloud database.

**Docker (any host):**

```bash
docker build -t preset-editor .
docker run -p 8080:8080 -v preset-data:/data preset-editor
```

**Google Cloud Run (free tier friendly):**

```bash
gcloud run deploy preset-editor --source . --allow-unauthenticated --region us-central1
```

> Note: on Cloud Run the filesystem is ephemeral — saved presets reset on redeploys/restarts unless you mount a volume (Cloud Run volume mounts or any host with a persistent disk). For durable presets prefer a small VPS, Fly.io, Railway with a volume, or your own machine + a tunnel (e.g. `cloudflared`, `ngrok`).

**Local (development):**

```bash
python -m venv .venv && source .venv/bin/activate
pip install .[dev]
python -m server.app   # → http://localhost:8080/mcp
```

Your MCP endpoint is **`https://YOUR-HOST/mcp`** — ChatGPT needs a publicly reachable HTTPS URL.

### 2. Connect it to ChatGPT

1. ChatGPT → **Settings → Apps & Connectors → Advanced → Developer mode** (enable it)
2. **Create** a new connector
3. Name: `Preset Editor` · MCP Server URL: `https://YOUR-HOST/mcp` · Auth: **None**
4. Save. In a new chat, enable the connector (＋ → your connector if needed)

### 3. Use it

| You say | What happens |
|---|---|
| *"I want to compose an image"* | The visual editor opens in the chat |
| *(click around)* | The prompt compiles live in the panel |
| *"Generate the image"* / **Generate 🎨** | ChatGPT generates with the exact compiled prompt |
| *"Save it as promo dark"* / **Save** | Preset stored on your instance |
| *"List my presets"* | Names + when you last used each |
| *"Open the one I used yesterday"* | Editor reopens pre-loaded |

## Why deterministic prompts?

Hand-written prompts drift: every retype changes words, order, emphasis — and your brand look with them. Here a preset is **data** (JSON), and the prompt is **compiled** from it with fixed templates, fixed order, zero randomness, zero LLM:

```json
{
  "size": { "width": 1080, "height": 1350, "aspect_label": "4:5" },
  "layout": "diagonal",
  "elements": [
    { "kind": "text", "content": "50% OFF", "zone": "top-right" },
    { "kind": "subject", "content": "a steaming artisan pizza", "zone": "center" }
  ],
  "style": { "art_style": "photorealistic", "palette": ["#1a1a2e", "#e94560"] },
  "restrictions": ["no_watermarks", "no_extra_text"]
}
```

compiles — **always** — to:

```
Output format: 1080x1350 pixels (4:5).

Layout pattern: Diagonal split: the canvas is divided into two contrasting triangular zones by a diagonal line.

Element placement:
  - "50% OFF" (text) -> positioned at top-right
  - a steaming artisan pizza (subject) -> positioned at center

Visual style — art style: photorealistic, color palette: #1a1a2e #e94560.

Do NOT include: watermarks, any text other than the quoted texts.

Follow the layout, element placement, palette and restrictions exactly as specified. Render every quoted text verbatim, with no spelling changes or additions.
```

Two guarantees back this up:

- **Golden tests**: every fixture in `core/tests/golden/` must compile to its exact expected output, byte for byte — in **both** the Python compiler and its JS port (the widget's live preview). CI fails if they diverge by one character.
- **Versioned compilers**: each preset records its `compiler_version`. Compilers are frozen on release — future improvements ship as v2, v3… and old presets keep producing their original prompt forever.

## MCP tools

| Tool | Purpose |
|---|---|
| `open_preset_editor` | Opens the widget (optionally pre-loaded with a saved preset) |
| `compile_preset` | Preset JSON → deterministic prompt |
| `save_preset` | Save/update by name (also used by the widget's Save button) |
| `list_presets` | Filter by name, sort by `last_used` / `created` / `name` |
| `get_preset` | Fetch a preset + its compiled prompt |
| `delete_preset` | Remove one |
| `get_preset_options` | Reference of all valid values (layouts, zones, styles…) |

## Development

```bash
pip install .[dev]
pytest                              # Python: compiler goldens + storage + MCP e2e
node widget/test/golden.test.js     # JS port == Python compiler, byte for byte
python widget/dev/serve.py          # widget UI at http://127.0.0.1:8001 (mock host)
```

The widget dev server injects a fake `window.openai`, so you can iterate on the UI in a normal browser — no deploy, no ChatGPT.

After an **intentional** compiler change (a new version!): `python -m core.tests.regen_goldens` and review the diff.

```
core/      schema + constants + versioned compilers + golden fixtures
server/    FastMCP server: tools, SQLite storage, widget assembly
widget/    the editor: src/ (inlined into ONE html), dev/ (mock), test/ (parity)
```

## Roadmap

- Export / import presets as portable JSON
- Community preset gallery
- Standalone web playground (no ChatGPT needed)
- Multi-user mode with OAuth — contributions welcome

## License

[MIT](LICENSE)
