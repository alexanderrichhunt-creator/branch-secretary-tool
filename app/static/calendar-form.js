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

  function setAllDayState(formRoot, allDay) {
    const timeRow = formRoot.querySelector(".cal-time-row");
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

    init: function (modalEl) {
      this.modal = modalEl ? new bootstrap.Modal(modalEl) : null;
      if (!modalEl) return;
      bindRecurrenceControls(modalEl);
      bindAllDayControls(modalEl);
      setAllDayState(modalEl.querySelector("#cal-pane-event"), false);
    },

    open: function (opts) {
      if (!this.modal) return;
      const start = opts.start instanceof Date ? opts.start : new Date();
      let end = opts.end instanceof Date ? opts.end : new Date(start.getTime() + 60 * 60 * 1000);
      const allDay = !!opts.allDay;

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
