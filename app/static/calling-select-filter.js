(function () {
  let callingOptions = null;
  let documentClickBound = false;
  const boundInputs = new Set();

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

  function hideAllResults(exceptInput) {
    boundInputs.forEach(function (input) {
      if (exceptInput && input === exceptInput) return;
      if (input._callingResultsEl) hideResults(input._callingResultsEl);
    });
  }

  function bindCallingFilter(input) {
    if (!input || input.dataset.callingFilterBound) return;
    input.dataset.callingFilterBound = "1";
    boundInputs.add(input);

    const options = loadOptions();
    const resultsEl = ensureResultsEl(input);
    input._callingResultsEl = resultsEl;

    function chooseOption(value) {
      input.value = value || "";
      hideResults(resultsEl);
      // Change only — avoid re-opening the list via a synthetic input event.
      input.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function renderResults() {
      const q = (input.value || "").trim();
      const matches = options
        .filter(function (opt) {
          return matchesQuery(opt, q);
        })
        .slice(0, 12);

      hideAllResults(input);

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
    input.addEventListener("focus", function () {
      hideAllResults(input);
      renderResults();
    });

    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideResults(resultsEl);
      }
      if (event.key === "Enter") {
        const first = resultsEl.querySelector(".calling-filter-result");
        if (first && !resultsEl.classList.contains("d-none")) {
          event.preventDefault();
          event.stopPropagation();
          chooseOption(first.getAttribute("data-calling") || "");
        }
      }
    });

    resultsEl.addEventListener("mousedown", function (event) {
      // Keep focus on the input so the field is not blurred before click applies.
      event.preventDefault();
    });

    resultsEl.addEventListener("click", function (event) {
      const btn = event.target.closest(".calling-filter-result");
      if (!btn || !resultsEl.contains(btn)) return;
      event.preventDefault();
      event.stopPropagation();
      chooseOption(btn.getAttribute("data-calling") || "");
    });

    input._callingFilterReset = function () {
      input.value = "";
      hideResults(resultsEl);
    };
  }

  function ensureDocumentClick() {
    if (documentClickBound) return;
    documentClickBound = true;
    document.addEventListener("click", function (event) {
      boundInputs.forEach(function (input) {
        const resultsEl = input._callingResultsEl;
        if (!resultsEl) return;
        if (input.contains(event.target) || resultsEl.contains(event.target)) return;
        hideResults(resultsEl);
      });
    });
  }

  function bindWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-calling-filter]").forEach(function (input) {
      if (input.dataset.callingFilterBound) return;
      bindCallingFilter(input);
    });
    ensureDocumentClick();
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
