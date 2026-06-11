# Plan: MCP de Presets para Prompts de Imagen (proyecto open source)

> Estado: PLAN APROBADO EN DISCUSIÓN — pendiente nombre final y arranque
> Fecha: 2026-06-10
> Repo destino: NUEVO repo público en github.com/leorivastech (separado de frontera3k)

## 1. Pitch

App de ChatGPT (MCP + widget Apps SDK) para **formular prompts de imagen estructurados y reproducibles**. El usuario abre un mini editor dentro del chat, selecciona medida → layout → estilo → paleta → restricciones, el prompt se compila en vivo de forma **determinista** (mismo preset = mismo prompt, siempre), y luego le dice a ChatGPT "genera la imagen" — la generación la pone el host, sin API keys ni costos nuestros.

Los presets se guardan: *"guárdalo como promo dark"*, *"tráeme el que usé ayer"*.

**Claim honesto**: lo determinista es el prompt, no la imagen (el modelo sigue siendo estocástico). El pitch es "reproducible prompts / structured prompting".

## 2. Modelo de distribución: self-host, README-first

**No es un super sistema ni un servicio hosted multi-usuario.** Es un repo open source donde cada quien levanta SU instancia y la conecta a SU ChatGPT. Consecuencias de diseño:

- **Sin OAuth, sin IdP, sin Firestore**: cada instancia es de un solo usuario/equipo. ChatGPT permite agregar connectors sin auth (dev mode).
- **Storage simple**: presets en **SQLite o JSON file** dentro de la instancia. "Guárdala" y "tráeme la de ayer" funcionan igual — es single-user.
- **El README es el producto**: instrucciones claras de levantar + conectar son la mitad del valor del repo. Secciones: qué es (GIF demo), deploy en 1 click (Cloud Run button / Railway / Render), correr con Docker, conectarlo a ChatGPT paso a paso (settings → connectors → dev mode), FAQ.
- Multi-usuario/OAuth queda como nota en el roadmap por si alguien lo quiere contribuir — no lo construimos nosotros.

## 3. Decisiones tomadas

| Decisión | Valor | Razón |
|---|---|---|
| Forma | MCP-first, app de ChatGPT con widget | Generación nativa del host resuelve BYOK; Leo ya domina Apps SDK |
| Público | **Solo OpenAI/ChatGPT en v1** | Claude no genera imágenes — no es el público (decisión Leo 2026-06-10) |
| Distribución | **Self-host, cada quien su instancia** | "No ocupamos hacer un super sistema, solo un README claro de cómo conectarlo" (Leo 2026-06-10) |
| Nombre comercial de recetas | **Presets** | Universal (Lightroom), cero explicación |
| Storage | SQLite (o JSON file) local a la instancia | Single-user, cero infra |
| Auth | Ninguna en v1 | Connector dev-mode sin auth; instancia personal |
| Stack | Python 3.12 + FastMCP, widget HTML/JS plano | Stack ya probado de Leo en los MCP de frontera (widgets incluidos) |
| Licencia | MIT | |

## 4. Base heredada (frontera3k, commit `e2f8453` — la v1 simple de ai_visual_recipes)

Lo que se extrae y limpia del compilador v1:

- **Patterns de layout** (con thumbnail SVG en el widget): `full_bleed`, `split_v`, `split_h`, `diagonal`, `grid_2x2`, `three_col`, `hero_cta`, `frame`, `overlay`
- **Zonas 3×3**: top-left … center … bottom-right para posicionar textos
- **Estilo**: palette, typography, lighting
- **Restricciones**: presets de "Do NOT include …" + custom
- **Orden fijo de ensamblado**: size → layout → element placement → style → restrictions → free text → closing line

Lo que NO se hereda: intents/estrategias, placeholders de página, buckets/colecciones, referencias de imagen, Leonardo, MySQL, FastAPI routers.

## 5. Schema del Preset v1

```json
{
  "schema_version": 1,
  "name": "promo dark",
  "size": { "width": 1080, "height": 1350, "aspect_label": "4:5" },
  "layout": "diagonal",
  "elements": [
    { "kind": "text", "content": "50% OFF", "zone": "top-right" },
    { "kind": "subject", "content": "a steaming pizza", "zone": "center" }
  ],
  "style": {
    "art_style": "photorealistic | flat illustration | 3d render | …",
    "palette": ["#1a1a2e", "#e94560"],
    "typography": "bold condensed sans-serif",
    "lighting": "dramatic side lighting"
  },
  "restrictions": ["no_watermarks", "no_extra_text", "custom: no people"],
  "free_text": "…",
  "compiler_version": 1
}
```

**`compiler_version` es clave para el determinismo**: si el compilador evoluciona, los presets guardados siguen compilando con su versión original → el mismo preset produce el mismo prompt para siempre. Compiladores versionados conviven en el código.

## 6. Compilador (core)

- Módulo puro, cero dependencias, función `compile(preset) -> str`
- Orden fijo, plantillas fijas en inglés, sin aleatoriedad, sin LLM
- Salida ejemplo:

```
Output format: 1080x1350 pixels (4:5).

Layout pattern: Diagonal split: two contrasting triangular zones.

Element placement:
  - "50% OFF" (text) → positioned at top-right
  - a steaming pizza (subject) → positioned at center

Visual style — photorealistic, color palette: #1a1a2e, #e94560, typography: bold condensed sans-serif, lighting: dramatic side lighting.

Do NOT include: watermarks, extra text, people.
```

- Suite de tests golden: preset JSON → prompt exacto esperado (snapshot tests). Es la garantía pública del determinismo.

## 7. Tools del MCP

| Tool | Hace | Notas |
|---|---|---|
| `open_preset_editor` | Devuelve el widget editor (vacío o pre-cargado con un preset) | Widget = la cara del producto |
| `compile_preset` | preset JSON → prompt texto | También la usa el widget en vivo |
| `save_preset` | Guarda/actualiza por nombre | `created_at`, `updated_at`, `last_used_at` |
| `list_presets` | Lista con filtros (`query`, `sort=last_used`) | Habilita "tráeme el que usé ayer" — el LLM traduce lenguaje natural a args |
| `get_preset` | Trae uno (por nombre/id) y opcionalmente reabre el editor pre-cargado | Editar uno guardado |
| `delete_preset` | Borra | Confirmación en conversación |

Flujo estrella: `get_preset("promo dark")` → editor pre-cargado → ajusta paleta → `save_preset` → "ahora genera la imagen" → ChatGPT genera con el prompt compilado.

## 8. Widget (Apps SDK) — ingeniería

UX: editor por pasos en un solo iframe: **medida** (presets de aspect ratio) → **layout** (grid de thumbnails SVG — el momento "wow") → **elementos** (texto + zona en grid 3×3 clickeable) → **estilo/paleta** (color pickers) → **restricciones** (chips). Panel con el **prompt compilándose en vivo** con cada click. Botones: Copy prompt · Save preset · **Generate 🎨**.

Reglas de ingeniería (lo que hace un widget BUENO):

1. **Un solo HTML autocontenido** servido como resource MCP (`ui://widget/editor.html`, mimeType `text/html+skybridge`). Iframe sandboxeado con CSP → JS/CSS/SVGs inline, nada de CDNs. Hay paso de build aunque el fuente esté en archivos separados.
2. **`window.openai` es toda la API**:
   - `setWidgetState()` en cada click → el editor sobrevive scroll/re-render (error #1 de widgets malos)
   - `callTool("save_preset", …)` → el botón Save habla directo con el server
   - `sendFollowUpMessage("Generate the image with this prompt: …")` → botón Generate mete el mensaje y ChatGPT genera; flujo completo sin teclear
   - Altura reservada fija desde el primer render (lección frontera: iframe que colapsa)
3. **Preview en vivo sin latencia**: `compiler.js` es un port JS del compilador Python. La divergencia la mata el diseño: **ambos compiladores corren contra los mismos archivos golden** — si el port se desvía un carácter, CI truena. Los goldens son el contrato entre lenguajes.
4. **`structuredContent` vs `_meta`** en el tool result: el prompt compilado va en `structuredContent` (el modelo lo lee para generar); el estado interno del editor va en `_meta` (solo el widget, no gasta contexto).
5. **Harness local**: `dev/mock-openai.js` finge `window.openai` → el widget se desarrolla en un browser normal, sin deploy ni ChatGPT. Iterar UI en segundos.

## 9. Estructura del repo

```
ai-mcp-editor/
├── README.md                  ← el producto: demo GIF, deploy 1-click, conexión a ChatGPT, FAQ
├── LICENSE                    ← MIT
├── Dockerfile
├── pyproject.toml
├── core/                      ← EL CEREBRO (Python puro, cero deps de red)
│   ├── schema.py              ← Pydantic: Preset v1
│   ├── constants.py           ← 9 layouts, zonas 3×3, estilos, restricciones
│   ├── compiler/
│   │   ├── __init__.py        ← compile(preset) despacha por compiler_version
│   │   └── v1.py              ← compilador v1, CONGELADO al publicar
│   └── tests/
│       ├── golden/            ← preset.json → expected_prompt.txt (contrato Python↔JS)
│       └── test_compiler.py
├── server/                    ← EL MCP (FastMCP)
│   ├── app.py                 ← arranque, monta tools + widget resource
│   ├── tools.py               ← las 6 tools
│   ├── storage.py             ← SQLite (presets + timestamps)
│   └── widget_resource.py     ← sirve ui://widget/editor.html
└── widget/                    ← LA CARA (Apps SDK)
    ├── src/
    │   ├── index.html
    │   ├── editor.js          ← estado + pasos + render
    │   ├── compiler.js        ← port JS del compilador (live preview)
    │   ├── layouts.js         ← thumbnails SVG
    │   └── styles.css
    ├── dev/mock-openai.js     ← window.openai falso para desarrollo en browser
    └── build → un solo HTML inline
```

## 10. Fases / orden de construcción (cada paso deja algo que funciona)

1. **`core/`** — schema + constants + compiler v1 + goldens. Pure Python, pytest verde. Sin servidor.
2. **`storage.py`** — SQLite con tests.
3. **`server/`** — FastMCP con las 6 tools; probado con MCP Inspector (tools devuelven texto, sin widget).
4. **`widget/`** — desarrollo en browser local contra el mock; aquí se quema el tiempo de UI iterando rápido.
5. **Integración** — widget como resource, conectar a ChatGPT dev mode, flujo completo real. (El paso más frágil va al final, cuando cerebro y cara ya están probados por separado — solo se depura el pegamento.)
6. **Empaque** — Dockerfile, deploy buttons, README con GIF, demo grabada.

Versiones públicas: **v0.1** = pasos 1–5 sin pulir · **v0.2** = README de lujo + deploy buttons + guía con capturas · **v0.3** = pulido de widget, export/import de presets JSON · **Roadmap** (README): galería comunitaria de presets, playground web, multi-user/OAuth (contribución bienvenida).

## 11. Nombre del proyecto (pendiente — candidatos)

- **PresetLab** — directo, recordable
- **PromptPresets** — descriptivo, SEO fácil
- **Framecraft** — más marca, menos descriptivo
- **Presetic** — corto, disponible probablemente

## 12. Riesgos

- Apps SDK cambia protocolo (ya pasó) → costo de mantenimiento asumido
- Distribución: usuarios necesitan agregar el connector en dev mode (el README lo cubre con screenshots)
- Fricción de self-host (deploy + conectar) → mitigada con botones 1-click y guía con capturas
