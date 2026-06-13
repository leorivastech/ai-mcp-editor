"""Vocabulary of the preset language: layouts, zones, restrictions, closing line.

These strings ARE the compiler output surface. Changing any of them changes
compiled prompts, which breaks determinism for saved presets — that is why the
compiler is versioned (see core/compiler/). Never edit v1 strings after
release; add a v2 instead.
"""

from __future__ import annotations

# --- Layout patterns (key → fixed English description) ---
LAYOUTS: dict[str, str] = {
    "full_bleed": (
        "Full bleed: the image covers the entire canvas edge to edge, "
        "with text overlaid on top."
    ),
    "split_v": (
        "Vertical split 50/50: two distinct visual zones side by side, "
        "left and right."
    ),
    "split_h": (
        "Horizontal split: upper half is the main image, "
        "lower half is a solid area for text."
    ),
    "diagonal": (
        "Diagonal split: the canvas is divided into two contrasting "
        "triangular zones by a diagonal line."
    ),
    "grid_2x2": "2x2 grid: four equal quadrants, each with its own content.",
    "three_col": (
        "Three equal vertical columns, each with its own content "
        "and supporting text."
    ),
    "hero_cta": (
        "Hero layout: the image fills the upper 80% of the canvas, "
        "with a solid bar across the bottom."
    ),
    "frame": (
        "Frame layout: all content sits inside a centered card "
        "over a contrasting background."
    ),
    "overlay": (
        "Overlay: a dark semi-transparent layer covers the full image, "
        "with all text centered on top."
    ),
}

# --- 3x3 placement zones ---
ZONES: tuple[str, ...] = (
    "top-left",
    "top-center",
    "top-right",
    "middle-left",
    "center",
    "middle-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)

# --- Element kinds ---
# text/subject are text-only (compiler v1+). product/background reference a
# real photo the user attaches at generation time (compiler v2+).
ELEMENT_KINDS: tuple[str, ...] = ("text", "subject", "product", "background")

# --- v2 vocabulary: user-provided input images (products & backgrounds) ---
# New in compiler v2; FROZEN at v2 release, same rule as the v1 strings above.
# A product can be placed in any of the 9 zones, plus "all-over".
PRODUCT_PLACEMENTS: tuple[str, ...] = ZONES + ("all-over",)
PRODUCT_DIRECTIVE = (
    "integrate it realistically into the composition with matching "
    "lighting, perspective and shadows"
)
PRODUCT_ALL_OVER = "repeated across the whole canvas"
BACKGROUND_DIRECTIVE = "use it as the full-canvas background behind everything"

# --- Restriction presets (key → phrase used in the "Do NOT include" line).
# Unknown restriction strings pass through verbatim (custom restrictions). ---
RESTRICTION_PRESETS: dict[str, str] = {
    "no_watermarks": "watermarks",
    "no_extra_text": "any text other than the quoted texts",
    "no_people": "people or faces",
    "no_logos": "logos or brand marks",
    "no_borders": "borders or frames",
    "no_distortion": "blurry, deformed or distorted areas",
}

CLOSING_LINE = (
    "Follow the layout, element placement, palette and restrictions exactly "
    "as specified. Render every quoted text verbatim, with no spelling "
    "changes or additions."
)

# --- Suggested values surfaced by the widget (not enforced by the schema) ---
ART_STYLES: tuple[str, ...] = (
    "photorealistic",
    "cinematic photo",
    "flat illustration",
    "3d render",
    "watercolor",
    "line art",
    "pixel art",
    "anime",
    "oil painting",
    "minimalist vector",
)

LIGHTING_STYLES: tuple[str, ...] = (
    "soft daylight",
    "golden hour",
    "studio softbox",
    "dramatic side lighting",
    "neon glow",
    "high-key bright",
)

SIZE_PRESETS: tuple[dict, ...] = (
    {"label": "1:1", "width": 1024, "height": 1024},
    {"label": "4:5", "width": 1080, "height": 1350},
    {"label": "9:16", "width": 1080, "height": 1920},
    {"label": "16:9", "width": 1920, "height": 1080},
    {"label": "3:2", "width": 1536, "height": 1024},
)
