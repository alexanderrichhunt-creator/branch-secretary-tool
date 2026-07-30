(function () {
  let callingOptions = null;

  function loadOptions() {
    if (callingOptions) return callingOptions;
    const el = document.getElementById("calling-select-options-data");
    if (!el) return [];
    try {
      callingOptions = JSON.parse(el.textContent || "[]");
    } catch (e) {
      callingOptions = [];
    }
    return callingOptions;
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function matchesQuery(text, query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) return true;
    const hay = (text || "").toLowerCase();
    const tokens = q.split(/\s+/).filter(Boolean);
    if (!tokens.length) return true;
    return tokens.every(function (token) {
      return hay.includes(token);
    });
  }

  function ensureResultsEl(input) {
    let wrap = input.closest(".calling-filter-wrap");
    if (!wrap) {
      wrap = document.createElement("div");
      wrap.className = "calling-filter-wrap member-filter-wrap";
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);
    }
    let resultsEl = wrap.querySelector(".calling-filter-results");
    if (!resultsEl) {
      resultsEl = document.createElement("div");
      resultsEl.className = "calling-filter-results member-filter-results list-group d-none";
      resultsEl.setAttribute("role", "listbox");
      input.insertAdjacentElement("afterend", resultsEl);
    }
    return resultsEl;
  }

  function hideResults(resultsEl) {
    if (!resultsEl) return;
    resultsEl.classList.add("d-none");
    resultsEl.innerHTML = "";
  }

  function bindCallingFilter(input) {
    if (!input || input.dataset.callingFilterBound) return;
    input.dataset.callingFilterBound = "1";

    const options = loadOptions();
    const resultsEl = ensureResultsEl(input);

    function chooseOption(value) {
      input.value = value;
      hideResults(resultsEl);
      input.dispatchEvent(new Event("change", { bubbles: true }));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function renderResults() {
      const q = (input.value || "").trim();
      const matches = options
        .filter(function (opt) {
          return matchesQuery(opt, q);
        })
        .slice(0, 12);

      if (!q && !matches.length) {
        hideResults(resultsEl);
        return;
      }

      if (!matches.length) {
        resultsEl.innerHTML =
          '<div class="list-group-item small text-muted py-2">No callings match — you can still use what you typed.</div>';
        resultsEl.classList.remove("d-none");
        return;
      }

      resultsEl.innerHTML = matches
        .map(function (opt) {
          return (
            '<button type="button" class="list-group-item list-group-item-action py-2 calling-filter-result" role="option" data-calling="' +
            escapeHtml(opt) +
            '">' +
            escapeHtml(opt) +
            "</button>"
          );
        })
        .join("");
      resultsEl.classList.remove("d-none");
    }

    input.addEventListener("input", renderResults);
    input.addEventListener("focus", renderResults);

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideResults(resultsEl);
      }
      if (event.key === "Enter") {
        const first = resultsEl.querySelector(".calling-filter-result");
        if (first && !resultsEl.classList.contains("d-none")) {
          event.preventDefault();
          chooseOption(first.getAttribute("data-calling") || "");
        }
      }
    });

    resultsEl.addEventListener("mousedown", function (event) {
      event.preventDefault();
    });

    resultsEl.addEventListener("click", function (event) {
      const btn = event.target.closest(".calling-filter-result");
      if (!btn) return;
      chooseOption(btn.getAttribute("data-calling") || "");
    });

    document.addEventListener("click", function (event) {
      if (!input.contains(event.target) && !resultsEl.contains(event.target)) {
        hideResults(resultsEl);
      }
    });

    input._callingFilterReset = function () {
      input.value = "";
      hideResults(resultsEl);
    };
  }

  function bindWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-calling-filter]").forEach(function (input) {
      if (input.dataset.callingFilterBound) return;
      bindCallingFilter(input);
    });
  }

  function resetWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-calling-filter]").forEach(function (input) {
      if (typeof input._callingFilterReset === "function") {
        input._callingFilterReset();
      } else {
        input.value = "";
      }
    });
  }

  window.CallingSelectFilter = {
    bind: bindCallingFilter,
    init: function () {
      bindWithin(document);
    },
    bindWithin: bindWithin,
    refreshWithin: bindWithin,
    recaptureWithin: bindWithin,
    resetWithin: resetWithin,
    resetAll: function () {
      resetWithin(document);
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.CallingSelectFilter.init();
    });
  } else {
    window.CallingSelectFilter.init();
  }
})();
