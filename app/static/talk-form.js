(function () {
  function isFirstSacramentSunday(iso) {
    if (!iso) return false;
    const parts = iso.split("-");
    if (parts.length !== 3) return false;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.getDay() === 0 && d.getDate() <= 7;
  }

  function selectedTalkKind(form) {
    const checked = form.querySelector('input[name="talk_kind"]:checked');
    return checked ? checked.value : "assigned";
  }

  function setTalkKind(form, kind) {
    const input = form.querySelector('input[name="talk_kind"][value="' + kind + '"]');
    if (input) input.checked = true;
    syncTalkKind(form);
  }

  function syncTalkKind(form) {
    const isFast = selectedTalkKind(form) === "fast_testimony";
    form.querySelectorAll(".talk-assigned-fields").forEach(function (el) {
      el.classList.toggle("d-none", isFast);
    });

    const hint = form.querySelector(".talk-kind-hint");
    const dateInput = form.querySelector('[name="talk_date"]');
    const dateValue = dateInput ? dateInput.value : "";
    if (hint) {
      if (isFast) {
        hint.textContent = isFirstSacramentSunday(dateValue)
          ? "First Sunday of the month — Fast & Testimony selected automatically."
          : "No assigned speakers for this week. Appears on the calendar and bulletin.";
      } else if (isFirstSacramentSunday(dateValue)) {
        hint.textContent = "First Sunday of the month — switch to Fast & Testimony if needed.";
      } else {
        hint.textContent = "Pick a member or type a visitor name.";
      }
    }
  }

  function maybeAutoSelectFastTestimony(form) {
    const dateInput = form.querySelector('[name="talk_date"]');
    if (!dateInput || !dateInput.value) return;
    if (isFirstSacramentSunday(dateInput.value)) {
      setTalkKind(form, "fast_testimony");
      return;
    }
    if (selectedTalkKind(form) === "fast_testimony") {
      setTalkKind(form, "assigned");
    }
  }

  function bindForm(form) {
    form.querySelectorAll(".talk-kind-input").forEach(function (input) {
      input.addEventListener("change", function () {
        syncTalkKind(form);
      });
    });

    const dateInput = form.querySelector('[name="talk_date"]');
    if (dateInput) {
      dateInput.addEventListener("change", function () {
        maybeAutoSelectFastTestimony(form);
        syncTalkKind(form);
      });
    }

    syncTalkKind(form);
  }

  document.querySelectorAll(".talk-add-form").forEach(bindForm);
})();
