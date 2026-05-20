(function () {
  const select = document.getElementById("member_id");
  const alertEl = document.getElementById("speaker-recency-alert");
  const dataEl = document.getElementById("member-talk-recency-data");
  if (!select || !alertEl || !dataEl) return;

  let recency = {};
  try {
    recency = JSON.parse(dataEl.textContent || "{}");
  } catch (e) {
    return;
  }

  // Match dashboard: ~6 months = 183 days; ~3 months = 92 days.
  const RED_MAX_DAYS = 92;
  const YELLOW_MAX_DAYS = 183;

  function formatTimeAgo(days) {
    if (days <= 0) return "today";
    if (days === 1) return "1 day ago";
    if (days < 45) return days + " days ago";
    const months = Math.round(days / 30.44);
    if (months === 1) return "about 1 month ago";
    return "about " + months + " months ago";
  }

  function formatDate(iso) {
    const parts = iso.split("-");
    if (parts.length !== 3) return iso;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

  function showAlert(level, message) {
    alertEl.className = "alert mt-2 alert-" + level;
    alertEl.textContent = message;
    alertEl.classList.remove("d-none");
  }

  function hideAlert() {
    alertEl.classList.add("d-none");
    alertEl.textContent = "";
  }

  function updateRecencyAlert() {
    const id = select.value;
    if (!id) {
      hideAlert();
      return;
    }

    const info = recency[id];
    if (!info || !info.last_talk_date) {
      showAlert(
        "success",
        "No prior talk on record — OK to ask this person to speak."
      );
      return;
    }

    const days = info.days_since;
    const when = formatTimeAgo(days);
    const onDate = formatDate(info.last_talk_date);

    if (days <= RED_MAX_DAYS) {
      showAlert(
        "danger",
        "Last spoke " + when + " (" + onDate + ") — may be too soon to ask again."
      );
    } else if (days <= YELLOW_MAX_DAYS) {
      showAlert(
        "warning",
        "Last spoke " + when + " (" + onDate + ") — consider waiting a bit longer if you can."
      );
    } else {
      showAlert(
        "success",
        "Last spoke " + when + " (" + onDate + ") — good spacing; OK to schedule."
      );
    }
  }

  select.addEventListener("change", updateRecencyAlert);
  updateRecencyAlert();
})();
