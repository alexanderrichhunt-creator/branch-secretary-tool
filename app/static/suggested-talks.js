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
    if (window.branchCalendar && window.branchCalendar.refetchEvents) {
      window.branchCalendar.refetchEvents();
    }
  }

  async function submitSuggestedForm(form, errorSelector, onSuccess) {
    const errorEl = form.querySelector(errorSelector);
    showFormError(errorEl, "");
    try {
      const res = await fetch("/api/suggested-talks", {
        method: "POST",
        body: new FormData(form),
      });
      const data = await res.json();
      if (!res.ok) {
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
    addForm.reset();
    if (addDateEl && keepDate) addDateEl.value = keepDate;
    showFormError(addForm.querySelector(".cal-suggested-form-error"), "");
    if (window.MemberSelectFilter) window.MemberSelectFilter.resetAll();
  }

  if (addForm) {
    addForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      await submitSuggestedForm(addForm, ".cal-suggested-form-error", async function () {
        if (dateFilterEl && addDateEl && addDateEl.value) {
          dateFilterEl.value = addDateEl.value;
        }
        resetAddForm();
        await refreshList();
      });
    });
  }

  if (calAddForm) {
    calAddForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      await submitSuggestedForm(calAddForm, ".cal-suggested-modal-error", async function () {
        const dateInput = document.getElementById("cal_suggested_date");
        const dateValue = dateInput ? dateInput.value : "";
        calAddForm.reset();
        if (dateInput && dateValue) dateInput.value = dateValue;
        if (dateFilterEl && dateValue) dateFilterEl.value = dateValue;
        if (addDateEl && dateValue) addDateEl.value = dateValue;
        if (window.MemberSelectFilter) window.MemberSelectFilter.resetAll();
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
