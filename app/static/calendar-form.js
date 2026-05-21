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

  function toDateInputValueUTC(d) {
    return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate());
  }

  function resolveDateValue(start, allDay, dateStr) {
    if (dateStr && dateStr.length >= 10) {
      return dateStr.slice(0, 10);
    }
    if (allDay && start instanceof Date) {
      return toDateInputValueUTC(start);
    }
    return toDateInputValue(start instanceof Date ? start : new Date());
  }

  function dateFromParts(dateValue) {
    const parts = dateValue.split("-");
    if (parts.length !== 3) return new Date();
    return new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
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
    document.querySelectorAll("#calEventForm textarea, #calInterviewForm textarea, #calTalkForm textarea").forEach(function (el) {
      el.value = "";
    });
    const talkForm = document.getElementById("calTalkForm");
    if (talkForm) {
      talkForm.querySelectorAll('input[type="text"]').forEach(function (el) {
        el.value = "";
      });
      const member = talkForm.querySelector('[name="member_id"]');
      if (member) member.value = "";
      const assigned = talkForm.querySelector("#cal_talk_kind_assigned");
      if (assigned) assigned.checked = true;
    }
  }

  function dispatchTalkDateChange() {
    const talkForm = document.getElementById("calTalkForm");
    if (!talkForm) return;
    const dateInput = talkForm.querySelector('[name="talk_date"]');
    if (dateInput) {
      dateInput.dispatchEvent(new Event("change", { bubbles: true }));
    }
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
    document.querySelectorAll(".cal-event-date, .cal-talk-date").forEach(function (el) {
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

    openFromCalendar: function (start, end, allDay, dateStr) {
      this.open({
        start: start,
        end: end,
        allDay: allDay,
        dateStr: dateStr,
      });
    },

    open: function (opts) {
      if (!this.modal) return;
      const allDay = !!opts.allDay;
      let start = opts.start instanceof Date ? new Date(opts.start) : new Date();
      let end = opts.end instanceof Date ? new Date(opts.end) : new Date(start.getTime() + 60 * 60 * 1000);

      resetCreateForms();

      const dateValue = resolveDateValue(start, allDay, opts.dateStr);
      syncDates(dateValue);

      const titleDate = dateFromParts(dateValue);

      if (allDay) {
        syncTimes("09:00", "10:00");
      } else {
        if (end <= start) {
          end = new Date(start.getTime() + 60 * 60 * 1000);
        }
        syncTimes(toTimeInputValue(start), toTimeInputValue(end));
      }

      const allDayBox = document.getElementById("all_day_event");
      const eventPane = document.getElementById("cal-pane-event");
      if (allDayBox && eventPane) {
        allDayBox.checked = allDay;
        setAllDayState(eventPane, allDay);
      }

      if (this.modalTitleEl) {
        this.modalTitleEl.textContent = "Add to calendar — " + formatDayLabel(titleDate);
      }

      const freq = document.querySelector(".cal-recurrence-freq");
      if (freq) {
        freq.value = "none";
        toggleWeeklyDays(false);
      }
      document.querySelectorAll('input[name="recurrence_byweekday"]').forEach(function (el) {
        el.checked = false;
      });
      const dayBox = document.querySelector(
        'input[name="recurrence_byweekday"][value="' + weekdayCode(titleDate) + '"]'
      );
      if (dayBox) dayBox.checked = true;

      dispatchTalkDateChange();
      this.modal.show();
    },
  };

  window.CalCreateForm = CalCreateForm;
})();
