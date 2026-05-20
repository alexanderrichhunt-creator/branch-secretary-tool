(function () {
  const dataEl = document.getElementById("member-talk-recency-data");
  if (!dataEl) return;

  let recency = {};
  try {
    recency = JSON.parse(dataEl.textContent || "{}");
  } catch (e) {
    return;
  }

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

  function bindForm(form) {
    const select = form.querySelector('[name="member_id"]');
    const alertEl = form.querySelector(".speaker-recency-alert");
    if (!select || !alertEl) return;

    function showAlert(level, message) {
      alertEl.className = "speaker-recency-alert alert alert-" + level + " py-1 px-2 small mt-1 mb-0";
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
        showAlert("success", "No prior talk — OK to schedule.");
        return;
      }

      const days = info.days_since;
      const when = formatTimeAgo(days);
      const onDate = formatDate(info.last_talk_date);

      if (days <= RED_MAX_DAYS) {
        showAlert("danger", "Last spoke " + when + " — may be too soon.");
      } else if (days <= YELLOW_MAX_DAYS) {
        showAlert("warning", "Last spoke " + when + " — consider waiting.");
      } else {
        showAlert("success", "Last spoke " + when + " — OK to schedule.");
      }
    }

    select.addEventListener("change", updateRecencyAlert);
    updateRecencyAlert();
  }

  document.querySelectorAll(".talk-add-form").forEach(bindForm);
})();
