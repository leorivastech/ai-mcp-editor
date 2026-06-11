/**
 * JS port of core/compiler/v1.py — MUST stay byte-identical to the Python
 * compiler. Both run against core/tests/golden/ (widget/test/golden.test.js
 * verifies this port). Never edit v1 strings after release; add a v2.
 */
(function (root) {
  "use strict";

  var COMPILER_VERSION = 1;

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

  function compile(preset) {
    var parts = [];

    var size = preset.size;
    var label = size.aspect_label ? " (" + size.aspect_label + ")" : "";
    parts.push(
      "Output format: " + size.width + "x" + size.height + " pixels" + label + "."
    );

    parts.push("Layout pattern: " + LAYOUTS[preset.layout]);

    var elementLines = [];
    (preset.elements || []).forEach(function (el) {
      var content = (el.content || "").trim();
      if (!content) return;
      if (el.kind === "text") {
        elementLines.push(
          '  - "' + content + '" (text) -> positioned at ' + el.zone
        );
      } else {
        elementLines.push(
          "  - " + content + " (subject) -> positioned at " + el.zone
        );
      }
    });
    if (elementLines.length) {
      parts.push("Element placement:\n" + elementLines.join("\n"));
    }

    var style = preset.style || {};
    var styleBits = [];
    if (style.art_style) styleBits.push("art style: " + style.art_style.trim());
    if (style.palette && style.palette.length) {
      styleBits.push(
        "color palette: " +
          style.palette
            .map(function (c) {
              return c.toLowerCase();
            })
            .join(" ")
      );
    }
    if (style.typography) styleBits.push("typography: " + style.typography.trim());
    if (style.lighting) styleBits.push("lighting: " + style.lighting.trim());
    if (styleBits.length) {
      parts.push("Visual style — " + styleBits.join(", ") + ".");
    }

    var restrictionBits = [];
    (preset.restrictions || []).forEach(function (key) {
      var phrase = Object.prototype.hasOwnProperty.call(RESTRICTION_PRESETS, key)
        ? RESTRICTION_PRESETS[key]
        : key.trim();
      if (phrase) restrictionBits.push(phrase);
    });
    if (restrictionBits.length) {
      parts.push("Do NOT include: " + restrictionBits.join(", ") + ".");
    }

    if (preset.free_text && preset.free_text.trim()) {
      parts.push("Additional details:\n" + preset.free_text.trim());
    }

    parts.push(CLOSING_LINE);
    return parts.join("\n\n");
  }

  var api = {
    compile: compile,
    COMPILER_VERSION: COMPILER_VERSION,
    LAYOUTS: LAYOUTS,
    RESTRICTION_PRESETS: RESTRICTION_PRESETS,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.PresetCompiler = api;
  }
})(typeof self !== "undefined" ? self : globalThis);
