/* Runs before the page draws, so saved reading settings apply without a flash.
   Reading settings are saved on this device automatically, as on The Stasis
   Project. "Forget everything" in Reading settings erases them. */
(function () {
  var root = document.documentElement;
  root.classList.add("js");
  var prefs = null;
  try {
    prefs = JSON.parse(window.localStorage.getItem("strand:prefs") || "null");
  } catch (e) {
    prefs = null;
  }
  if (!prefs || typeof prefs !== "object") return;
  var allowed = {
    theme: ["auto", "light", "dark", "contrast"],
    size: ["m", "l", "xl"],
    spacing: ["normal", "wide"],
    font: ["system", "hyper"],
    brief: ["off", "on"]
  };
  Object.keys(allowed).forEach(function (key) {
    if (allowed[key].indexOf(prefs[key]) !== -1) {
      root.setAttribute("data-" + key, prefs[key]);
    }
  });
})();
