(function () {
  const STATUS_TIER = { never: 0, available: 1, consider: 2, recent: 3, upcoming: 3 };

  function poolDays(el) {
    const raw = el.getAttribute("data-pool-days");
    if (raw === "" || raw === null) return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  function compareAvailability(a, b) {
    const tierA = STATUS_TIER[a.getAttribute("data-pool-status")] ?? 9;
    const tierB = STATUS_TIER[b.getAttribute("data-pool-status")] ?? 9;
    if (tierA !== tierB) return tierA - tierB;

    const status = a.getAttribute("data-pool-status");
    const daysA = poolDays(a);
    const daysB = poolDays(b);
    if (status === "available" || status === "recent" || status === "upcoming") {
      const dA = daysA ?? 0;
      const dB = daysB ?? 0;
      if (dA !== dB) return dB - dA;
    } else if (status === "consider") {
      const dA = daysA ?? 0;
      const dB = daysB ?? 0;
      if (dA !== dB) return dA - dB;
    }

    return (a.getAttribute("data-pool-name") || "").localeCompare(b.getAttribute("data-pool-name") || "");
  }

  function compareName(a, b, direction) {
    const cmp = (a.getAttribute("data-pool-name") || "").localeCompare(b.getAttribute("data-pool-name") || "");
    return direction === "desc" ? -cmp : cmp;
  }

  function compareIsoDates(dateA, dateB, direction) {
    const emptySentinel = direction === "desc" ? "0000-01-01" : "9999-12-31";
    const rankA = dateA || emptySentinel;
    const rankB = dateB || emptySentinel;
    const cmp = rankA.localeCompare(rankB);
    if (cmp !== 0) return direction === "asc" ? cmp : -cmp;
    return 0;
  }

  function poolSortDate(el) {
    return el.getAttribute("data-pool-sort-date") || "";
  }

  function compareLastTalk(a, b, direction) {
    const cmp = compareIsoDates(poolSortDate(a), poolSortDate(b), direction);
    if (cmp !== 0) return cmp;
    return compareName(a, b, "asc");
  }

  function compareStatus(a, b, direction) {
    const tierA = STATUS_TIER[a.getAttribute("data-pool-status")] ?? 9;
    const tierB = STATUS_TIER[b.getAttribute("data-pool-status")] ?? 9;
    const cmp = tierA - tierB;
    if (cmp !== 0) return direction === "desc" ? -cmp : cmp;
    return compareName(a, b, "asc");
  }

  function getItems(wrap) {
    return Array.from(wrap.querySelectorAll(".speaker-pool-row[data-pool-status]"));
  }

  function getListParent(wrap) {
    return wrap.querySelector("tbody") || wrap.querySelector(".speaker-pool-compact-list");
  }

  function defaultDirection(column) {
    if (column === "name") return "asc";
    if (column === "last_talk") return "desc";
    if (column === "status") return "asc";
    return "asc";
  }

  function updateHeaderIndicators(wrap, column, direction) {
    wrap.querySelectorAll(".speaker-pool-sortable").forEach(function (btn) {
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

  function applySortFilter(wrap, state) {
    const filterSelect = wrap.querySelector(".speaker-pool-filter-status");
    const searchInput = wrap.querySelector(".speaker-pool-name-search");
    const emptyEl = wrap.querySelector(".speaker-pool-filter-empty");
    const parent = getListParent(wrap);
    if (!parent) return;

    const filterStatus = filterSelect ? filterSelect.value : "";
    const searchQuery = searchInput ? searchInput.value.trim().toLowerCase() : "";
    let items = getItems(wrap);

    if (filterStatus) {
      items = items.filter(function (el) {
        const status = el.getAttribute("data-pool-status");
        if (filterStatus === "recent") {
          return status === "recent" || status === "upcoming";
        }
        return status === filterStatus;
      });
    }

    if (searchQuery) {
      items = items.filter(function (el) {
        return (el.getAttribute("data-pool-name") || "").includes(searchQuery);
      });
    }

    if (state.column) {
      items.sort(function (a, b) {
        if (state.column === "name") return compareName(a, b, state.direction);
        if (state.column === "last_talk") return compareLastTalk(a, b, state.direction);
        if (state.column === "status") return compareStatus(a, b, state.direction);
        return compareAvailability(a, b);
      });
      items.forEach(function (el) {
        parent.appendChild(el);
      });
    }

    getItems(wrap).forEach(function (el) {
      let visible = true;
      if (filterStatus) {
        const status = el.getAttribute("data-pool-status");
        visible =
          filterStatus === "recent"
            ? status === "recent" || status === "upcoming"
            : status === filterStatus;
      }
      if (visible && searchQuery) {
        visible = (el.getAttribute("data-pool-name") || "").includes(searchQuery);
      }
      el.classList.toggle("d-none", !visible);
    });

    if (emptyEl) {
      emptyEl.classList.toggle("d-none", items.length > 0);
    }
  }

  function initWrap(wrap) {
    const filterSelect = wrap.querySelector(".speaker-pool-filter-status");
    const searchInput = wrap.querySelector(".speaker-pool-name-search");
    const sortButtons = wrap.querySelectorAll(".speaker-pool-sortable");
    if (!sortButtons.length && !filterSelect && !searchInput) return;

    const state = { column: null, direction: "asc" };

    function refresh() {
      applySortFilter(wrap, state);
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

    if (filterSelect) filterSelect.addEventListener("change", refresh);
    if (searchInput) searchInput.addEventListener("input", refresh);
    refresh();
  }

  document.querySelectorAll("[data-speaker-pool-list]").forEach(initWrap);

  window.SpeakerPoolControls = { applySortFilter: applySortFilter };
  window.AppDateSort = { compareIsoDates: compareIsoDates };
})();
