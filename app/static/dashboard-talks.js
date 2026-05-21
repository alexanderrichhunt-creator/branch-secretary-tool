(function () {
  const modalEl = document.getElementById("dashboardAddTalkModal");
  if (!modalEl) return;

  const dateInput = document.getElementById("dashboard_add_talk_date");
  const titleEl = document.getElementById("dashboardAddTalkModalLabel");

  document.querySelectorAll("[data-add-talk-date]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const iso = btn.getAttribute("data-add-talk-date") || "";
      const label = btn.getAttribute("data-add-talk-label") || "Add talk";
      if (dateInput && iso) dateInput.value = iso;
      if (titleEl) titleEl.textContent = label;
    });
  });
})();
