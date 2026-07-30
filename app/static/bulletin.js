(function () {
  const form = document.getElementById("bulletin-form");
  const preview = document.getElementById("bulletin-preview");
  const meetingDate = document.getElementById("meeting_date");
  const speakersField = document.getElementById("speakers_text");
  const speakersHint = document.getElementById("speakers_mode_hint");
  const saveStatus = document.getElementById("bulletin-save-status");
  const modeInputs = document.querySelectorAll('input[name="speakers_mode"]');
  if (!form || !preview) return;

  const MODE_TALKS = "talks";
  const MODE_FAST = "fast_testimony";
  const MODE_BRANCH = "branch_conference";
  const MODE_STAKE = "stake_conference";
  const MODE_GENERAL = "general_conference";
  const SPECIAL_MODES = [MODE_FAST, MODE_BRANCH, MODE_STAKE, MODE_GENERAL];
  const DRAFT_FIELD_IDS = [
    "presiding",
    "conducting",
    "on_the_stand",
    "welcome_text",
    "opening_hymn_num",
    "opening_hymn_title",
    "invocation",
    "branch_business",
    "stake_business",
    "announcements",
    "sacrament_notes",
    "sacrament_hymn_num",
    "sacrament_hymn_title",
    "intermediate_hymn_num",
    "intermediate_hymn_title",
    "closing_hymn_num",
    "closing_hymn_title",
    "benediction",
    "speakers_text",
  ];
  const MODE_HINTS = {
    fast_testimony: {
      firstSunday: "First Sunday of the month — Fast & Testimony Meeting selected automatically.",
      selected: "Fast & Testimony Meeting selected. You can still edit the text below.",
    },
    branch_conference: {
      selected: "Branch Conference selected. You can still edit the text below.",
    },
    stake_conference: {
      selected: "Stake Conference selected. You can still edit the text below.",
    },
    general_conference: {
      selected: "General Conference selected. You can still edit the text below.",
    },
  };
  const URL_PATTERN = /https?:\/\/[^\s<>"']+/g;
  const SAVE_DELAY_MS = 800;

  let saveTimer = null;
  let isLoadingDraft = false;
  let previousMeetingDate = meetingDate ? meetingDate.value : "";

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function linkifyText(text) {
    return escapeHtml(text).replace(URL_PATTERN, function (url) {
      var clean = url.replace(/[.,);]+$/, "");
      var trailing = url.slice(clean.length);
      return (
        '<a href="' +
        clean +
        '" target="_blank" rel="noopener noreferrer">' +
        clean +
        "</a>" +
        trailing
      );
    });
  }

  function renderPreviewLines(lines) {
    return lines
      .map(function (line) {
        return linkifyText(line);
      })
      .join("\n");
  }

  function formatDisplayDate(iso) {
    if (!iso) return "";
    const parts = iso.split("-");
    if (parts.length !== 3) return iso;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
  }

  function hymnLine(numInput, titleInput) {
    const numRaw = (numInput && numInput.value || "").trim();
    const title = (titleInput && titleInput.value || "").trim();
    if (numRaw && title) {
      const prefix = numRaw.startsWith("#") ? numRaw : "#" + numRaw;
      return prefix + "  " + title;
    }
    if (title) return title;
    if (numRaw) return numRaw.startsWith("#") ? numRaw : "#" + numRaw;
    return "";
  }

  function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  function selectedSpeakersMode() {
    const checked = document.querySelector('input[name="speakers_mode"]:checked');
    return checked ? checked.value : MODE_TALKS;
  }

  function setSpeakersMode(mode) {
    modeInputs.forEach(function (input) {
      input.checked = input.value === mode;
    });
  }

  function hasIntermediateHymn() {
    return Boolean(val("intermediate_hymn_num") || val("intermediate_hymn_title"));
  }

  function isSpecialSpeakersMode(mode) {
    return SPECIAL_MODES.indexOf(mode) !== -1;
  }

  function setSaveStatus(message, tone) {
    if (!saveStatus) return;
    saveStatus.textContent = message;
    saveStatus.classList.remove("text-success", "text-danger", "text-muted");
    if (tone) {
      saveStatus.classList.add(tone);
    }
  }

  function formDataForDate(dateIso) {
    const fd = new FormData(form);
    if (dateIso) {
      fd.set("meeting_date", dateIso);
    }
    fd.set("speakers_mode", selectedSpeakersMode());
    return fd;
  }

  function scheduleSave() {
    if (isLoadingDraft) return;
    setSaveStatus("Unsaved changes…", "text-muted");
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveDraftNow, SAVE_DELAY_MS);
  }

  async function saveDraftNow(dateIso) {
    const targetDate = dateIso || (meetingDate && meetingDate.value);
    if (!targetDate || isLoadingDraft) return;
    clearTimeout(saveTimer);
    setSaveStatus("Saving…", "text-muted");
    try {
      const res = await fetch("/api/bulletin/draft", {
        method: "POST",
        body: formDataForDate(targetDate),
      });
      if (!res.ok) {
        setSaveStatus("Could not save changes.", "text-danger");
        return;
      }
      if (!dateIso || dateIso === meetingDate.value) {
        setSaveStatus("Saved for this meeting date.", "text-success");
      }
    } catch (e) {
      setSaveStatus("Could not save changes.", "text-danger");
    }
  }

  function applyDraftData(data) {
    DRAFT_FIELD_IDS.forEach(function (id) {
      const el = document.getElementById(id);
      if (!el || typeof data[id] !== "string") return;
      el.value = data[id];
    });
    if (data.speakers_mode) {
      setSpeakersMode(data.speakers_mode);
    }
    document.querySelectorAll(".hymn-num-input").forEach(function (input) {
      const numRaw = (input.value || "").trim();
      if (numRaw) {
        input.setAttribute("data-last-hymn-num", String(parseInt(numRaw.replace(/^#/, ""), 10) || ""));
      } else {
        input.removeAttribute("data-last-hymn-num");
      }
    });
    updateSpeakersHint(Boolean(data.is_first_sacrament_sunday), selectedSpeakersMode());
    if (data.saved) {
      setSaveStatus("Saved work loaded for this date.", "text-success");
    } else {
      setSaveStatus("Changes save automatically for this meeting date.", "text-muted");
    }
  }

  async function loadBulletinForDate() {
    if (!meetingDate || !meetingDate.value) return;
    isLoadingDraft = true;
    clearTimeout(saveTimer);
    setSaveStatus("Loading…", "text-muted");
    try {
      const res = await fetch("/api/bulletin/draft?date=" + encodeURIComponent(meetingDate.value));
      if (!res.ok) {
        setSaveStatus("Could not load saved work for this date.", "text-danger");
        return;
      }
      const data = await res.json();
      applyDraftData(data);
      await Promise.all(
        Array.from(document.querySelectorAll(".hymn-num-input")).map(function (input) {
          return lookupHymn(input, { skipSave: true });
        })
      );
    } catch (e) {
      setSaveStatus("Could not load saved work for this date.", "text-danger");
    } finally {
      isLoadingDraft = false;
      updatePreview();
    }
  }

  function updateSpeakersHint(isFirstSunday, mode) {
    if (!speakersHint) return;
    if (mode === MODE_FAST) {
      speakersHint.textContent = isFirstSunday ? MODE_HINTS.fast_testimony.firstSunday : MODE_HINTS.fast_testimony.selected;
      return;
    }
    if (mode === MODE_BRANCH) {
      speakersHint.textContent = MODE_HINTS.branch_conference.selected;
      return;
    }
    if (mode === MODE_STAKE) {
      speakersHint.textContent = MODE_HINTS.stake_conference.selected;
      return;
    }
    if (mode === MODE_GENERAL) {
      speakersHint.textContent = MODE_HINTS.general_conference.selected;
      return;
    }
    speakersHint.textContent = isFirstSunday
      ? "First Sunday of the month — switch to Fast & Testimony if needed."
      : "Auto-filled from calendar talks when assigned speakers is selected.";
  }

  function programLinesAfterSacrament() {
    const lines = [];
    const intermediate = hymnLine(
      document.getElementById("intermediate_hymn_num"),
      document.getElementById("intermediate_hymn_title")
    );
    const speakersText = val("speakers_text");
    const mode = selectedSpeakersMode();

    if (isSpecialSpeakersMode(mode)) {
      if (speakersText) {
        lines.push(speakersText);
        lines.push("");
      }
      return lines;
    }

    if (speakersText && intermediate) {
      const parts = speakersText.split(/\n\s*\n/).map(function (p) {
        return p.trim();
      }).filter(Boolean);
      if (parts.length >= 2) {
        lines.push(parts[0]);
        lines.push("");
        lines.push("Intermediate Hymn: " + intermediate);
        lines.push("");
        for (let i = 1; i < parts.length; i++) {
          lines.push(parts[i]);
        }
        lines.push("");
        return lines;
      }
    }

    if (speakersText) {
      lines.push(speakersText);
      lines.push("");
    }
    if (intermediate) {
      lines.push("Intermediate Hymn: " + intermediate);
      lines.push("");
    }
    return lines;
  }

  function updatePreview() {
    const lines = ["Sacrament Meeting", formatDisplayDate(val("meeting_date")), ""];

    if (val("presiding")) lines.push("Presiding: " + val("presiding"));
    if (val("conducting")) lines.push("Conducting: " + val("conducting"));
    if (val("on_the_stand")) lines.push("On the stand: " + val("on_the_stand"));
    lines.push("");
    if (val("welcome_text")) {
      lines.push(val("welcome_text"));
      lines.push("");
    }
    const opening = hymnLine(
      document.getElementById("opening_hymn_num"),
      document.getElementById("opening_hymn_title")
    );
    if (opening) lines.push("Opening Hymn: " + opening);
    if (val("invocation")) lines.push("Invocation: " + val("invocation"));
    lines.push("");
    var branchBusiness = val("branch_business");
    var branchParts = [];
    if (branchBusiness) {
      branchBusiness.split(/\r?\n/).forEach(function (part) {
        if (part.trim()) branchParts.push(part.trim());
      });
    }
    // First line sits beside the label (same pattern as Stake Business)
    if (branchParts.length) {
      lines.push("Branch Business: " + branchParts[0]);
      branchParts.slice(1).forEach(function (part) {
        lines.push(part);
      });
    } else {
      lines.push("Branch Business:");
    }
    // Blank lines for handwritten notes after printing (matches Word/text download)
    lines.push("");
    lines.push("");
    lines.push("");
    lines.push("Stake Business: " + val("stake_business"));
    lines.push("");
    if (val("announcements")) {
      lines.push(val("announcements"));
      lines.push("");
    }
    if (val("sacrament_notes")) {
      lines.push(val("sacrament_notes"));
      lines.push("");
    }
    const sacrament = hymnLine(
      document.getElementById("sacrament_hymn_num"),
      document.getElementById("sacrament_hymn_title")
    );
    if (sacrament) lines.push("The Sacrament Hymn is " + sacrament);
    lines.push("");
    lines.push.apply(lines, programLinesAfterSacrament());
    const closing = hymnLine(
      document.getElementById("closing_hymn_num"),
      document.getElementById("closing_hymn_title")
    );
    if (closing) lines.push("Closing Hymn " + closing);
    if (val("benediction")) lines.push("Benediction: " + val("benediction"));

    preview.innerHTML = renderPreviewLines(lines).trim() + "\n";
  }

  async function lookupHymn(input, options) {
    const skipSave = options && options.skipSave;
    const targetId = input.getAttribute("data-title-target");
    const target = targetId ? document.getElementById(targetId) : null;
    const numRaw = (input.value || "").trim();
    if (!target) {
      updatePreview();
      if (!skipSave) scheduleSave();
      return;
    }
    if (!numRaw) {
      target.value = "";
      input.removeAttribute("data-last-hymn-num");
      updatePreview();
      if (!skipSave) scheduleSave();
      return;
    }
    const n = parseInt(numRaw.replace(/^#/, ""), 10);
    if (!n) {
      updatePreview();
      if (!skipSave) scheduleSave();
      return;
    }
    const lastNum = input.getAttribute("data-last-hymn-num");
    if (lastNum !== String(n)) {
      try {
        const res = await fetch("/api/hymn/" + n);
        if (res.ok) {
          const data = await res.json();
          target.value = data.title || "";
          target.removeAttribute("data-title-manual");
        }
      } catch (e) {
        /* ignore */
      }
      input.setAttribute("data-last-hymn-num", String(n));
    }
    updatePreview();
    if (!skipSave) scheduleSave();
  }

  async function loadSpeakers(modeOverride) {
    if (!meetingDate || !speakersField) return;
    const d = meetingDate.value;
    if (!d) return;

    const mode = modeOverride || selectedSpeakersMode();
    try {
      const url =
        "/api/bulletin/speakers?date=" +
        encodeURIComponent(d) +
        "&mode=" +
        encodeURIComponent(mode) +
        "&has_intermediate=" +
        (hasIntermediateHymn() ? "1" : "0");
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      if (data.speakers_mode) {
        setSpeakersMode(data.speakers_mode);
      }
      if (typeof data.speakers_text === "string") {
        speakersField.value = data.speakers_text;
      }
      updateSpeakersHint(Boolean(data.is_first_sacrament_sunday), selectedSpeakersMode());
    } catch (e) {
      /* ignore */
    }
    updatePreview();
    scheduleSave();
  }

  document.querySelectorAll(".hymn-title-display").forEach(function (input) {
    input.addEventListener("input", function () {
      input.setAttribute("data-title-manual", "1");
    });
  });

  document.querySelectorAll(".hymn-num-input").forEach(function (input) {
    input.addEventListener("input", function () {
      lookupHymn(input);
    });
    input.addEventListener("change", function () {
      lookupHymn(input);
    });
  });

  form.querySelectorAll("input, textarea, select").forEach(function (el) {
    el.addEventListener("input", function () {
      updatePreview();
      scheduleSave();
    });
    el.addEventListener("change", function () {
      updatePreview();
      scheduleSave();
    });
  });

  modeInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      loadSpeakers(input.value);
    });
  });

  if (meetingDate) {
    meetingDate.addEventListener("focus", function () {
      previousMeetingDate = meetingDate.value;
    });
    meetingDate.addEventListener("change", async function () {
      const newDate = meetingDate.value;
      const oldDate = previousMeetingDate;
      clearTimeout(saveTimer);
      if (oldDate && oldDate !== newDate) {
        await saveDraftNow(oldDate);
      }
      previousMeetingDate = newDate;
      await loadBulletinForDate();
    });
  }

  ["intermediate_hymn_num", "intermediate_hymn_title"].forEach(function (id) {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener("change", function () {
      if (selectedSpeakersMode() === MODE_TALKS) {
        loadSpeakers();
      }
    });
  });

  const printBtn = document.getElementById("bulletin-print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(
        "<div style=\"font-family: Georgia, serif; font-size: 14px; white-space: pre-wrap; padding: 24px;\">" +
          preview.innerHTML +
          "</div>"
      );
      w.document.close();
      w.focus();
      w.print();
    });
  }

  window.addEventListener("beforeunload", function () {
    if (isLoadingDraft || !meetingDate || !meetingDate.value) return;
    clearTimeout(saveTimer);
    navigator.sendBeacon("/api/bulletin/draft", formDataForDate(meetingDate.value));
  });

  loadBulletinForDate();
})();
