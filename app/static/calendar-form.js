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
      talkForm.querySelectorAll('input[type="text"]:not(.member-filter-input)').forEach(function (el) {
        el.value = "";
      });
      const talkMember = talkForm.querySelector('[name="member_id"]');
      if (talkMember) talkMember.value = "";
      const assigned = talkForm.querySelector("#cal_talk_kind_assigned");
      if (assigned) assigned.checked = true;
    }
    if (window.MemberSelectFilter) {
      window.MemberSelectFilter.resetWithin(document.getElementById("calCreateModal"));
    }
    const suggestedTalkId = document.getElementById("cal_suggested_talk_id");
    if (suggestedTalkId) suggestedTalkId.value = "";
    const calSuggestedForm = document.getElementById("cal-suggested-talk-add-form");
    if (calSuggestedForm) {
      calSuggestedForm.reset();
      showCalSuggestedError("");
    }
  }

  function showCalSuggestedError(message) {
    const el = document.querySelector(".cal-suggested-modal-error");
    if (!el) return;
    if (!message) {
      el.classList.add("d-none");
      el.textContent = "";
      return;
    }
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function activateCreateTab(tabId) {
    const tabBtn = document.getElementById(tabId);
    if (!tabBtn) return;
    if (window.bootstrap && bootstrap.Tab) {
      try {
        bootstrap.Tab.getOrCreateInstance(tabBtn).show();
        return;
      } catch (e) {
        /* fall through to native click */
      }
    }
    tabBtn.click();
  }

  function fillTalkFromSuggestion(suggestion) {
    const form = document.getElementById("calTalkForm");
    if (!form || !suggestion) return;

    const idField = document.getElementById("cal_suggested_talk_id");
    if (idField) idField.value = suggestion.id ? String(suggestion.id) : "";

    const member = form.querySelector('[name="member_id"]');
    if (member) {
      member.value = suggestion.member_id ? String(suggestion.member_id) : "";
      member.dispatchEvent(new Event("change", { bubbles: true }));
    }

    const speakerText = document.getElementById("cal_talk_speaker_text");
    if (speakerText) speakerText.value = suggestion.speaker_text || "";

    const topic = document.getElementById("cal_talk_topic");
    if (topic) topic.value = suggestion.topic || "";

    const notes = document.getElementById("cal_talk_notes");
    if (notes) notes.value = suggestion.notes || "";

    const sortOrder = form.querySelector('[name="sort_order"]');
    if (sortOrder) {
      sortOrder.value =
        suggestion.sort_order && suggestion.sort_order > 0 ? String(suggestion.sort_order) : "";
    }

    const assigned = form.querySelector("#cal_talk_kind_assigned");
    if (assigned) assigned.checked = true;
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
    document.querySelectorAll(".cal-event-date, .cal-talk-date, .cal-suggested-date").forEach(function (el) {
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

  function showFormError(selector, message) {
    const el = document.querySelector(selector);
    if (!el) return;
    if (!message) {
      el.classList.add("d-none");
      el.textContent = "";
      return;
    }
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function showCalTalkError(message) {
    showFormError(".cal-talk-form-error", message);
  }

  function clearCalendarFormErrors() {
    showFormError(".cal-talk-form-error", "");
    showFormError(".cal-event-form-error", "");
    showFormError(".cal-interview-form-error", "");
    showCalSuggestedError("");
  }

  function afterCalendarSaveSuccess() {
    if (window.CalCreateForm && window.CalCreateForm.modal) {
      window.CalCreateForm.modal.hide();
    }
    if (window.branchCalendar && window.branchCalendar.refetchEvents) {
      window.branchCalendar.refetchEvents();
    }
    if (window.SuggestedTalks && window.SuggestedTalks.refresh) {
      window.SuggestedTalks.refresh();
    }
    resetCreateForms();
  }

  function bindCalendarAjaxForm(form, errorSelector) {
    if (!form || form.dataset.ajaxBound) return;
    if (!form.querySelector('[name="respond_json"]')) return;
    form.dataset.ajaxBound = "1";
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      showFormError(errorSelector, "");
      const submitBtn = form.querySelector('[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;
      try {
        const res = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
        });
        const data = await res.json().catch(function () {
          return {};
        });
        if (!res.ok || !data.ok) {
          showFormError(errorSelector, data.error || "Could not save.");
          return;
        }
        afterCalendarSaveSuccess();
      } catch (e) {
        showFormError(errorSelector, "Could not save.");
      } finally {
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  function bindCalendarAjaxForms() {
    bindCalendarAjaxForm(document.getElementById("calTalkForm"), ".cal-talk-form-error");
    bindCalendarAjaxForm(document.getElementById("calEventForm"), ".cal-event-form-error");
    bindCalendarAjaxForm(document.getElementById("calInterviewForm"), ".cal-interview-form-error");
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
      bindCalendarAjaxForms();
      setAllDayState(modalEl.querySelector("#cal-pane-event"), false);
      setAllDayState(modalEl.querySelector("#cal-pane-interview"), false);
    },

    openFromCalendar: function (start, end, allDay, dateStr, extra) {
      this.open(
        Object.assign(
          {
            start: start,
            end: end,
            allDay: allDay,
            dateStr: dateStr,
          },
          extra || {}
        )
      );
    },

    openForSuggestion: function (suggestion, dateStr) {
      const start = dateStr ? dateFromParts(dateStr) : new Date();
      this.open({
        start: start,
        end: start,
        allDay: true,
        dateStr: dateStr || "",
        tab: "cal-tab-talk",
        suggestion: suggestion,
      });
    },

    open: function (opts) {
      if (!this.modal) return;
      const allDay = !!opts.allDay;
      let start = opts.start instanceof Date ? new Date(opts.start) : new Date();
      let end = opts.end instanceof Date ? new Date(opts.end) : new Date(start.getTime() + 60 * 60 * 1000);

      resetCreateForms();
      clearCalendarFormErrors();

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

      if (opts.suggestion) {
        fillTalkFromSuggestion(opts.suggestion);
      }
      if (opts.tab) {
        activateCreateTab(opts.tab);
      } else {
        activateCreateTab("cal-tab-event");
      }

      dispatchTalkDateChange();
      this.modal.show();
    },
  };

  window.CalCreateForm = CalCreateForm;
  window.showCalSuggestedError = showCalSuggestedError;
})();
