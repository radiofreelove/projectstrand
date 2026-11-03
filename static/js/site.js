/* The Strand Project: small enhancements. The site works without this file.
   No network requests. Nothing is stored unless the reader turns on "Remember". */
(function () {
  "use strict";
  var root = document.documentElement;
  var KEYS = { remember: "strand:remember", prefs: "strand:prefs", checks: "strand:checks" };

  function store(action, key, value) {
    try {
      if (action === "get") return window.localStorage.getItem(key);
      if (action === "set") window.localStorage.setItem(key, value);
      if (action === "remove") window.localStorage.removeItem(key);
    } catch (e) {
      return null;
    }
    return null;
  }
  function remembering() { return store("get", KEYS.remember) === "on"; }

  function announce(text) {
    var el = document.getElementById("announcer");
    if (!el) return;
    el.textContent = "";
    window.setTimeout(function () { el.textContent = text; }, 50);
  }

  /* ---------- Reading settings ---------- */
  var DEFAULTS = { theme: "auto", size: "m", spacing: "normal", font: "system", brief: "off" };

  function current() {
    var out = {};
    Object.keys(DEFAULTS).forEach(function (k) {
      out[k] = root.getAttribute("data-" + k) || DEFAULTS[k];
    });
    return out;
  }
  function apply(prefs) {
    Object.keys(prefs).forEach(function (k) { root.setAttribute("data-" + k, prefs[k]); });
    if (remembering()) store("set", KEYS.prefs, JSON.stringify(prefs));
  }

  var dialog = document.getElementById("settings");
  var opener = document.getElementById("settings-open");
  var closer = document.getElementById("settings-close");

  function syncForm() {
    if (!dialog) return;
    var p = current();
    dialog.querySelectorAll('input[name="size"]').forEach(function (el) { el.checked = el.value === p.size; });
    dialog.querySelectorAll('input[name="theme"]').forEach(function (el) { el.checked = el.value === p.theme; });
    var spacing = dialog.querySelector('input[name="spacing"]');
    if (spacing) spacing.checked = p.spacing === "wide";
    var font = dialog.querySelector('input[name="font"]');
    if (font) font.checked = p.font === "hyper";
    var brief = dialog.querySelector('input[name="brief"]');
    if (brief) brief.checked = p.brief === "on";
    var remember = dialog.querySelector('input[name="remember"]');
    if (remember) remember.checked = remembering();
  }

  if (dialog && opener && typeof dialog.showModal === "function") {
    opener.addEventListener("click", function () {
      syncForm();
      dialog.showModal();
    });
    closer.addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("close", function () { opener.focus(); });
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("change", function (event) {
      var el = event.target;
      var p = current();
      if (el.name === "size" || el.name === "theme") p[el.name] = el.value;
      if (el.name === "spacing") p.spacing = el.checked ? "wide" : "normal";
      if (el.name === "font") p.font = el.checked ? "hyper" : "system";
      if (el.name === "brief") p.brief = el.checked ? "on" : "off";
      if (el.name === "remember") {
        if (el.checked) {
          store("set", KEYS.remember, "on");
          saveChecks();
          announce("Your settings will be remembered on this device.");
        } else {
          store("remove", KEYS.remember);
          store("remove", KEYS.prefs);
          store("remove", KEYS.checks);
          announce("Nothing will be saved on this device.");
        }
      }
      apply(p);
    });
    var forget = document.getElementById("forget-all");
    if (forget) {
      forget.addEventListener("click", function () {
        [KEYS.remember, KEYS.prefs, KEYS.checks].forEach(function (k) { store("remove", k); });
        apply(DEFAULTS);
        checks = {};
        document.querySelectorAll("input[data-check]").forEach(function (box) {
          box.checked = false;
          markStep(box);
        });
        syncForm();
        var status = document.getElementById("forget-status");
        if (status) status.textContent = "Done. Nothing from this site is saved on this device.";
      });
    }
  } else if (opener) {
    opener.hidden = true;
  }

  /* ---------- Leave quickly ---------- */
  var exit = document.getElementById("quick-exit");
  function leave(event) {
    if (event) event.preventDefault();
    var url = exit ? exit.href : "https://www.weather.gov/";
    try { document.body.innerHTML = ""; document.title = "Weather"; } catch (e) { /* keep going */ }
    window.location.replace(url);
  }
  if (exit) exit.addEventListener("click", leave);
  var shiftPresses = [];
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Shift" || event.repeat) return;
    var now = Date.now();
    shiftPresses = shiftPresses.filter(function (t) { return now - t < 2000; });
    shiftPresses.push(now);
    if (shiftPresses.length >= 3) leave();
  });

  /* ---------- Checklists ---------- */
  var checks = {};
  if (remembering()) {
    try { checks = JSON.parse(store("get", KEYS.checks) || "{}") || {}; } catch (e) { checks = {}; }
  }
  function saveChecks() {
    if (remembering()) store("set", KEYS.checks, JSON.stringify(checks));
  }
  function markStep(box) {
    var step = box.closest(".step");
    if (step) step.classList.toggle("is-done", box.checked);
  }
  document.querySelectorAll("input[data-check]").forEach(function (box) {
    var key = box.getAttribute("data-check");
    if (checks[key]) box.checked = true;
    markStep(box);
    box.addEventListener("change", function () {
      if (box.checked) { checks[key] = true; } else { delete checks[key]; }
      markStep(box);
      saveChecks();
    });
  });

  /* ---------- Copy buttons ---------- */
  document.querySelectorAll("button[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      var done = function () {
        btn.textContent = "Copied";
        announce("Copied: " + text);
        window.setTimeout(function () { btn.textContent = "Copy"; }, 2500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, function () { announce("Copy did not work. Select the text instead."); });
      } else {
        announce("Copy is not available in this browser. Select the text instead.");
      }
    });
  });

  /* ---------- Print buttons and printing ---------- */
  document.querySelectorAll("[data-print]").forEach(function (btn) {
    btn.addEventListener("click", function () { window.print(); });
  });
  var reopened = [];
  window.addEventListener("beforeprint", function () {
    document.querySelectorAll("details:not([open])").forEach(function (d) { d.open = true; reopened.push(d); });
  });
  window.addEventListener("afterprint", function () {
    reopened.forEach(function (d) { d.open = false; });
    reopened = [];
  });

  /* Open a "Go deeper" section when a link points into it. */
  function openTarget() {
    if (!window.location.hash) return;
    var target = document.getElementById(window.location.hash.slice(1));
    if (target) {
      var d = target.closest("details");
      if (d) d.open = true;
    }
  }
  window.addEventListener("hashchange", openTarget);
  openTarget();
})();
