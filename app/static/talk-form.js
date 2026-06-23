(function () {
  const SPECIAL_KINDS = {
    fast_testimony: {
      autoHint: "First Sunday of the month — Fast & Testimony selected automatically.",
      selectedHint: "No assigned speakers for this week. Appears on the calendar and bulletin.",
    },
    branch_conference: {
      selectedHint: "Branch Conference for this sacrament Sunday. No assigned speakers.",
    },
    stake_conference: {
      selectedHint: "Stake Conference for this sacrament Sunday. No assigned speakers.",
    },
    general_conference: {
      selectedHint: "General Conference for this sacrament Sunday. No assigned speakers.",
    },
  };

  function isFirstSacramentSunday(iso) {
    if (!iso) return false;
    const parts = iso.split("-");
    if (parts.length !== 3) return false;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.getDay() === 0 && d.getDate() <= 7;
  }

  function selectedTalkKind(form) {
    const checked = form.querySelector('input[name="talk_kind"]:checked');
    if (checked) return checked.value;
    const select = form.querySelector('select[name="talk_kind"]');
    return select ? select.value : "assigned";
  }

  function setTalkKind(form, kind) {
    const input = form.querySelector('input[name="talk_kind"][value="' + kind + '"]');
    if (input) input.checked = true;
    const select = form.querySelector('select[name="talk_kind"]');
    if (select) select.value = kind;
    syncTalkKind(form);
  }

  function isSpecialTalkKind(kind) {
    return kind !== "assigned";
  }

  function syncTalkKind(form) {
    const kind = selectedTalkKind(form);
    const isSpecial = isSpecialTalkKind(kind);
    form.querySelectorAll(".talk-assigned-fields").forEach(function (el) {
      el.classList.toggle("d-none", isSpecial);
    });

    const hint = form.querySelector(".talk-kind-hint");
    const dateInput = form.querySelector('[name="talk_date"]');
    const dateValue = dateInput ? dateInput.value : "";
    if (hint) {
      if (isSpecial) {
        const meta = SPECIAL_KINDS[kind] || {};
        if (kind === "fast_testimony" && isFirstSacramentSunday(dateValue)) {
          hint.textContent = meta.autoHint || meta.selectedHint || "";
        } else {
          hint.textContent = meta.selectedHint || "No assigned speakers for this week.";
        }
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
    form.querySelectorAll(".talk-kind-select").forEach(function (input) {
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
