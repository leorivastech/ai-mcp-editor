/**
 * The preset editor app. No framework — DOM is built once and patched on
 * events, so typing never loses focus to a re-render.
 *
 * window.openai integration:
 *  - state survives re-renders via setWidgetState (called on every change)
 *  - the Save button calls the save_preset tool directly (callTool)
 *  - the Generate button injects a follow-up message so ChatGPT renders the
 *    image from the compiled prompt (sendFollowUpMessage)
 *  - pre-loaded presets arrive via toolResponseMetadata.preset (_meta) when
 *    the model calls open_preset_editor(preset_name=...)
 */
(function () {
  "use strict";

  var compiler = window.PresetCompiler;
  var layouts = window.PresetLayouts;

  var ZONES = [
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
  ];
  var SIZE_PRESETS = [
    { label: "1:1", width: 1024, height: 1024 },
    { label: "4:5", width: 1080, height: 1350 },
    { label: "9:16", width: 1080, height: 1920 },
    { label: "16:9", width: 1920, height: 1080 },
    { label: "3:2", width: 1536, height: 1024 },
  ];
  var ART_STYLES = [
    "photorealistic", "cinematic photo", "flat illustration", "3d render",
    "watercolor", "line art", "pixel art", "anime", "oil painting",
    "minimalist vector",
  ];
  var LIGHTING = [
    "soft daylight", "golden hour", "studio softbox",
    "dramatic side lighting", "neon glow", "high-key bright",
  ];
  var RESTRICTIONS = {
    no_watermarks: "no watermarks",
    no_extra_text: "no extra text",
    no_people: "no people",
    no_logos: "no logos",
    no_borders: "no borders",
    no_distortion: "no distortion",
  };

  // --- state ---------------------------------------------------------------

  function defaultPreset() {
    return {
      schema_version: 1,
      size: { width: 1024, height: 1024, aspect_label: "1:1" },
      layout: "full_bleed",
      elements: [],
      style: { palette: [] },
      restrictions: [],
      free_text: null,
      compiler_version: compiler.COMPILER_VERSION,
    };
  }

  function initialPreset() {
    var oai = window.openai || {};
    if (oai.widgetState && oai.widgetState.preset) return oai.widgetState.preset;
    var meta = oai.toolResponseMetadata;
    if (meta && meta.preset) return meta.preset;
    return defaultPreset();
  }

  var preset = initialPreset();
  var saveTimer = null;

  function persist() {
    if (!window.openai || !window.openai.setWidgetState) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () {
      try {
        window.openai.setWidgetState({ preset: preset });
      } catch (e) { /* host may not support it */ }
    }, 250);
  }

  function hasKind(kind) {
    return preset.elements.some(function (e) { return e.kind === kind; });
  }

  function changed() {
    // Presets that use product/background images need the v2 compiler.
    if (hasKind("product") || hasKind("background")) preset.compiler_version = 2;
    renderPrompt();
    persist();
  }

  // --- tiny DOM helpers ------------------------------------------------------

  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      if (k === "class") el.className = attrs[k];
      else if (k === "html") el.innerHTML = attrs[k];
      else if (k.indexOf("on") === 0) el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  }

  function section(title, nodes) {
    return h("div", { class: "sec" }, [
      h("label", { class: "sec-title" }, [title]),
    ].concat(nodes));
  }

  function toast(msg, isError) {
    var t = document.getElementById("toast");
    t.textContent = msg;
    t.className = "show" + (isError ? " err" : "");
    clearTimeout(toast._timer);
    toast._timer = setTimeout(function () { t.className = ""; }, 2200);
  }

  // --- theme -----------------------------------------------------------------

  function applyTheme() {
    var theme =
      (window.openai && window.openai.theme) ||
      (window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light");
    document.documentElement.setAttribute("data-theme", theme);
  }
  window.addEventListener("openai:set_globals", applyTheme);

  // --- sections ----------------------------------------------------------------

  var refs = {};

  function buildSize() {
    var chips = h("div", { class: "chips" });
    SIZE_PRESETS.forEach(function (sp) {
      var chip = h("button", {
        class: "chip",
        type: "button",
        onclick: function () {
          preset.size = { width: sp.width, height: sp.height, aspect_label: sp.label };
          syncSize();
          changed();
        },
      }, [sp.label + " · " + sp.width + "×" + sp.height]);
      chip.dataset.label = sp.label;
      chips.appendChild(chip);
    });

    refs.w = h("input", { type: "number", min: 64, max: 8192, value: preset.size.width,
      oninput: function () { customSize(); } });
    refs.hh = h("input", { type: "number", min: 64, max: 8192, value: preset.size.height,
      oninput: function () { customSize(); } });
    var custom = h("div", { class: "size-custom" }, [
      refs.w, h("span", {}, ["×"]), refs.hh, h("span", {}, ["px"]),
    ]);

    refs.sizeChips = chips;
    syncSize();
    return section("Size", [chips, custom]);
  }

  function customSize() {
    var w = parseInt(refs.w.value, 10);
    var hh = parseInt(refs.hh.value, 10);
    if (!w || !hh) return;
    preset.size = { width: w, height: hh, aspect_label: null };
    syncSizeChips();
    changed();
  }

  function syncSizeChips() {
    Array.prototype.forEach.call(refs.sizeChips.children, function (c) {
      c.classList.toggle("on", c.dataset.label === preset.size.aspect_label);
    });
  }

  function syncSize() {
    refs.w.value = preset.size.width;
    refs.hh.value = preset.size.height;
    syncSizeChips();
  }

  function buildLayout() {
    var grid = h("div", { class: "layout-grid" });
    Object.keys(layouts.thumbs).forEach(function (key) {
      var card = h("button", {
        class: "layout-card" + (preset.layout === key ? " on" : ""),
        type: "button",
        html: layouts.thumbs[key],
        onclick: function () {
          preset.layout = key;
          Array.prototype.forEach.call(grid.children, function (c) {
            c.classList.toggle("on", c.dataset.key === key);
          });
          changed();
        },
      });
      card.dataset.key = key;
      card.appendChild(h("span", { class: "lbl" }, [layouts.labels[key]]));
      grid.appendChild(card);
    });
    return section("Layout", [grid]);
  }

  function zonePicker(el) {
    var grid = h("div", { class: "zone-grid", title: "Position" });
    ZONES.forEach(function (z) {
      var cell = h("button", {
        class: "zone-cell" + (el.zone === z ? " on" : ""),
        type: "button",
        title: z,
        onclick: function () {
          el.zone = z;
          Array.prototype.forEach.call(grid.children, function (c) {
            c.classList.toggle("on", c.dataset.zone === z);
          });
          changed();
        },
      });
      cell.dataset.zone = z;
      grid.appendChild(cell);
    });
    return grid;
  }

  function elementRow(el) {
    if (el.kind === "product") return imageRow(el, "PRODUCT", true);
    if (el.kind === "background") return imageRow(el, "BACKGROUND", false);
    return textRow(el);
  }

  function textRow(el) {
    var kindBtn = h("button", {
      class: "kind-toggle",
      type: "button",
      title: "Text is rendered verbatim inside the image; Subject describes what to draw",
      onclick: function () {
        el.kind = el.kind === "text" ? "subject" : "text";
        kindBtn.textContent = el.kind === "text" ? "TEXT" : "SUBJECT";
        input.placeholder = placeholderFor(el.kind);
        changed();
      },
    }, [el.kind === "text" ? "TEXT" : "SUBJECT"]);

    var input = h("input", {
      type: "text",
      value: el.content || "",
      placeholder: placeholderFor(el.kind),
      maxlength: 300,
      oninput: function () { el.content = input.value; changed(); },
    });

    var row = h("div", { class: "el-row" }, [
      kindBtn,
      input,
      zonePicker(el),
      h("button", {
        class: "el-del", type: "button", title: "Remove",
        onclick: function () {
          preset.elements = preset.elements.filter(function (e) { return e !== el; });
          row.remove();
          changed();
        },
      }, ["✕"]),
    ]);
    return row;
  }

  function placeholderFor(kind) {
    return kind === "text"
      ? 'Exact text to render, e.g. "50% OFF"'
      : "What to draw, e.g. a steaming pizza";
  }

  // Product placement: the same 3x3 grid as texts, plus an "All over" chip.
  function productPlacement(el) {
    var grid = h("div", { class: "zone-grid", title: "Position" });
    var allBtn;
    function sync() {
      Array.prototype.forEach.call(grid.children, function (c) {
        c.classList.toggle("on", c.dataset.zone === el.zone);
      });
      allBtn.classList.toggle("on", el.zone === "all-over");
    }
    ZONES.forEach(function (z) {
      var cell = h("button", {
        class: "zone-cell", type: "button", title: z,
        onclick: function () { el.zone = z; sync(); changed(); },
      });
      cell.dataset.zone = z;
      grid.appendChild(cell);
    });
    allBtn = h("button", {
      class: "chip allover", type: "button", title: "Scatter across the whole canvas",
      onclick: function () { el.zone = "all-over"; sync(); changed(); },
    }, ["All over"]);
    var wrap = h("div", { class: "placement" }, [grid, allBtn]);
    sync();
    return wrap;
  }

  // Product/background row: a fixed kind badge, an optional hint, and (for
  // products) a placement picker. The image itself is NOT uploaded here —
  // ChatGPT asks the user to attach it at generation time.
  function imageRow(el, badge, withPlacement) {
    var input = h("input", {
      type: "text",
      value: el.content || "",
      placeholder: withPlacement
        ? "Optional hint, e.g. the red sneaker"
        : "Optional hint, e.g. a marble kitchen counter",
      maxlength: 300,
      oninput: function () { el.content = input.value; changed(); },
    });
    var del = h("button", {
      class: "el-del", type: "button", title: "Remove",
      onclick: function () {
        preset.elements = preset.elements.filter(function (e) { return e !== el; });
        row.remove();
        changed();
      },
    }, ["✕"]);
    var children = [
      h("span", {
        class: "kind-badge",
        title: "You attach this photo in the chat when generating",
      }, [badge]),
      input,
    ];
    if (withPlacement) children.push(productPlacement(el));
    children.push(del);
    var row = h("div", { class: "el-row" }, children);
    return row;
  }

  function buildElements() {
    refs.elRows = h("div", { class: "el-rows" });
    preset.elements.forEach(function (el) {
      refs.elRows.appendChild(elementRow(el));
    });
    function add(kind) {
      if (preset.elements.length >= 12) return toast("Max 12 elements", true);
      // For now: at most one product and one background image slot.
      if ((kind === "product" || kind === "background") && hasKind(kind)) {
        return toast("One " + kind + " for now", true);
      }
      var el = kind === "background"
        ? { kind: kind, content: "" }
        : { kind: kind, content: "", zone: "center" };
      preset.elements.push(el);
      refs.elRows.appendChild(elementRow(el));
      changed();
    }
    function addBtn(label, kind) {
      return h("button", {
        class: "btn", type: "button",
        onclick: function () { add(kind); },
      }, [label]);
    }
    var btns = h("div", { class: "add-btns" }, [
      addBtn("+ Text", "text"),
      addBtn("+ Subject", "subject"),
      addBtn("+ Product 🖼", "product"),
      addBtn("+ Background 🖼", "background"),
    ]);
    return section("Elements", [refs.elRows, btns]);
  }

  function singleChips(values, get, set) {
    var chips = h("div", { class: "chips" });
    values.forEach(function (v) {
      var chip = h("button", {
        class: "chip" + (get() === v ? " on" : ""),
        type: "button",
        onclick: function () {
          set(get() === v ? null : v);
          Array.prototype.forEach.call(chips.children, function (c) {
            c.classList.toggle("on", c.dataset.v === get());
          });
          changed();
        },
      }, [v]);
      chip.dataset.v = v;
      chips.appendChild(chip);
    });
    return chips;
  }

  function buildStyle() {
    var artChips = singleChips(
      ART_STYLES,
      function () { return preset.style.art_style || null; },
      function (v) { preset.style.art_style = v; }
    );

    refs.paletteRow = h("div", { class: "palette-row" });
    var colorInput = h("input", { type: "color", value: "#4f46e5",
      style: "position:absolute;opacity:0;width:0;height:0" });
    colorInput.addEventListener("change", function () {
      if ((preset.style.palette || []).length >= 8) return toast("Max 8 colors", true);
      preset.style.palette.push(colorInput.value.toLowerCase());
      renderPalette();
      changed();
    });
    refs.colorInput = colorInput;
    renderPalette();

    var typo = h("input", {
      class: "txt-input", type: "text", maxlength: 120,
      placeholder: "Typography, e.g. bold condensed sans-serif",
      value: (preset.style.typography || ""),
      oninput: function () { preset.style.typography = typo.value || null; changed(); },
    });

    var lightChips = singleChips(
      LIGHTING,
      function () { return preset.style.lighting || null; },
      function (v) { preset.style.lighting = v; }
    );

    return section("Style", [artChips, refs.paletteRow, colorInput, typo, lightChips]);
  }

  function renderPalette() {
    refs.paletteRow.innerHTML = "";
    (preset.style.palette || []).forEach(function (color, i) {
      refs.paletteRow.appendChild(
        h("button", {
          class: "swatch", type: "button", title: color + " (click to remove)",
          style: "background:" + color,
          onclick: function () {
            preset.style.palette.splice(i, 1);
            renderPalette();
            changed();
          },
        })
      );
    });
    refs.paletteRow.appendChild(
      h("button", {
        class: "palette-add", type: "button", title: "Add color",
        onclick: function () { refs.colorInput.click(); },
      }, ["+"])
    );
  }

  function buildRestrictions() {
    var chips = h("div", { class: "chips" });
    Object.keys(RESTRICTIONS).forEach(function (key) {
      var chip = h("button", {
        class: "chip" + (preset.restrictions.indexOf(key) >= 0 ? " on" : ""),
        type: "button",
        onclick: function () {
          var idx = preset.restrictions.indexOf(key);
          if (idx >= 0) preset.restrictions.splice(idx, 1);
          else preset.restrictions.push(key);
          chip.classList.toggle("on", idx < 0);
          changed();
        },
      }, [RESTRICTIONS[key]]);
      chips.appendChild(chip);
    });

    refs.customChips = h("div", { class: "chips" });
    renderCustomRestrictions();

    var input = h("input", {
      class: "txt-input", type: "text", maxlength: 120,
      placeholder: "Custom, e.g. no neon colors — press Enter",
      onkeydown: function (ev) {
        if (ev.key !== "Enter") return;
        var v = input.value.trim();
        if (!v) return;
        if (preset.restrictions.length >= 20) return toast("Max 20 restrictions", true);
        preset.restrictions.push(v);
        input.value = "";
        renderCustomRestrictions();
        changed();
      },
    });

    var row = h("div", { class: "custom-restriction" }, [input]);
    return section("Restrictions", [chips, refs.customChips, row]);
  }

  function renderCustomRestrictions() {
    refs.customChips.innerHTML = "";
    preset.restrictions
      .filter(function (r) { return !(r in RESTRICTIONS); })
      .forEach(function (r) {
        refs.customChips.appendChild(
          h("button", {
            class: "chip on removable", type: "button", title: "Remove",
            onclick: function () {
              preset.restrictions = preset.restrictions.filter(function (x) { return x !== r; });
              renderCustomRestrictions();
              changed();
            },
          }, [r])
        );
      });
  }

  function buildFreeText() {
    var ta = h("textarea", {
      class: "txt-input", maxlength: 1500, rows: 2,
      placeholder: "Anything else, in your own words (optional)",
      oninput: function () { preset.free_text = ta.value || null; changed(); },
    });
    ta.value = preset.free_text || "";
    return section("Additional details", [ta]);
  }

  // --- prompt panel ---------------------------------------------------------

  function buildPromptPanel() {
    refs.promptPre = h("pre", {}, [""]);

    var copyBtn = h("button", { class: "btn", type: "button", onclick: copyPrompt }, ["Copy"]);
    refs.saveName = h("input", {
      class: "save-name", type: "text", maxlength: 80,
      placeholder: "Preset name…",
      value: preset.name || "",
    });
    var saveBtn = h("button", { class: "btn", type: "button", onclick: savePreset }, ["Save"]);
    var genBtn = h("button", { class: "btn primary", type: "button", onclick: generate }, ["Generate 🎨"]);

    return h("div", { class: "prompt-panel" }, [
      h("div", { class: "pp-head" }, [
        h("span", { class: "t" }, ["Compiled prompt — live"]),
      ]),
      refs.promptPre,
      h("div", { class: "pp-actions" }, [copyBtn, refs.saveName, saveBtn, genBtn]),
    ]);
  }

  function currentPrompt() {
    return compiler.compile(preset);
  }

  function renderPrompt() {
    refs.promptPre.textContent = currentPrompt();
  }

  function copyPrompt() {
    var text = currentPrompt();
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () { toast("Prompt copied"); },
        function () { toast("Copy failed", true); }
      );
    } else {
      toast("Clipboard unavailable", true);
    }
  }

  function savePreset() {
    var name = (refs.saveName.value || "").trim();
    if (!name) return toast("Give the preset a name first", true);
    if (!window.openai || !window.openai.callTool) {
      return toast("Saving needs the ChatGPT host", true);
    }
    preset.name = name;
    window.openai
      .callTool("save_preset", { name: name, preset: preset })
      .then(function () { toast("Saved as “" + name + "”"); persist(); })
      .catch(function (e) { toast("Save failed: " + (e && e.message ? e.message : e), true); });
  }

  function generate() {
    var message =
      "Generate this image now, using this exact prompt verbatim:\n\n" +
      currentPrompt();
    var oai = window.openai || {};
    try {
      if (oai.sendFollowUpMessage) {
        oai.sendFollowUpMessage({ prompt: message });
        toast("Sent to ChatGPT — generating…");
      } else if (oai.sendFollowupTurn) {
        oai.sendFollowupTurn({ prompt: message });
        toast("Sent to ChatGPT — generating…");
      } else {
        copyPrompt();
        toast("Prompt copied — paste it to generate", false);
      }
    } catch (e) {
      toast("Could not send: " + e.message, true);
    }
  }

  // --- boot -------------------------------------------------------------------

  function boot() {
    applyTheme();
    var app = document.getElementById("app");

    var header = h("div", { class: "hd" }, [
      h("h1", {}, ["Image Prompt Preset"]),
    ]);
    if (preset.name) {
      header.appendChild(h("span", { class: "loaded-name" }, [preset.name]));
    }

    app.appendChild(header);
    app.appendChild(buildSize());
    app.appendChild(buildLayout());
    app.appendChild(buildElements());
    app.appendChild(buildStyle());
    app.appendChild(buildRestrictions());
    app.appendChild(buildFreeText());
    app.appendChild(buildPromptPanel());
    app.appendChild(h("div", { id: "toast" }));

    renderPrompt();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
