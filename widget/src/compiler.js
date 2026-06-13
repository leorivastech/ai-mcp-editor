/**
 * JS port of core/compiler/ — MUST stay byte-identical to the Python
 * compilers. Both run against core/tests/golden/ (widget/test/golden.test.js
 * verifies this port). Never edit a released version's strings; add a new one.
 *
 * compile(preset) dispatches by preset.compiler_version, exactly like the
 * Python core/compiler/__init__.py.
 */
(function (root) {
  "use strict";

  var LATEST_VERSION = 2;

  var LAYOUTS = {
    full_bleed:
      "Full bleed: the image covers the entire canvas edge to edge, with text overlaid on top.",
    split_v:
      "Vertical split 50/50: two distinct visual zones side by side, left and right.",
    split_h:
      "Horizontal split: upper half is the main image, lower half is a solid area for text.",
    diagonal:
      "Diagonal split: the canvas is divided into two contrasting triangular zones by a diagonal line.",
    grid_2x2: "2x2 grid: four equal quadrants, each with its own content.",
    three_col:
      "Three equal vertical columns, each with its own content and supporting text.",
    hero_cta:
      "Hero layout: the image fills the upper 80% of the canvas, with a solid bar across the bottom.",
    frame:
      "Frame layout: all content sits inside a centered card over a contrasting background.",
    overlay:
      "Overlay: a dark semi-transparent layer covers the full image, with all text centered on top.",
  };

  var RESTRICTION_PRESETS = {
    no_watermarks: "watermarks",
    no_extra_text: "any text other than the quoted texts",
    no_people: "people or faces",
    no_logos: "logos or brand marks",
    no_borders: "borders or frames",
    no_distortion: "blurry, deformed or distorted areas",
  };

  var CLOSING_LINE =
    "Follow the layout, element placement, palette and restrictions exactly " +
    "as specified. Render every quoted text verbatim, with no spelling " +
    "changes or additions.";

  // v2 vocabulary (mirrors core/constants.py).
  var PRODUCT_DIRECTIVE =
    "integrate it realistically into the composition with matching " +
    "lighting, perspective and shadows";
  var PRODUCT_ALL_OVER = "repeated across the whole canvas";
  var BACKGROUND_DIRECTIVE =
    "use it as the full-canvas background behind everything";

  // -- shared section builders (identical text in v1 and v2) ------------------

  function sizeLine(size) {
    var label = size.aspect_label ? " (" + size.aspect_label + ")" : "";
    return "Output format: " + size.width + "x" + size.height + " pixels" + label + ".";
  }

  function styleLine(style) {
    style = style || {};
    var bits = [];
    if (style.art_style) bits.push("art style: " + style.art_style.trim());
    if (style.palette && style.palette.length) {
      bits.push(
        "color palette: " +
          style.palette
            .map(function (c) {
              return c.toLowerCase();
            })
            .join(" ")
      );
    }
    if (style.typography) bits.push("typography: " + style.typography.trim());
    if (style.lighting) bits.push("lighting: " + style.lighting.trim());
    return bits.length ? "Visual style — " + bits.join(", ") + "." : null;
  }

  function restrictionsLine(restrictions) {
    var bits = [];
    (restrictions || []).forEach(function (key) {
      var phrase = Object.prototype.hasOwnProperty.call(RESTRICTION_PRESETS, key)
        ? RESTRICTION_PRESETS[key]
        : key.trim();
      if (phrase) bits.push(phrase);
    });
    return bits.length ? "Do NOT include: " + bits.join(", ") + "." : null;
  }

  // -- v1 (FROZEN) ------------------------------------------------------------

  function compileV1(preset) {
    var parts = [];
    parts.push(sizeLine(preset.size));
    parts.push("Layout pattern: " + LAYOUTS[preset.layout]);

    var elementLines = [];
    (preset.elements || []).forEach(function (el) {
      var content = (el.content || "").trim();
      if (!content) return;
      if (el.kind === "text") {
        elementLines.push('  - "' + content + '" (text) -> positioned at ' + el.zone);
      } else {
        elementLines.push("  - " + content + " (subject) -> positioned at " + el.zone);
      }
    });
    if (elementLines.length) {
      parts.push("Element placement:\n" + elementLines.join("\n"));
    }

    var sl = styleLine(preset.style);
    if (sl) parts.push(sl);
    var rl = restrictionsLine(preset.restrictions);
    if (rl) parts.push(rl);

    if (preset.free_text && preset.free_text.trim()) {
      parts.push("Additional details:\n" + preset.free_text.trim());
    }

    parts.push(CLOSING_LINE);
    return parts.join("\n\n");
  }

  // -- v2 (FROZEN) — superset of v1 with an input-images section --------------

  function compileV2(preset) {
    var parts = [];
    parts.push(sizeLine(preset.size));
    parts.push("Layout pattern: " + LAYOUTS[preset.layout]);

    var imageLines = [];
    var n = 0;
    (preset.elements || []).forEach(function (el) {
      if (el.kind !== "product" && el.kind !== "background") return;
      n++;
      var content = (el.content || "").trim();
      var hint = content ? ' ("' + content + '")' : "";
      if (el.kind === "product") {
        var placement =
          el.zone === "all-over" ? PRODUCT_ALL_OVER : "placed at " + el.zone;
        imageLines.push(
          "  - Attached image " + n + " = PRODUCT" + hint + " -> " +
            placement + ", " + PRODUCT_DIRECTIVE + "."
        );
      } else {
        imageLines.push(
          "  - Attached image " + n + " = BACKGROUND" + hint + " -> " +
            BACKGROUND_DIRECTIVE + "."
        );
      }
    });
    if (imageLines.length) {
      parts.push(
        "Input images (the user will attach these, in order):\n" +
          imageLines.join("\n")
      );
    }

    var elementLines = [];
    (preset.elements || []).forEach(function (el) {
      if (el.kind !== "text" && el.kind !== "subject") return;
      var content = (el.content || "").trim();
      if (!content) return;
      if (el.kind === "text") {
        elementLines.push('  - "' + content + '" (text) -> positioned at ' + el.zone);
      } else {
        elementLines.push("  - " + content + " (subject) -> positioned at " + el.zone);
      }
    });
    if (elementLines.length) {
      parts.push("Element placement:\n" + elementLines.join("\n"));
    }

    var sl = styleLine(preset.style);
    if (sl) parts.push(sl);
    var rl = restrictionsLine(preset.restrictions);
    if (rl) parts.push(rl);

    if (preset.free_text && preset.free_text.trim()) {
      parts.push("Additional details:\n" + preset.free_text.trim());
    }

    parts.push(CLOSING_LINE);
    return parts.join("\n\n");
  }

  var COMPILERS = { 1: compileV1, 2: compileV2 };

  function compile(preset) {
    var version = (preset && preset.compiler_version) || 1;
    var fn = COMPILERS[version];
    if (!fn) throw new Error("Unknown compiler_version " + version);
    return fn(preset);
  }

  var api = {
    compile: compile,
    LATEST_VERSION: LATEST_VERSION,
    // Back-compat: defaultPreset() historically read COMPILER_VERSION.
    COMPILER_VERSION: 1,
    LAYOUTS: LAYOUTS,
    RESTRICTION_PRESETS: RESTRICTION_PRESETS,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.PresetCompiler = api;
  }
})(typeof self !== "undefined" ? self : globalThis);
