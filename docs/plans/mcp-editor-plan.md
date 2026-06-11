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

## 8. Widget (Apps SDK)

- Editor por pasos en un solo iframe: **medida** (presets de aspect ratio) → **layout** (grid de thumbnails SVG dibujados — el momento "wow") → **elementos** (texto + zona en grid 3×3 clickeable) → **estilo/paleta** (color pickers) → **restricciones** (chips)
- Panel lateral/inferior: **prompt compilándose en vivo** con cada click
- Botones: Copy prompt · Save preset (dispara tool call con el JSON)
- Lecciones ya aprendidas en frontera: reservar altura del iframe (no colapsa), protocolo Apps SDK actual, widget auto-actualizable

## 9. Estructura del repo

```
README.md            ← EL PRODUCTO: GIF demo, deploy 1-click, Docker, conectar a ChatGPT paso a paso, FAQ
core/                ← compilador puro + schemas + golden tests
server/              ← FastMCP server (tools + storage SQLite)
widget/              ← editor HTML/JS (Apps SDK)
Dockerfile           ← correr en cualquier lado
```

## 10. Fases

1. **v0.1** — core (compilador + golden tests) + MCP con `compile_preset` + widget editor básico + storage SQLite con save/list/get/delete. Sin auth. Demo grabada.
2. **v0.2** — README de lujo: GIF del flujo completo, botones de deploy (Cloud Run/Railway/Render), guía paso a paso de conexión a ChatGPT con screenshots, FAQ.
3. **v0.3** — pulir widget (thumbnails SVG finales, paletas predefinidas), export/import de presets como JSON portable.
4. **Roadmap público** (README): galería comunitaria de presets, playground web, multi-user/OAuth (contribución bienvenida).

## 11. Nombre del proyecto (pendiente — candidatos)

- **PresetLab** — directo, recordable
- **PromptPresets** — descriptivo, SEO fácil
- **Framecraft** — más marca, menos descriptivo
- **Presetic** — corto, disponible probablemente

## 12. Riesgos

- Apps SDK cambia protocolo (ya pasó) → costo de mantenimiento asumido
- Distribución: usuarios necesitan agregar el connector en dev mode (el README lo cubre con screenshots)
- Fricción de self-host (deploy + conectar) → mitigada con botones 1-click y guía con capturas
