(function () {
  let memberOptions = null;

  function loadOptions() {
    if (memberOptions) return memberOptions;
    const el = document.getElementById("member-select-options-data");
    if (!el) return [];
    try {
      memberOptions = JSON.parse(el.textContent || "[]");
    } catch (e) {
      memberOptions = [];
    }
    return memberOptions;
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function searchText(name) {
    const text = (name || "").trim();
    const parts = [text];
    const comma = text.indexOf(",");
    if (comma > 0) {
      const last = text.slice(0, comma).trim();
      const first = text.slice(comma + 1).replace(/\(\d+\)\s*$/, "").trim();
      if (first && last) {
        parts.push(first + " " + last);
        parts.push(last + " " + first);
      }
    }
    return parts.join(" ").toLowerCase();
  }

  function matchesQuery(text, query) {
    const q = (query || "").trim().toLowerCase();
    if (!q) return true;
    const tokens = q.split(/\s+/).filter(Boolean);
    if (!tokens.length) return true;
    return tokens.every(function (token) {
      return text.includes(token);
    });
  }

  function populateSelect(selectEl, options, placeholder) {
    selectEl.innerHTML = "";
    const first = document.createElement("option");
    first.value = "";
    first.textContent = placeholder;
    selectEl.appendChild(first);

    const pool = options.filter(function (opt) {
      return opt.group === "pool";
    });
    const other = options.filter(function (opt) {
      return opt.group !== "pool";
    });

    function appendGroup(label, items) {
      if (!items.length) return;
      const group = document.createElement("optgroup");
      group.label = label;
      items.forEach(function (opt) {
        const option = document.createElement("option");
        option.value = String(opt.id);
        option.textContent = opt.hint ? opt.name + " · " + opt.hint : opt.name;
        option.setAttribute("data-member-name", opt.name);
        group.appendChild(option);
      });
      selectEl.appendChild(group);
    }

    appendGroup("Regular attendees (speaker pool)", pool);
    appendGroup(pool.length ? "Other members" : "All members", other);
  }

  function ensureResultsEl(filterInput, selectEl) {
    let resultsEl = filterInput.nextElementSibling;
    if (!resultsEl || !resultsEl.classList.contains("member-filter-results")) {
      resultsEl = document.createElement("div");
      resultsEl.className = "member-filter-results list-group d-none";
      resultsEl.setAttribute("role", "listbox");
      filterInput.insertAdjacentElement("afterend", resultsEl);
    }
    selectEl.classList.add("member-filter-select-hidden");
    return resultsEl;
  }

  function hideResults(resultsEl) {
    if (!resultsEl) return;
    resultsEl.classList.add("d-none");
    resultsEl.innerHTML = "";
  }

  function bindMemberSelectFilter(filterInput, selectEl) {
    if (!filterInput || !selectEl || filterInput.dataset.memberFilterBound) return;
    filterInput.dataset.memberFilterBound = "1";

    const options = loadOptions();
    const placeholder =
      selectEl.querySelector('option[value=""]')?.textContent || "— Choose speaker —";
    if (options.length && !selectEl.dataset.optionsLoaded) {
      populateSelect(selectEl, options, placeholder);
      selectEl.dataset.optionsLoaded = "1";
    }

    const resultsEl = ensureResultsEl(filterInput, selectEl);

    function chooseOption(opt) {
      selectEl.value = String(opt.id);
      filterInput.value = opt.name;
      hideResults(resultsEl);
      selectEl.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function renderResults() {
      const q = (filterInput.value || "").trim();
      if (!q) {
        hideResults(resultsEl);
        return;
      }

      const matches = options
        .filter(function (opt) {
          return matchesQuery(searchText(opt.name), q);
        })
        .slice(0, 12);

      if (!matches.length) {
        resultsEl.innerHTML =
          '<div class="list-group-item small text-muted py-2">No members match that search.</div>';
        resultsEl.classList.remove("d-none");
        return;
      }

      resultsEl.innerHTML = matches
        .map(function (opt) {
          return (
            '<button type="button" class="list-group-item list-group-item-action py-2 member-filter-result" role="option" data-member-id="' +
            escapeHtml(String(opt.id)) +
            '">' +
            '<div class="fw-semibold">' +
            escapeHtml(opt.name) +
            "</div>" +
            (opt.hint
              ? '<div class="small text-muted">' + escapeHtml(opt.hint) + "</div>"
              : "") +
            "</button>"
          );
        })
        .join("");
      resultsEl.classList.remove("d-none");
    }

    filterInput.addEventListener("input", renderResults);
    filterInput.addEventListener("focus", renderResults);

    filterInput.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideResults(resultsEl);
      }
    });

    resultsEl.addEventListener("mousedown", function (event) {
      event.preventDefault();
    });

    resultsEl.addEventListener("click", function (event) {
      const btn = event.target.closest(".member-filter-result");
      if (!btn) return;
      const id = btn.getAttribute("data-member-id");
      const opt = options.find(function (item) {
        return String(item.id) === String(id);
      });
      if (opt) chooseOption(opt);
    });

    document.addEventListener("click", function (event) {
      if (!filterInput.contains(event.target) && !resultsEl.contains(event.target)) {
        hideResults(resultsEl);
      }
    });

    filterInput._memberFilterReset = function () {
      filterInput.value = "";
      selectEl.value = "";
      hideResults(resultsEl);
    };

    filterInput._memberFilterApply = renderResults;
  }

  function bindWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      if (input.dataset.memberFilterBound) return;
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      bindMemberSelectFilter(input, select);
    });
  }

  function recaptureWithin(root) {
    bindWithin(root);
  }

  function resetWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      if (typeof input._memberFilterReset === "function") {
        input._memberFilterReset();
      } else {
        input.value = "";
        const id = input.getAttribute("data-member-filter-target");
        const select = id ? document.getElementById(id) : null;
        if (select) select.value = "";
      }
    });
  }

  function resetAll() {
    resetWithin(document);
  }

  window.MemberSelectFilter = {
    bind: bindMemberSelectFilter,
    init: function () {
      bindWithin(document);
    },
    bindWithin: bindWithin,
    refreshWithin: bindWithin,
    recaptureWithin: recaptureWithin,
    resetWithin: resetWithin,
    resetAll: resetAll,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      window.MemberSelectFilter.init();
    });
  } else {
    window.MemberSelectFilter.init();
  }
})();
