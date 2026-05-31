(function () {
  function bindMemberSelectFilter(filterInput, selectEl) {
    if (!filterInput || !selectEl || selectEl.dataset.memberFilterBound) return;
    selectEl.dataset.memberFilterBound = "1";

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

    function renderFiltered(query) {
      const selected = selectEl.value;
      const q = (query || "").trim().toLowerCase();
      selectEl.innerHTML = "";
      if (firstOption) {
        selectEl.appendChild(firstOption.cloneNode(true));
      }

      for (const item of structure) {
        if (item.type === "option") {
          const text = (item.option.textContent || "").toLowerCase();
          if (!q || text.includes(q)) {
            selectEl.appendChild(item.option.cloneNode(true));
          }
        } else if (item.type === "group") {
          const group = document.createElement("optgroup");
          group.label = item.label;
          let added = 0;
          for (const opt of item.options) {
            const text = (opt.textContent || "").toLowerCase();
            if (!q || text.includes(q)) {
              group.appendChild(opt.cloneNode(true));
              added += 1;
            }
          }
          if (added) {
            selectEl.appendChild(group);
          }
        }
      }

      if (selected && Array.from(selectEl.options).some(function (o) { return o.value === selected; })) {
        selectEl.value = selected;
      }
    }

    filterInput.addEventListener("input", function () {
      renderFiltered(filterInput.value);
    });
    selectEl._memberFilterApply = function () {
      renderFiltered(filterInput.value);
    };
  }

  function init() {
    document.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      bindMemberSelectFilter(input, select);
    });
  }

  function resetAll() {
    document.querySelectorAll("[data-member-filter-target]").forEach(function (input) {
      input.value = "";
      const id = input.getAttribute("data-member-filter-target");
      const select = id ? document.getElementById(id) : null;
      if (select && typeof select._memberFilterApply === "function") {
        select._memberFilterApply();
      }
    });
  }

  window.MemberSelectFilter = {
    bind: bindMemberSelectFilter,
    init: init,
    resetAll: resetAll,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
