(function () {
  const STATUS_TIER = { never: 0, available: 1, consider: 2, recent: 3 };

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
    if (status === "available" || status === "recent") {
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

  function compareLastTalk(a, b, direction) {
    const daysA = poolDays(a);
    const daysB = poolDays(b);
    const rankA = daysA === null ? Number.MAX_SAFE_INTEGER : daysA;
    const rankB = daysB === null ? Number.MAX_SAFE_INTEGER : daysB;
    if (direction === "asc") {
      if (rankA !== rankB) return rankB - rankA;
    } else if (rankA !== rankB) {
      return rankA - rankB;
    }
    return compareName(a, b, "asc");
  }

  function getItems(wrap) {
    return Array.from(
      wrap.querySelectorAll(".speaker-pool-row[data-pool-status], .speaker-pool-compact-row[data-pool-status]")
    );
  }

  function getListParent(wrap) {
    return wrap.querySelector("tbody") || wrap.querySelector(".speaker-pool-compact-list");
  }

  function applySortFilter(wrap) {
    const sortSelect = wrap.querySelector(".speaker-pool-sort");
    const filterSelect = wrap.querySelector(".speaker-pool-filter-status");
    const emptyEl = wrap.querySelector(".speaker-pool-filter-empty");
    const parent = getListParent(wrap);
    if (!parent) return;

    const sortBy = sortSelect ? sortSelect.value : "availability";
    const filterStatus = filterSelect ? filterSelect.value : "";
    let items = getItems(wrap);

    if (filterStatus) {
      items = items.filter(function (el) {
        return el.getAttribute("data-pool-status") === filterStatus;
      });
    }

    items.sort(function (a, b) {
      if (sortBy === "name_asc") return compareName(a, b, "asc");
      if (sortBy === "name_desc") return compareName(a, b, "desc");
      if (sortBy === "last_talk_asc") return compareLastTalk(a, b, "asc");
      if (sortBy === "last_talk_desc") return compareLastTalk(a, b, "desc");
      return compareAvailability(a, b);
    });

    items.forEach(function (el) {
      parent.appendChild(el);
    });

    getItems(wrap).forEach(function (el) {
      const visible = !filterStatus || el.getAttribute("data-pool-status") === filterStatus;
      el.classList.toggle("d-none", !visible);
    });

    if (emptyEl) {
      emptyEl.classList.toggle("d-none", items.length > 0);
    }
  }

  function initWrap(wrap) {
    const sortSelect = wrap.querySelector(".speaker-pool-sort");
    const filterSelect = wrap.querySelector(".speaker-pool-filter-status");
    if (!sortSelect && !filterSelect) return;

    function refresh() {
      applySortFilter(wrap);
    }

    if (sortSelect) sortSelect.addEventListener("change", refresh);
    if (filterSelect) filterSelect.addEventListener("change", refresh);
    refresh();
  }

  document.querySelectorAll("[data-speaker-pool-list]").forEach(initWrap);

  window.SpeakerPoolControls = { applySortFilter: applySortFilter };
})();
