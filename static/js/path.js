/* Path finder: shows only the steps that fit the reader's 4 answers.
   Answers never leave the page and are never saved. */
(function () {
  "use strict";
  var form = document.getElementById("path-form");
  if (!form) return;
  var results = document.getElementById("path-results");
  var body = document.getElementById("results-body");
  var summary = document.getElementById("results-summary");
  var errorBox = document.getElementById("path-error");
  var heading = document.getElementById("results-h");

  var QUESTIONS = [
    { name: "live", label: "Where do you live?" },
    { name: "change", label: "What do you want to change?" },
    { name: "who", label: "Who is this for?" },
    { name: "born", label: "Where were you born?" }
  ];
  var WORDS = {
    live: { or: "you live in Oregon", wa: "you live in Washington", ut: "you live in Utah", other: "you live outside Oregon, Washington, and Utah" },
    change: { name: "a name change", marker: "a gender marker change", both: "a name and gender marker change" },
    who: { adult: "for yourself", parent: "for your child", minor: "for yourself, under 18" },
    born: { or: "an Oregon birth certificate", wa: "a Washington birth certificate", ut: "a Utah birth certificate", "other-us": "a birth certificate from another U.S. state or territory", outside: "a birth certificate from outside the U.S." }
  };

  function value(name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : null;
  }

  function keep(el, answers) {
    var change = el.getAttribute("data-change");
    var who = el.getAttribute("data-who");
    var okChange = !change || change.split(" ").indexOf(answers.change) !== -1;
    var okWho = !who || who.split(" ").indexOf(answers.who) !== -1;
    return okChange && okWho;
  }

  function block(id, answers) {
    var tpl = document.getElementById(id);
    if (!tpl || !tpl.content) return null;
    var frag = tpl.content.cloneNode(true);
    frag.querySelectorAll("[data-change], [data-who]").forEach(function (el) {
      if (!keep(el, answers)) el.parentNode.removeChild(el);
    });
    frag.querySelectorAll("ul").forEach(function (ul) {
      if (!ul.children.length) ul.parentNode.removeChild(ul);
    });
    return frag;
  }

  function showErrors(missing) {
    errorBox.textContent = "";
    var title = document.createElement("p");
    title.className = "callout-title";
    title.innerHTML = "<strong>Please answer every question.</strong>";
    errorBox.appendChild(title);
    var list = document.createElement("ul");
    missing.forEach(function (q) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.href = "#q-" + q.name;
      a.textContent = q.label;
      a.addEventListener("click", function (event) {
        event.preventDefault();
        var first = form.querySelector('input[name="' + q.name + '"]');
        if (first) first.focus();
      });
      li.appendChild(a);
      list.appendChild(li);
    });
    errorBox.appendChild(list);
    errorBox.hidden = false;
    var firstMissing = form.querySelector('input[name="' + missing[0].name + '"]');
    if (firstMissing) firstMissing.focus();
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var answers = {};
    var missing = [];
    QUESTIONS.forEach(function (q) {
      answers[q.name] = value(q.name);
      if (!answers[q.name]) missing.push(q);
    });
    if (missing.length) {
      showErrors(missing);
      return;
    }
    errorBox.hidden = true;
    body.textContent = "";

    var order = [
      "t-court-" + answers.live,
      "t-federal",
      "t-id-" + answers.live,
      "t-birth-" + answers.born,
      "t-after",
      "t-help-" + answers.live
    ];
    var n = 0;
    order.forEach(function (id) {
      var frag = block(id, answers);
      if (!frag) return;
      var h = frag.querySelector("h3");
      var hasContent = frag.querySelector("li, p");
      if (!hasContent) return;
      n += 1;
      if (h) h.textContent = "Step " + n + ": " + h.textContent;
      body.appendChild(frag);
    });

    summary.textContent =
      "These steps are for " + WORDS.change[answers.change] + " " + WORDS.who[answers.who] +
      ", when " + WORDS.live[answers.live] + ", with " + WORDS.born[answers.born] + ".";
    results.hidden = false;
    heading.focus();
  });

  form.addEventListener("reset", function () {
    results.hidden = true;
    errorBox.hidden = true;
    body.textContent = "";
  });
})();
