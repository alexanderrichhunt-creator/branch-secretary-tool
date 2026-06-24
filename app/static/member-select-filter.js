(function () {
  function optionSearchText(opt) {
    const explicit = (opt.getAttribute("data-member-name") || "").trim();
    if (explicit) return explicit.toLowerCase();
    const text = (opt.textContent || "").trim();
    return text.split("·")[0].trim().toLowerCase();
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

  function bindMemberSelectFilter(filterInput, selectEl) {
    if (!filterInput || !selectEl) return;

    if (!filterInput._memberFilterState) {
      filterInput._memberFilterState = captureStructure(selectEl);
    }

    const state = filterInput._memberFilterState;

    function renderFiltered() {
      const selected = selectEl.value;
      const q = (filterInput.value || "").trim();
      const qLower = q.toLowerCase();
      let visibleCount = 0;
      let singleMatchValue = null;
      let matchCount = 0;

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

      if (q && matchCount === 1 && singleMatchValue) {
        selectEl.value = singleMatchValue;
        selectEl.dispatchEvent(new Event("change", { bubbles: true }));
      } else if (selected && Array.from(selectEl.options).some(function (o) { return o.value === selected; })) {
        selectEl.value = selected;
      } else if (q) {
        selectEl.value = "";
      }

      if (q && visibleCount > 0) {
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
    renderFiltered();
  }

  function bindWithin(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      bindMemberSelectFilter(input, select);
    });
  }

  function resetAll() {
    document.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      input.value = "";
      if (typeof input._memberFilterApply === "function") {
        input._memberFilterApply();
      }
    });
  }

  function refreshWithin(root) {
    bindWithin(root);
  }

  window.MemberSelectFilter = {
    bind: bindMemberSelectFilter,
    init: function () {
      bindWithin(document);
    },
    bindWithin: bindWithin,
    refreshWithin: refreshWithin,
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
