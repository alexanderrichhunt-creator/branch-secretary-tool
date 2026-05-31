(function () {
  function formatDateLong(d) {
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatTimeShort(d) {
    return d.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  }

  function formatDurationMinutes(minutes) {
    if (!minutes || minutes <= 0) return "—";
    if (minutes < 60) {
      return minutes === 1 ? "1 minute" : minutes + " minutes";
    }
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (mins === 0) {
      return hours === 1 ? "1 hour" : hours + " hours";
    }
    return hours + " hr " + mins + " min";
  }

  function durationFromRange(start, end, allDay) {
    if (allDay || !start || !end) return null;
    const minutes = Math.max(1, Math.round((end.getTime() - start.getTime()) / 60000));
    return formatDurationMinutes(minutes);
  }

  function setText(el, text) {
    if (!el) return;
    el.textContent = text || "";
  }

  function setHtml(el, html) {
    if (!el) return;
    el.innerHTML = html;
  }

  function toggleBlock(el, show) {
    if (!el) return;
    el.classList.toggle("d-none", !show);
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function metaRow(label, value) {
    if (!value) return "";
    return (
      '<div class="cal-detail-meta-row">' +
      '<span class="cal-detail-meta-label">' +
      escapeHtml(label) +
      "</span>" +
      '<span class="cal-detail-meta-value">' +
      escapeHtml(value) +
      "</span></div>"
    );
  }

  window.CalEventDetail = {
    render: function (modalEl, fcEvent) {
      if (!modalEl || !fcEvent) return;

      const props = fcEvent.extendedProps || {};
      const start = fcEvent.start;
      const end = fcEvent.end;
      const allDay = !!fcEvent.allDay;

      const title = props.fullTitle || fcEvent.title || "Event";
      const kindLabel = props.kindLabel || props.categoryLabel || "Calendar item";
      const accent = props.accentColor || fcEvent.backgroundColor || "#64748b";

      let timeText = "All day";
      let durationText = "All day";
      let showDuration = true;

      if (!allDay && start) {
        timeText = formatTimeShort(start);
        if (end) {
          timeText += " – " + formatTimeShort(end);
          durationText =
            props.durationMinutes != null
              ? formatDurationMinutes(Number(props.durationMinutes))
              : durationFromRange(start, end, false) || "—";
        } else if (props.durationMinutes != null) {
          durationText = formatDurationMinutes(Number(props.durationMinutes));
        } else {
          durationText = "—";
        }
      } else if (allDay) {
        showDuration = false;
      }

      modalEl.querySelector(".modal-title").textContent = title;

      const badge = modalEl.querySelector(".cal-detail-badge");
      if (badge) {
        badge.textContent = kindLabel;
        badge.style.backgroundColor = accent;
      }

      setText(modalEl.querySelector(".cal-detail-date"), start ? formatDateLong(start) : "—");
      setText(modalEl.querySelector(".cal-detail-time"), timeText);
      setText(modalEl.querySelector(".cal-detail-duration"), durationText);
      toggleBlock(modalEl.querySelector(".cal-detail-duration-wrap"), showDuration);

      const subtitle = props.subtitle || "";
      toggleBlock(modalEl.querySelector(".cal-detail-subtitle-wrap"), !!subtitle);
      setText(modalEl.querySelector(".cal-detail-subtitle"), subtitle);

      const metaParts = [];
      if (props.kind === "talk" && props.topic) {
        metaParts.push(metaRow("Topic", props.topic));
      }
      if (props.kind === "interview") {
        if (props.interviewSubject) metaParts.push(metaRow("With", props.interviewSubject));
        if (props.interviewPurpose) metaParts.push(metaRow("Purpose", props.interviewPurpose));
      }
      if (props.location) {
        metaParts.push(metaRow("Location", props.location));
      }
      if (props.recurrence) {
        metaParts.push(metaRow("Repeats", props.recurrence));
      }
      if (props.categoryLabel && props.kind === "event" && props.categoryLabel !== kindLabel) {
        metaParts.push(metaRow("Category", props.categoryLabel));
      }

      const metaEl = modalEl.querySelector(".cal-detail-meta");
      if (metaEl) {
        if (metaParts.length) {
          metaEl.innerHTML = metaParts.join("");
          metaEl.classList.remove("d-none");
        } else {
          metaEl.innerHTML = "";
          metaEl.classList.add("d-none");
        }
      }

      const notes = (props.notes || "").trim();
      toggleBlock(modalEl.querySelector(".cal-detail-notes-wrap"), !!notes);
      setText(modalEl.querySelector(".cal-detail-notes"), notes);

      const editLink = modalEl.querySelector(".cal-edit-link");
      if (editLink) {
        editLink.href = props.editUrl || "#";
      }
    },
  };
})();
