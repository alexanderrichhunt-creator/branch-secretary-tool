(function () {
  function bindMemberSelectFilter(filterInput, selectEl) {
    if (!filterInput || !selectEl || selectEl.dataset.memberFilterBound) return;
    selectEl.dataset.memberFilterBound = "1";

    const options = Array.from(selectEl.options);
    const keepFirst = options[0];
    const otherOpts = options.slice(1);

    function applyFilter() {
      const q = (filterInput.value || "").trim().toLowerCase();
      const selected = selectEl.value;

      selectEl.innerHTML = "";
      selectEl.appendChild(keepFirst);

      for (const opt of otherOpts) {
        const text = (opt.textContent || "").toLowerCase();
        if (!q || text.includes(q)) {
          selectEl.appendChild(opt);
        }
      }

      if (selected && Array.from(selectEl.options).some(function (o) { return o.value === selected; })) {
        selectEl.value = selected;
      }
    }

    filterInput.addEventListener("input", applyFilter);
    selectEl._memberFilterApply = applyFilter;
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
