(function () {
  function optionSearchText(opt) {
    const explicit = (opt.getAttribute("data-member-name") || "").trim();
    let text = explicit || (opt.textContent || "").trim().split("·")[0].trim();
    const parts = [];
    if (text) parts.push(text);
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

  function captureStructure(selectEl) {
    const structure = [];
    let firstOption = null;

    for (const node of selectEl.children) {
      if (node.tagName === "OPTION" && !firstOption) {
        firstOption = node.cloneNode(true);
        continue;
      }
      if (node.tagName === "OPTION") {
        structure.push({ type: "option", option: node.cloneNode(true) });
      } else if (node.tagName === "OPTGROUP") {
        structure.push({
          type: "group",
          label: node.label,
          options: Array.from(node.options).map(function (opt) {
            return opt.cloneNode(true);
          }),
        });
      }
    }

    return { firstOption: firstOption, structure: structure };
  }

  function appendStructure(selectEl, state) {
    selectEl.innerHTML = "";
    if (state.firstOption) {
      selectEl.appendChild(state.firstOption.cloneNode(true));
    }
    for (const item of state.structure) {
      if (item.type === "option") {
        selectEl.appendChild(item.option.cloneNode(true));
      } else if (item.type === "group") {
        const group = document.createElement("optgroup");
        group.label = item.label;
        for (const opt of item.options) {
          group.appendChild(opt.cloneNode(true));
        }
        selectEl.appendChild(group);
      }
    }
  }

  function bindMemberSelectFilter(filterInput, selectEl) {
    if (!filterInput || !selectEl) return;

    function ensureState() {
      if (!filterInput._memberFilterState) {
        filterInput._memberFilterState = captureStructure(selectEl);
      }
      return filterInput._memberFilterState;
    }

    function renderFiltered() {
      const state = ensureState();
      const selected = selectEl.value;
      const q = (filterInput.value || "").trim();
      const qLower = q.toLowerCase();
      let visibleCount = 0;
      let singleMatchValue = null;
      let matchCount = 0;

      if (!q) {
        appendStructure(selectEl, state);
        selectEl.removeAttribute("size");
        selectEl.classList.remove("member-filter-listbox");
        delete selectEl.dataset.memberFilterDirty;
        if (selected && Array.from(selectEl.options).some(function (o) { return o.value === selected; })) {
          selectEl.value = selected;
        }
        return;
      }

      selectEl.dataset.memberFilterDirty = "1";
      selectEl.innerHTML = "";
      if (state.firstOption) {
        selectEl.appendChild(state.firstOption.cloneNode(true));
      }

      for (const item of state.structure) {
        if (item.type === "option") {
          const text = optionSearchText(item.option);
          if (matchesQuery(text, qLower)) {
            selectEl.appendChild(item.option.cloneNode(true));
            visibleCount += 1;
            matchCount += 1;
            singleMatchValue = item.option.value;
          }
        } else if (item.type === "group") {
          const group = document.createElement("optgroup");
          group.label = item.label;
          let added = 0;
          for (const opt of item.options) {
            const text = optionSearchText(opt);
            if (matchesQuery(text, qLower)) {
              group.appendChild(opt.cloneNode(true));
              added += 1;
              visibleCount += 1;
              matchCount += 1;
              singleMatchValue = opt.value;
            }
          }
          if (added) {
            selectEl.appendChild(group);
          }
        }
      }

      if (matchCount === 1 && singleMatchValue) {
        selectEl.value = singleMatchValue;
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (selected && Array.from(selectEl.options).some(function (o) { return o.value === selected; })) {
        selectEl.value = selected;
      } else {
        selectEl.value = "";
      }

      if (visibleCount > 0) {
        selectEl.size = Math.min(8, visibleCount + 1);
        selectEl.classList.add("member-filter-listbox");
      } else {
        selectEl.removeAttribute("size");
        selectEl.classList.remove("member-filter-listbox");
      }
    }

    if (!filterInput.dataset.memberFilterBound) {
      filterInput.dataset.memberFilterBound = "1";
      filterInput.addEventListener("input", renderFiltered);
    }

    filterInput._memberFilterApply = renderFiltered;
  }

  function recaptureWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      if (!select) return;

      if (select.dataset.memberFilterDirty === "1" && input._memberFilterState) {
        appendStructure(select, input._memberFilterState);
        select.removeAttribute("size");
        select.classList.remove("member-filter-listbox");
        delete select.dataset.memberFilterDirty;
      }

      delete input._memberFilterState;
      bindMemberSelectFilter(input, select);
    });
  }

  function bindWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      bindMemberSelectFilter(input, select);
    });
  }

  function resetWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      input.value = "";
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      if (select && select.dataset.memberFilterDirty === "1" && typeof input._memberFilterApply === "function") {
        input._memberFilterApply();
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
