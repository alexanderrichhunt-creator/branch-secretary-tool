(function () {
  const listEl = document.getElementById("suggested-talk-list");
  const addForm = document.getElementById("suggested-talk-add-form");
  const editForm = document.getElementById("suggested-talk-edit-form");
  const editModalEl = document.getElementById("suggestedTalkEditModal");
  const editSaveBtn = document.getElementById("suggestedTalkEditSaveBtn");
  const countBadge = document.querySelector(".cal-suggested-count");

  if (!listEl) return;

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

  function renderSuggestionItem(item) {
    const topicHtml = item.topic
      ? '<div class="cal-suggested-topic small">' + escapeHtml(item.topic) + "</div>"
      : "";
    const notesHtml = item.notes
      ? '<div class="cal-suggested-notes small muted">' + escapeHtml(item.notes) + "</div>"
      : "";

    return (
      '<div class="cal-suggested-item" data-suggestion-id="' +
      item.id +
      '">' +
      '<div class="cal-suggested-item-main">' +
      '<div class="cal-suggested-speaker fw-semibold">' +
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
    updateCount(items.length);
    if (!items.length) {
      listEl.innerHTML =
        '<div class="cal-suggested-empty muted small">No suggestions yet. Add speakers or topics above.</div>';
      return;
    }
    listEl.innerHTML = items.map(renderSuggestionItem).join("");
  }

  async function refreshList() {
    try {
      const res = await fetch("/api/suggested-talks");
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
    addForm.reset();
    showFormError(addForm.querySelector(".cal-suggested-form-error"), "");
    if (window.MemberSelectFilter) window.MemberSelectFilter.resetAll();
  }

  if (addForm) {
    addForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      showFormError(addForm.querySelector(".cal-suggested-form-error"), "");
      try {
        const res = await fetch("/api/suggested-talks", {
          method: "POST",
          body: new FormData(addForm),
        });
        const data = await res.json();
        if (!res.ok) {
          showFormError(addForm.querySelector(".cal-suggested-form-error"), data.error || "Could not save.");
          return;
        }
        resetAddForm();
        await refreshList();
      } catch (e) {
        showFormError(addForm.querySelector(".cal-suggested-form-error"), "Could not save.");
      }
    });
  }

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
      } catch (e) {
        /* ignore */
      }
      return;
    }

    if (event.target.closest(".cal-suggested-edit-btn")) {
      try {
        const suggestion = await fetchSuggestion(id);
        document.getElementById("suggested_edit_id").value = suggestion.id;
        document.getElementById("suggested_edit_member_id").value = suggestion.member_id
          ? String(suggestion.member_id)
          : "";
        document.getElementById("suggested_edit_speaker_text").value = suggestion.speaker_text || "";
        document.getElementById("suggested_edit_topic").value = suggestion.topic || "";
        document.getElementById("suggested_edit_notes").value = suggestion.notes || "";
        document.getElementById("suggested_edit_member_filter").value = "";
        if (window.MemberSelectFilter) window.MemberSelectFilter.resetAll();
        showFormError(editForm.querySelector(".cal-suggested-edit-error"), "");
        if (editModal) editModal.show();
      } catch (e) {
        /* ignore */
      }
      return;
    }

    if (event.target.closest(".cal-suggested-schedule-btn")) {
      try {
        const suggestion = await fetchSuggestion(id);
        if (window.CalCreateForm && window.CalCreateForm.openForSuggestion) {
          window.CalCreateForm.openForSuggestion(suggestion, "");
        }
      } catch (e) {
        /* ignore */
      }
    }
  });

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
      } catch (e) {
        showFormError(editForm.querySelector(".cal-suggested-edit-error"), "Could not save.");
      }
    });
  }

  window.SuggestedTalks = {
    refresh: refreshList,
  };
})();
