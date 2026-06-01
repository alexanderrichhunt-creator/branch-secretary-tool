(function () {
  function compareIsoDates(dateA, dateB, direction) {
    if (window.AppDateSort && window.AppDateSort.compareIsoDates) {
      return window.AppDateSort.compareIsoDates(dateA, dateB, direction);
    }
    const emptySentinel = direction === "desc" ? "0000-01-01" : "9999-12-31";
    const rankA = dateA || emptySentinel;
    const rankB = dateB || emptySentinel;
    const cmp = rankA.localeCompare(rankB);
    if (cmp !== 0) return direction === "asc" ? cmp : -cmp;
    return 0;
  }

  function getRows(wrap) {
    const tbody = wrap.querySelector("tbody");
    if (!tbody) return [];
    return Array.from(tbody.querySelectorAll("tr[data-talk-date]"));
  }

  function defaultDirection(column) {
    if (column === "date") return "desc";
    if (column === "speaker" || column === "topic") return "asc";
    return "asc";
  }

  function compareDate(a, b, direction) {
    const cmp = compareIsoDates(
      a.getAttribute("data-talk-date") || "",
      b.getAttribute("data-talk-date") || "",
      direction
    );
    if (cmp !== 0) return cmp;
    return (a.getAttribute("data-talk-speaker") || "").localeCompare(b.getAttribute("data-talk-speaker") || "");
  }

  function compareText(attr, a, b, direction) {
    const cmp = (a.getAttribute(attr) || "").localeCompare(b.getAttribute(attr) || "");
    if (cmp !== 0) return direction === "asc" ? cmp : -cmp;
    return compareDate(a, b, "desc");
  }

  function updateHeaderIndicators(wrap, column, direction) {
    wrap.querySelectorAll(".talks-recent-sortable").forEach(function (btn) {
      const sortColumn = btn.getAttribute("data-sort");
      const indicator = btn.querySelector(".speaker-pool-sort-indicator");
      const active = sortColumn === column;
      btn.classList.toggle("is-sorted", active);
      btn.setAttribute("aria-sort", active ? (direction === "asc" ? "ascending" : "descending") : "none");
      if (indicator) {
        indicator.textContent = active ? (direction === "asc" ? " ▲" : " ▼") : "";
      }
    });
  }

  function applySort(wrap, state) {
    const tbody = wrap.querySelector("tbody");
    if (!tbody || !state.column) return;

    const rows = getRows(wrap);
    rows.sort(function (a, b) {
      if (state.column === "date") return compareDate(a, b, state.direction);
      if (state.column === "speaker") return compareText("data-talk-speaker", a, b, state.direction);
      if (state.column === "topic") return compareText("data-talk-topic", a, b, state.direction);
      return 0;
    });

    rows.forEach(function (row) {
      tbody.appendChild(row);
    });
  }

  function initWrap(wrap) {
    const sortButtons = wrap.querySelectorAll(".talks-recent-sortable");
    if (!sortButtons.length) return;

    const state = { column: null, direction: "asc" };

    function refresh() {
      applySort(wrap, state);
      updateHeaderIndicators(wrap, state.column, state.direction);
    }

    sortButtons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        const column = btn.getAttribute("data-sort");
        if (!column) return;
        if (state.column === column) {
          state.direction = state.direction === "asc" ? "desc" : "asc";
        } else {
          state.column = column;
          state.direction = defaultDirection(column);
        }
        refresh();
      });
    });
  }

  document.querySelectorAll("[data-talks-recent-list]").forEach(initWrap);
})();
