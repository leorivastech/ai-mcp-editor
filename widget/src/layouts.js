/**
 * Inline SVG thumbnails for each layout pattern. They inherit CSS custom
 * properties (--th-a accent, --th-b base, --th-t text-line) so they adapt
 * to light/dark theme automatically.
 */
(function (root) {
  "use strict";

  function svg(inner) {
    return (
      '<svg viewBox="0 0 64 48" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
      inner +
      "</svg>"
    );
  }

  var bar = function (x, y, w) {
    return (
      '<rect x="' + x + '" y="' + y + '" width="' + w +
      '" height="3" rx="1.5" fill="var(--th-t)"/>'
    );
  };

  var LAYOUT_THUMBS = {
    full_bleed: svg(
      '<rect x="2" y="2" width="60" height="44" rx="3" fill="var(--th-a)"/>' +
        bar(18, 18, 28) + bar(22, 26, 20)
    ),
    split_v: svg(
      '<rect x="2" y="2" width="29" height="44" rx="3" fill="var(--th-a)"/>' +
        '<rect x="33" y="2" width="29" height="44" rx="3" fill="var(--th-b)"/>' +
        bar(38, 22, 19)
    ),
    split_h: svg(
      '<rect x="2" y="2" width="60" height="26" rx="3" fill="var(--th-a)"/>' +
        '<rect x="2" y="31" width="60" height="15" rx="3" fill="var(--th-b)"/>' +
        bar(22, 36, 20)
    ),
    diagonal: svg(
      '<path d="M5 2 h54 a3 3 0 0 1 3 3 v38 a3 3 0 0 1 -3 3 L5 2" fill="var(--th-a)"/>' +
        '<path d="M5 2 a3 3 0 0 0 -3 3 v38 a3 3 0 0 0 3 3 h54 L5 2" fill="var(--th-b)"/>' +
        bar(10, 34, 18)
    ),
    grid_2x2: svg(
      '<rect x="2" y="2" width="29" height="21" rx="3" fill="var(--th-a)"/>' +
        '<rect x="33" y="2" width="29" height="21" rx="3" fill="var(--th-b)"/>' +
        '<rect x="2" y="25" width="29" height="21" rx="3" fill="var(--th-b)"/>' +
        '<rect x="33" y="25" width="29" height="21" rx="3" fill="var(--th-a)"/>'
    ),
    three_col: svg(
      '<rect x="2" y="2" width="18" height="44" rx="3" fill="var(--th-a)"/>' +
        '<rect x="23" y="2" width="18" height="44" rx="3" fill="var(--th-b)"/>' +
        '<rect x="44" y="2" width="18" height="44" rx="3" fill="var(--th-a)"/>'
    ),
    hero_cta: svg(
      '<rect x="2" y="2" width="60" height="33" rx="3" fill="var(--th-a)"/>' +
        '<rect x="2" y="38" width="60" height="8" rx="3" fill="var(--th-b)"/>' +
        bar(24, 40.5, 16)
    ),
    frame: svg(
      '<rect x="2" y="2" width="60" height="44" rx="3" fill="var(--th-b)"/>' +
        '<rect x="12" y="9" width="40" height="30" rx="3" fill="var(--th-a)"/>' +
        bar(22, 22, 20)
    ),
    overlay: svg(
      '<rect x="2" y="2" width="60" height="44" rx="3" fill="var(--th-a)"/>' +
        '<rect x="2" y="2" width="60" height="44" rx="3" fill="var(--th-b)" opacity="0.55"/>' +
        bar(20, 20, 24) + bar(24, 27, 16)
    ),
  };

  var LAYOUT_LABELS = {
    full_bleed: "Full bleed",
    split_v: "Split vertical",
    split_h: "Split horizontal",
    diagonal: "Diagonal",
    grid_2x2: "Grid 2×2",
    three_col: "3 columns",
    hero_cta: "Hero + bar",
    frame: "Frame",
    overlay: "Overlay",
  };

  root.PresetLayouts = { thumbs: LAYOUT_THUMBS, labels: LAYOUT_LABELS };
})(typeof self !== "undefined" ? self : globalThis);
