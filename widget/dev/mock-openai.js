/**
 * Fake window.openai for local development — open the widget in a normal
 * browser (python widget/dev/serve.py) and iterate on the UI in seconds,
 * no deploy and no ChatGPT needed. Everything is logged to the console.
 */
(function () {
  "use strict";

  var KEY = "mock-widget-state";
  var stored = null;
  try {
    stored = JSON.parse(localStorage.getItem(KEY));
  } catch (e) { /* ignore */ }

  window.openai = {
    theme: window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light",
    locale: "en",
    maxHeight: 720,
    displayMode: "inline",
    toolOutput: null,
    toolResponseMetadata: null, // set to {preset: {...}} to test pre-loading
    widgetState: stored,

    setWidgetState: function (state) {
      console.log("[mock] setWidgetState", state);
      localStorage.setItem(KEY, JSON.stringify(state));
      return Promise.resolve();
    },

    callTool: function (name, args) {
      console.log("[mock] callTool", name, args);
      return new Promise(function (resolve) {
        setTimeout(function () {
          resolve({ structuredContent: { saved: true, name: args && args.name } });
        }, 400);
      });
    },

    sendFollowUpMessage: function (payload) {
      console.log("[mock] sendFollowUpMessage", payload);
      alert("Follow-up message sent to ChatGPT:\n\n" + (payload && payload.prompt));
      return Promise.resolve();
    },

    requestDisplayMode: function (payload) {
      console.log("[mock] requestDisplayMode", payload);
      return Promise.resolve({ mode: payload && payload.mode });
    },
  };

  console.log(
    "%c[mock] window.openai ready — tip: localStorage.removeItem('" + KEY + "') resets state",
    "color:#818cf8"
  );
})();
