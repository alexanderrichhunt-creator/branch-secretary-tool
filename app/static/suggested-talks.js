(function () {
  const listEl = document.getElementById("suggested-talk-list");
  const addForm = document.getElementById("suggested-talk-add-form");
  const calAddForm = document.getElementById("cal-suggested-talk-add-form");
  const editForm = document.getElementById("suggested-talk-edit-form");
  const editModalEl = document.getElementById("suggestedTalkEditModal");
  const editSaveBtn = document.getElementById("suggestedTalkEditSaveBtn");
  const countBadge = document.querySelector(".cal-suggested-count");
  const dateFilterEl = document.getElementById("suggested_date_filter");
  const dateFilterClearBtn = document.getElementById("suggested_date_filter_clear");
  const addDateEl = document.getElementById("suggested_date");

  if (!listEl && !addForm && !calAddForm) return;

  const editModal = editModalEl && window.bootstrap ? new bootstrap.Modal(editModalEl) : null;

  if (editModalEl && !editModalEl.dataset.memberFilterRecaptureBound) {
    editModalEl.dataset.memberFilterRecaptureBound = "1";
    editModalEl.addEventListener("shown.bs.modal", function () {
      if (window.MemberSelectFilter && window.MemberSelectFilter.recaptureWithin) {
        window.MemberSelectFilter.recaptureWithin(editModalEl);
      }
    });
  }

  function escapeHtml(text) {
    return String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function showFormError(el, message) {
    if (!el) return;
    if (!message) {
      el.classList.add("d-none");
      el.textContent = "";
      return;
    }
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function updateCount(count) {
    if (countBadge) countBadge.textContent = String(count);
  }

  function currentFilterDate() {
    return dateFilterEl && dateFilterEl.value ? dateFilterEl.value : "";
  }

  function refreshCalendar() {
    if (window.refreshBranchCalendar) {
      window.refreshBranchCalendar();
    } else if (window.branchCalendar && window.branchCalendar.refetchEvents) {
      window.branchCalendar.refetchEvents();
    }
  }

  function resetSuggestedSlots(form) {
    if (!form) return;
    form.querySelectorAll(".cal-suggested-slot").forEach(function (slot, index) {
      slot.classList.toggle("d-none", index > 0);
    });
    const addBtn = form.querySelector(".cal-add-suggested-slot");
    if (addBtn) addBtn.classList.remove("d-none");
  }

  function visibleSuggestedSlots(form) {
    return Array.from(form.querySelectorAll(".cal-suggested-slot")).filter(function (slot) {
      return !slot.classList.contains("d-none");
    });
  }

  function bindSuggestedSlotControls(form) {
    if (!form || form.dataset.suggestedSlotsBound) return;
    form.dataset.suggestedSlotsBound = "1";

    const addBtn = form.querySelector(".cal-add-suggested-slot");
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        const hidden = form.querySelector(".cal-suggested-slot.d-none");
        if (!hidden) {
          addBtn.classList.add("d-none");
          return;
        }
        hidden.classList.remove("d-none");
        if (window.MemberSelectFilter) {
          window.MemberSelectFilter.bindWithin(hidden);
        }
        if (!form.querySelector(".cal-suggested-slot.d-none")) {
          addBtn.classList.add("d-none");
        }
      });
    }

    form.querySelectorAll(".cal-remove-suggested-slot").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const slot = btn.closest(".cal-suggested-slot");
        if (!slot) return;
        slot.querySelectorAll(".member-filter-input").forEach(function (input) {
          if (typeof input._memberFilterReset === "function") {
            input._memberFilterReset();
          } else {
            input.value = "";
          }
        });
        slot.querySelectorAll(".cal-suggested-speaker-text, .cal-suggested-topic-input").forEach(function (el) {
          el.value = "";
        });
        const slots = Array.from(form.querySelectorAll(".cal-suggested-slot"));
        if (slots.indexOf(slot) <= 0) return;
        slot.classList.add("d-none");
        if (addBtn) addBtn.classList.remove("d-none");
      });
    });
  }

  function collectSuggestedSpeakers(form) {
    const speakers = [];
    visibleSuggestedSlots(form).forEach(function (slot) {
      const slotNum = Number(slot.getAttribute("data-slot") || "0");
      const memberSelect = slot.querySelector("select");
      const speakerText = slot.querySelector(".cal-suggested-speaker-text");
      const topic = slot.querySelector(".cal-suggested-topic-input");
      const memberId = memberSelect ? memberSelect.value : "";
      const text = speakerText ? speakerText.value.trim() : "";
      const topicText = topic ? topic.value.trim() : "";
      if (!memberId && !text && !topicText) return;
      speakers.push({
        member_id: memberId || null,
        speaker_text: text || null,
        topic: topicText,
        sort_order: slotNum,
      });
    });
    return speakers;
  }

  function notesFieldForForm(form) {
    if (form.id === "cal-suggested-talk-add-form") {
      return document.getElementById("cal_suggested_notes");
    }
    return document.getElementById("suggested_notes");
  }

  function dateFieldForForm(form) {
    if (form.id === "cal-suggested-talk-add-form") {
      return document.getElementById("cal_suggested_date");
    }
    return document.getElementById("suggested_date");
  }

  async function submitSuggestedBatch(form, errorSelector, onSuccess) {
    const errorEl = form.querySelector(errorSelector);
    showFormError(errorEl, "");
    const dateInput = dateFieldForForm(form);
    const notesInput = notesFieldForForm(form);
    const speakers = collectSuggestedSpeakers(form);

    try {
      const res = await fetch("/api/suggested-talks/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          suggested_date: dateInput ? dateInput.value : "",
          notes: notesInput ? notesInput.value : "",
          speakers: speakers,
        }),
      });
      const data = await res.json().catch(function () {
        return {};
      });
      if (!res.ok || !data.ok) {
        showFormError(errorEl, data.error || "Could not save.");
        return;
      }
      if (onSuccess) await onSuccess(data);
      refreshCalendar();
    } catch (e) {
      showFormError(errorEl, "Could not save.");
    }
  }

  function setSelectedDate(dateStr) {
    const value = dateStr || "";
    if (addDateEl && value) addDateEl.value = value;
    if (dateFilterEl) dateFilterEl.value = value;
    const calSuggestedDate = document.getElementById("cal_suggested_date");
    if (calSuggestedDate && value) calSuggestedDate.value = value;
    if (listEl) refreshList();
  }

  async function openEdit(id) {
    const suggestion = await fetchSuggestion(id);
    document.getElementById("suggested_edit_id").value = suggestion.id;
    document.getElementById("suggested_edit_date").value = suggestion.suggested_date || "";
    document.getElementById("suggested_edit_member_id").value = suggestion.member_id
      ? String(suggestion.member_id)
      : "";
    document.getElementById("suggested_edit_speaker_text").value = suggestion.speaker_text || "";
    document.getElementById("suggested_edit_topic").value = suggestion.topic || "";
    document.getElementById("suggested_edit_notes").value = suggestion.notes || "";
    const editSortOrder = document.getElementById("suggested_edit_sort_order");
    if (editSortOrder) {
      editSortOrder.value =
        suggestion.sort_order && suggestion.sort_order > 0 ? String(suggestion.sort_order) : "";
    }
    document.getElementById("suggested_edit_member_filter").value = "";
    if (window.MemberSelectFilter) window.MemberSelectFilter.resetAll();
    const editMember = document.getElementById("suggested_edit_member_id");
    if (editMember) editMember.dispatchEvent(new Event("change", { bubbles: true }));
    showFormError(editForm.querySelector(".cal-suggested-edit-error"), "");
    if (editModal) editModal.show();
  }

  function renderSuggestionItem(item) {
    const dateHtml = item.suggested_date_display
      ? '<div class="cal-suggested-date small fw-semibold text-primary">' +
        escapeHtml(item.suggested_date_display) +
        "</div>"
      : "";
    const topicHtml = item.topic
      ? '<div class="cal-suggested-topic small">' + escapeHtml(item.topic) + "</div>"
      : "";
    const notesHtml = item.notes
      ? '<div class="cal-suggested-notes small muted">' + escapeHtml(item.notes) + "</div>"
      : "";
    const orderHtml =
      item.sort_order && item.sort_order > 0
        ? '<span class="cal-suggested-order text-muted me-1">#' + escapeHtml(item.sort_order) + "</span>"
        : "";

    return (
      '<div class="cal-suggested-item" data-suggestion-id="' +
      item.id +
      '">' +
      '<div class="cal-suggested-item-main">' +
      dateHtml +
      '<div class="cal-suggested-speaker fw-semibold">' +
      orderHtml +
      escapeHtml(item.speaker_label || "—") +
      "</div>" +
      topicHtml +
      notesHtml +
      "</div>" +
      '<div class="cal-suggested-item-actions">' +
      '<button type="button" class="btn btn-sm btn-primary cal-suggested-schedule-btn">Schedule</button>' +
      '<button type="button" class="btn btn-sm btn-outline-secondary cal-suggested-edit-btn">Edit</button>' +
      '<button type="button" class="btn btn-sm btn-outline-danger cal-suggested-delete-btn">Remove</button>' +
      "</div></div>"
    );
  }

  function renderList(items) {
    if (!listEl) return;
    updateCount(items.length);
    if (!items.length) {
      const filterDate = currentFilterDate();
      listEl.innerHTML =
        '<div class="cal-suggested-empty muted small">' +
        (filterDate
          ? "No suggestions for this date yet. Add a speaker above."
          : "No suggestions yet. Pick a date and add a speaker above.") +
        "</div>";
      return;
    }
    listEl.innerHTML = items.map(renderSuggestionItem).join("");
  }

  async function refreshList() {
    if (!listEl) return;
    try {
      const filterDate = currentFilterDate();
      const url = filterDate
        ? "/api/suggested-talks?date=" + encodeURIComponent(filterDate)
        : "/api/suggested-talks";
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      renderList(data.suggestions || []);
    } catch (e) {
      /* ignore */
    }
  }

  async function fetchSuggestion(id) {
    const res = await fetch("/api/suggested-talks/" + encodeURIComponent(id));
    if (!res.ok) throw new Error("Could not load suggestion.");
    return res.json();
  }

  function resetAddForm() {
    if (!addForm) return;
    const keepDate = addDateEl ? addDateEl.value : "";
    const keepNotes = document.getElementById("suggested_notes")?.value || "";
    resetSuggestedSlots(addForm);
    addForm.querySelectorAll(".cal-suggested-speaker-text, .cal-suggested-topic-input").forEach(function (el) {
      el.value = "";
    });
    if (addDateEl && keepDate) addDateEl.value = keepDate;
    const notesEl = document.getElementById("suggested_notes");
    if (notesEl) notesEl.value = keepNotes;
    showFormError(addForm.querySelector(".cal-suggested-form-error"), "");
    if (window.MemberSelectFilter) window.MemberSelectFilter.resetWithin(addForm);
  }

  if (addForm) {
    bindSuggestedSlotControls(addForm);
    addForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      await submitSuggestedBatch(addForm, ".cal-suggested-form-error", async function () {
        if (dateFilterEl && addDateEl && addDateEl.value) {
          dateFilterEl.value = addDateEl.value;
        }
        resetAddForm();
        await refreshList();
      });
    });
  }

  if (calAddForm) {
    bindSuggestedSlotControls(calAddForm);
    calAddForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      await submitSuggestedBatch(calAddForm, ".cal-suggested-modal-error", async function () {
        const dateInput = document.getElementById("cal_suggested_date");
        const dateValue = dateInput ? dateInput.value : "";
        resetSuggestedSlots(calAddForm);
        calAddForm.querySelectorAll(".cal-suggested-speaker-text, .cal-suggested-topic-input").forEach(function (el) {
          el.value = "";
        });
        const notesEl = document.getElementById("cal_suggested_notes");
        if (notesEl) notesEl.value = "";
        if (dateInput && dateValue) dateInput.value = dateValue;
        if (dateFilterEl && dateValue) dateFilterEl.value = dateValue;
        if (addDateEl && dateValue) addDateEl.value = dateValue;
        if (window.MemberSelectFilter) window.MemberSelectFilter.resetWithin(calAddForm);
        await refreshList();
        if (window.CalCreateForm && window.CalCreateForm.modal) {
          window.CalCreateForm.modal.hide();
        }
      });
    });
  }

  if (dateFilterEl) {
    dateFilterEl.addEventListener("change", refreshList);
  }

  if (dateFilterClearBtn) {
    dateFilterClearBtn.addEventListener("click", function () {
      if (dateFilterEl) dateFilterEl.value = "";
      refreshList();
    });
  }

  if (listEl) {
    listEl.addEventListener("click", async function (event) {
      const itemEl = event.target.closest(".cal-suggested-item");
      if (!itemEl) return;
      const id = itemEl.getAttribute("data-suggestion-id");
      if (!id) return;

      if (event.target.closest(".cal-suggested-delete-btn")) {
        if (!window.confirm("Remove this suggestion from the list?")) return;
        try {
          await fetch("/api/suggested-talks/" + encodeURIComponent(id) + "/delete", { method: "POST" });
          await refreshList();
          refreshCalendar();
        } catch (e) {
          /* ignore */
        }
        return;
      }

      if (event.target.closest(".cal-suggested-edit-btn")) {
        try {
          await openEdit(id);
        } catch (e) {
          /* ignore */
        }
        return;
      }

      if (event.target.closest(".cal-suggested-schedule-btn")) {
        try {
          const suggestion = await fetchSuggestion(id);
          if (window.CalCreateForm && window.CalCreateForm.openForSuggestion) {
            window.CalCreateForm.openForSuggestion(suggestion, suggestion.suggested_date || "");
          }
        } catch (e) {
          /* ignore */
        }
      }
    });
  }

  if (editSaveBtn && editForm) {
    editSaveBtn.addEventListener("click", async function () {
      const id = document.getElementById("suggested_edit_id").value;
      showFormError(editForm.querySelector(".cal-suggested-edit-error"), "");
      if (!id) return;
      try {
        const res = await fetch("/api/suggested-talks/" + encodeURIComponent(id) + "/edit", {
          method: "POST",
          body: new FormData(editForm),
        });
        const data = await res.json();
        if (!res.ok) {
          showFormError(editForm.querySelector(".cal-suggested-edit-error"), data.error || "Could not save.");
          return;
        }
        if (editModal) editModal.hide();
        await refreshList();
        refreshCalendar();
      } catch (e) {
        showFormError(editForm.querySelector(".cal-suggested-edit-error"), "Could not save.");
      }
    });
  }

  window.SuggestedTalks = {
    refresh: refreshList,
    setSelectedDate: setSelectedDate,
    openEdit: openEdit,
  };
})();
