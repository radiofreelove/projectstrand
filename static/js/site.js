/* The Strand Project: small enhancements. The site works without this file.
   No network requests. Reading settings are saved on this device. Checklist
   checkmarks are saved only if the reader turns on "Remember". */
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
  }
  function savePrefs(prefs) { store("set", KEYS.prefs, JSON.stringify(prefs)); }

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

  /* ---------- "How much to show" strip ---------- */
  /* One button at the top of every page for the same "Short version" setting
     as the checkbox in Reading settings. CSS swaps the wording from
     data-brief; this keeps aria-pressed and the checkbox in step. */
  var briefToggle = document.getElementById("brief-toggle");
  function syncBrief() {
    if (briefToggle) briefToggle.setAttribute("aria-pressed", current().brief === "on" ? "true" : "false");
    syncForm();
  }
  function setBrief(on, message) {
    var p = current();
    p.brief = on ? "on" : "off";
    apply(p);
    savePrefs(p);
    syncBrief();
    announce(message || (on
      ? "Short version. Extra sections on this page are now hidden."
      : "Full version. All sections on this page are showing."));
  }
  if (briefToggle) {
    briefToggle.addEventListener("click", function () {
      /* Hiding sections above the reader would slide the page under them, so
         hold the button at the same spot in the window. Focus stays on it. */
      var before = briefToggle.getBoundingClientRect().top;
      setBrief(current().brief !== "on");
      var moved = briefToggle.getBoundingClientRect().top - before;
      if (moved) window.scrollBy(0, moved);
    });
  }
  syncBrief();

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
          announce("Your checklist will be remembered on this device.");
        } else {
          store("remove", KEYS.remember);
          store("remove", KEYS.checks);
          announce("Your checklist will not be saved on this device.");
        }
        return;
      }
      apply(p);
      savePrefs(p);
      if (el.name === "brief") {
        syncBrief();
        announce(el.checked
          ? "Short version. Extra sections on this page are now hidden."
          : "Full version. All sections on this page are showing.");
      }
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
        syncBrief();
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

  /* Open a "Go deeper" section when a link points into it. In "Short version"
     mode that section is hidden, so the link would go nowhere. Then the short
     version turns off first (the strip and the checkbox both show it), and
     the page goes to the section. */
  var HIDDEN_IN_BRIEF = ".deeper, .brief-extra";
  function openTarget() {
    if (!window.location.hash) return;
    var id = window.location.hash.slice(1);
    try { id = decodeURIComponent(id); } catch (e) { /* use it as written */ }
    var target = document.getElementById(id);
    if (!target) return;
    var wasHidden = current().brief === "on" && target.closest(HIDDEN_IN_BRIEF);
    if (wasHidden) {
      setBrief(false, "Full version. The link goes to a section the short version hides, so all sections are showing again.");
    }
    var d = target.closest("details");
    if (d) d.open = true;
    if (wasHidden) target.scrollIntoView();
  }
  window.addEventListener("hashchange", openTarget);
  /* A second click on the same link does not change the address, so no
     "hashchange" fires. Handle that click here. */
  document.addEventListener("click", function (event) {
    var link = event.target.closest ? event.target.closest('a[href^="#"]') : null;
    if (link && link.getAttribute("href") === window.location.hash) openTarget();
  });
  openTarget();
})();
