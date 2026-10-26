(function () {
  function formatDateLong(d) {
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function parseIsoDate(iso) {
    if (!iso || String(iso).length < 10) return null;
    const parts = String(iso).slice(0, 10).split("-");
    if (parts.length !== 3) return null;
    const year = Number(parts[0]);
    const month = Number(parts[1]);
    const day = Number(parts[2]);
    if (!year || !month || !day) return null;
    return new Date(year, month - 1, day);
  }

  function sameCalendarDay(a, b) {
    return (
      a &&
      b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  function formatDateSpan(start, end) {
    if (!start) return "—";
    if (!end || sameCalendarDay(start, end)) return formatDateLong(start);
    if (start.getFullYear() === end.getFullYear()) {
      const startText = start.toLocaleDateString(undefined, {
        weekday: "long",
        month: "long",
        day: "numeric",
      });
      return startText + " – " + formatDateLong(end);
    }
    return formatDateLong(start) + " – " + formatDateLong(end);
  }

  function inclusiveDayCount(start, end) {
    const startDay = new Date(start.getFullYear(), start.getMonth(), start.getDate());
    const endDay = new Date(end.getFullYear(), end.getMonth(), end.getDate());
    return Math.round((endDay.getTime() - startDay.getTime()) / 86400000) + 1;
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
    lastProps: null,

    render: function (modalEl, fcEvent) {
      if (!modalEl || !fcEvent) return;

      const props = fcEvent.extendedProps || {};
      this.lastProps = props;
      const start = fcEvent.start;
      const end = fcEvent.end;
      const allDay = !!fcEvent.allDay;

      const title = props.fullTitle || fcEvent.title || "Event";
      const kindLabel = props.kindLabel || props.categoryLabel || "Calendar item";
      const accent = props.accentColor || fcEvent.backgroundColor || "#64748b";
      const rangeStart = parseIsoDate(props.startDate) || start;
      const rangeEnd = parseIsoDate(props.endDate) || (allDay ? null : end);
      const multiDay = !!props.multiDay || (rangeStart && rangeEnd && !sameCalendarDay(rangeStart, rangeEnd));

      let timeText = "All day";
      let durationText = "All day";
      let showDuration = true;

      if (!allDay && start) {
        timeText = formatTimeShort(start);
        if (end) {
          timeText += " – " + formatTimeShort(end);
          if (multiDay && rangeStart && rangeEnd) {
            const days = inclusiveDayCount(rangeStart, rangeEnd);
            durationText = days === 1 ? "1 day" : days + " days";
          } else {
            durationText =
              props.durationMinutes != null
                ? formatDurationMinutes(Number(props.durationMinutes))
                : durationFromRange(start, end, false) || "—";
          }
        } else if (props.durationMinutes != null) {
          durationText = formatDurationMinutes(Number(props.durationMinutes));
        } else {
          durationText = "—";
        }
      } else if (allDay && multiDay && rangeStart && rangeEnd) {
        const days = inclusiveDayCount(rangeStart, rangeEnd);
        durationText = days === 1 ? "1 day" : days + " days";
        showDuration = true;
      } else if (allDay) {
        showDuration = false;
      }

      if (props.kind === "cleaning") {
        timeText = "Sunday–Saturday";
        durationText = "1 week";
        showDuration = true;
      }

      modalEl.querySelector(".modal-title").textContent = title;

      const dateLabel = modalEl.querySelector(".cal-detail-date-label");
      if (dateLabel) {
        dateLabel.textContent = props.kind === "cleaning" ? "Week" : multiDay ? "Dates" : "Date";
      }

      const badge = modalEl.querySelector(".cal-detail-badge");
      if (badge) {
        badge.textContent = kindLabel;
        badge.style.backgroundColor = accent;
      }

      setText(
        modalEl.querySelector(".cal-detail-date"),
        rangeStart ? formatDateSpan(rangeStart, multiDay ? rangeEnd : rangeStart) : "—"
      );
      setText(modalEl.querySelector(".cal-detail-time"), timeText);
      setText(modalEl.querySelector(".cal-detail-duration"), durationText);
      toggleBlock(modalEl.querySelector(".cal-detail-duration-wrap"), showDuration);

      const subtitle = props.subtitle || "";
      toggleBlock(modalEl.querySelector(".cal-detail-subtitle-wrap"), !!subtitle);
      setText(modalEl.querySelector(".cal-detail-subtitle"), subtitle);

      const metaParts = [];
      if (props.kind === "talk") {
        if (props.sortOrder && props.sortOrder > 0) {
          metaParts.push(metaRow("Order", "#" + props.sortOrder));
        }
        if (props.topic) {
          metaParts.push(metaRow("Topic", props.topic));
        }
      }
      if (props.kind === "suggested_talk") {
        if (props.sortOrder && props.sortOrder > 0) {
          metaParts.push(metaRow("Order", "#" + props.sortOrder));
        }
        if (props.speakerLabel && props.speakerLabel !== "—") {
          metaParts.push(metaRow("Speaker", props.speakerLabel));
        }
        if (props.topic) metaParts.push(metaRow("Topic", props.topic));
      }
      if (props.kind === "interview") {
        if (props.interviewSubject) metaParts.push(metaRow("With", props.interviewSubject));
        if (props.interviewPurpose) metaParts.push(metaRow("Purpose", props.interviewPurpose));
      }
      if (props.kind === "cleaning" && props.cleaners) {
        metaParts.push(metaRow("People", props.cleaners));
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
      const scheduleBtn = modalEl.querySelector(".cal-schedule-suggestion-btn");
      const deleteBtn = modalEl.querySelector(".cal-delete-item-btn, .cal-delete-suggestion-btn");
      const canDelete = !!(props.deleteUrl || (props.kind === "suggested_talk" && props.suggestionId));
      if (deleteBtn) deleteBtn.classList.toggle("d-none", !canDelete);
      if (props.kind === "suggested_talk") {
        if (editLink) {
          editLink.textContent = "Edit suggestion";
          editLink.href = "#";
          editLink.classList.remove("btn-primary");
          editLink.classList.add("btn-outline-primary");
        }
        if (scheduleBtn) scheduleBtn.classList.remove("d-none");
      } else {
        if (editLink) {
          editLink.textContent = "Edit";
          editLink.href = props.editUrl || "#";
          editLink.classList.add("btn-primary");
          editLink.classList.remove("btn-outline-primary");
        }
        if (scheduleBtn) scheduleBtn.classList.add("d-none");
      }
    },
  };
})();
