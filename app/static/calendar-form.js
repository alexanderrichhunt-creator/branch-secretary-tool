(function () {
  const WEEKDAY_CODES = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];

  function pad(n) {
    return String(n).padStart(2, "0");
  }

  function toDateInputValue(d) {
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  function toTimeInputValue(d) {
    return pad(d.getHours()) + ":" + pad(d.getMinutes());
  }

  function weekdayCode(d) {
    return WEEKDAY_CODES[d.getDay()];
  }

  function formatDayLabel(d) {
    return d.toLocaleDateString(undefined, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  }

  function resetCreateForms() {
    const title = document.getElementById("event_title");
    if (title) title.value = "";
    const location = document.getElementById("event_location");
    if (location) location.value = "";
    const purpose = document.getElementById("interview_purpose");
    if (purpose) purpose.value = "Interview";
    const who = document.getElementById("cal_who_text");
    if (who) who.value = "";
    const member = document.getElementById("cal_member_id");
    if (member) member.value = "";
    const until = document.getElementById("recurrence_until");
    if (until) until.value = "";
    const category = document.getElementById("event_category");
    if (category) category.value = "";
    document.querySelectorAll("#calEventForm textarea, #calInterviewForm textarea").forEach(function (el) {
      el.value = "";
    });
  }

  function normalizeCalendarSelection(start, end, allDay) {
    const startDate = start instanceof Date ? new Date(start) : new Date();
    let endDate = end instanceof Date ? new Date(end) : new Date(startDate.getTime() + 60 * 60 * 1000);
    const spanMs = endDate.getTime() - startDate.getTime();

    if (allDay && spanMs <= 36 * 60 * 60 * 1000) {
      startDate.setHours(9, 0, 0, 0);
      endDate = new Date(startDate);
      endDate.setHours(10, 0, 0, 0);
      return { start: startDate, end: endDate, allDay: false };
    }

    if (!allDay && endDate <= startDate) {
      endDate = new Date(startDate.getTime() + 60 * 60 * 1000);
    }

    return { start: startDate, end: endDate, allDay: !!allDay };
  }

  function setAllDayState(formRoot, allDay) {
    if (!formRoot) return;
    const timeRow = formRoot.querySelector(":scope > .cal-time-row, .cal-time-row");
    const startInputs = formRoot.querySelectorAll(".cal-start-time");
    const endInputs = formRoot.querySelectorAll(".cal-end-time");
    if (timeRow) {
      timeRow.classList.toggle("d-none", allDay);
    }
    startInputs.forEach(function (el) {
      el.disabled = allDay;
      el.required = !allDay;
    });
    endInputs.forEach(function (el) {
      el.disabled = allDay;
      el.required = !allDay;
    });
  }

  function syncDates(dateValue) {
    document.querySelectorAll(".cal-event-date").forEach(function (el) {
      el.value = dateValue;
    });
  }

  function syncTimes(startValue, endValue) {
    document.querySelectorAll(".cal-start-time").forEach(function (el) {
      el.value = startValue;
    });
    document.querySelectorAll(".cal-end-time").forEach(function (el) {
      el.value = endValue;
    });
  }

  function toggleWeeklyDays(show, activeDayCode) {
    const wrap = document.querySelector(".cal-weekdays-wrap");
    if (!wrap) return;
    wrap.classList.toggle("d-none", !show);
    if (show && activeDayCode) {
      const box = wrap.querySelector('input[value="' + activeDayCode + '"]');
      if (box) box.checked = true;
    }
  }

  function bindRecurrenceControls(modalEl) {
    const freq = modalEl.querySelector(".cal-recurrence-freq");
    if (!freq || freq.dataset.bound) return;
    freq.dataset.bound = "1";
    freq.addEventListener("change", function () {
      toggleWeeklyDays(freq.value === "weekly");
    });
  }

  function bindAllDayControls(modalEl) {
    const checkbox = modalEl.querySelector("#all_day_event");
    const eventPane = modalEl.querySelector("#cal-pane-event");
    if (!checkbox || !eventPane || checkbox.dataset.bound) return;
    checkbox.dataset.bound = "1";
    checkbox.addEventListener("change", function () {
      setAllDayState(eventPane, checkbox.checked);
    });
  }

  const CalCreateForm = {
    modal: null,
    modalTitleEl: null,

    init: function (modalEl) {
      this.modal = modalEl ? new bootstrap.Modal(modalEl) : null;
      this.modalTitleEl = modalEl ? modalEl.querySelector("#calCreateModalLabel") : null;
      if (!modalEl) return;
      bindRecurrenceControls(modalEl);
      bindAllDayControls(modalEl);
      setAllDayState(modalEl.querySelector("#cal-pane-event"), false);
      setAllDayState(modalEl.querySelector("#cal-pane-interview"), false);
    },

    openFromCalendar: function (start, end, allDay) {
      const normalized = normalizeCalendarSelection(start, end, allDay);
      this.open(normalized);
    },

    open: function (opts) {
      if (!this.modal) return;
      const start = opts.start instanceof Date ? opts.start : new Date();
      let end = opts.end instanceof Date ? opts.end : new Date(start.getTime() + 60 * 60 * 1000);
      const allDay = !!opts.allDay;

      resetCreateForms();

      const dateValue = toDateInputValue(start);
      syncDates(dateValue);

      if (allDay) {
        syncTimes("09:00", "10:00");
      } else {
        syncTimes(toTimeInputValue(start), toTimeInputValue(end));
      }

      const allDayBox = document.getElementById("all_day_event");
      const eventPane = document.getElementById("cal-pane-event");
      if (allDayBox && eventPane) {
        allDayBox.checked = allDay;
        setAllDayState(eventPane, allDay);
      }

      if (this.modalTitleEl) {
        this.modalTitleEl.textContent = "Add to calendar — " + formatDayLabel(start);
      }

      const freq = document.querySelector(".cal-recurrence-freq");
      if (freq) {
        freq.value = "none";
        toggleWeeklyDays(false);
      }
      document.querySelectorAll('input[name="recurrence_byweekday"]').forEach(function (el) {
        el.checked = false;
      });
      const dayBox = document.querySelector('input[name="recurrence_byweekday"][value="' + weekdayCode(start) + '"]');
      if (dayBox) dayBox.checked = true;

      const talkLink = document.querySelector(".cal-add-talk-link");
      if (talkLink) {
        talkLink.href = talkLink.href.split("?")[0] + "?prefill_date=" + encodeURIComponent(dateValue);
      }

      this.modal.show();
    },
  };

  window.CalCreateForm = CalCreateForm;
})();
