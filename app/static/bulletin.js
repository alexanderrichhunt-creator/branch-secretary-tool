(function () {
  const form = document.getElementById("bulletin-form");
  const preview = document.getElementById("bulletin-preview");
  const meetingDate = document.getElementById("meeting_date");
  const speakersField = document.getElementById("speakers_text");
  const speakersHint = document.getElementById("speakers_mode_hint");
  const modeInputs = document.querySelectorAll('input[name="speakers_mode"]');
  if (!form || !preview) return;

  const MODE_TALKS = "talks";
  const MODE_FAST = "fast_testimony";

  function formatDisplayDate(iso) {
    if (!iso) return "";
    const parts = iso.split("-");
    if (parts.length !== 3) return iso;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
  }

  function hymnLine(numInput, titleInput) {
    const n = parseInt(numInput.value, 10);
    const title = (titleInput && titleInput.value) || "";
    if (!n) return "";
    return title ? "#" + n + "  " + title : "#" + n;
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

  function updateSpeakersHint(isFirstSunday, mode) {
    if (!speakersHint) return;
    if (mode === MODE_FAST) {
      speakersHint.textContent = isFirstSunday
        ? "First Sunday of the month — Fast & Testimony Meeting selected automatically."
        : "Fast & Testimony Meeting selected. You can still edit the text below.";
      return;
    }
    speakersHint.textContent = isFirstSunday
      ? "First Sunday of the month — switch to Fast & Testimony if needed."
      : "Auto-filled from calendar talks when assigned speakers is selected.";
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
    lines.push("Branch Business:");
    lines.push(val("branch_business"));
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
    if (val("speakers_text")) {
      lines.push(val("speakers_text"));
      lines.push("");
    }
    const intermediate = hymnLine(
      document.getElementById("intermediate_hymn_num"),
      document.getElementById("intermediate_hymn_title")
    );
    if (intermediate) {
      lines.push("Intermediate Hymn: " + intermediate);
      lines.push("");
    }
    const closing = hymnLine(
      document.getElementById("closing_hymn_num"),
      document.getElementById("closing_hymn_title")
    );
    if (closing) lines.push("Closing Hymn " + closing);
    if (val("benediction")) lines.push("Benediction: " + val("benediction"));

    preview.textContent = lines.join("\n").trim() + "\n";
  }

  async function lookupHymn(input) {
    const targetId = input.getAttribute("data-title-target");
    const target = targetId ? document.getElementById(targetId) : null;
    const n = parseInt(input.value, 10);
    if (!target || !n) {
      if (target) target.value = "";
      updatePreview();
      return;
    }
    try {
      const res = await fetch("/api/hymn/" + n);
      if (!res.ok) return;
      const data = await res.json();
      target.value = data.title || "";
    } catch (e) {
      /* ignore */
    }
    updatePreview();
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
        encodeURIComponent(mode);
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
  }

  document.querySelectorAll(".hymn-num-input").forEach(function (input) {
    input.addEventListener("input", function () {
      lookupHymn(input);
    });
    input.addEventListener("change", function () {
      lookupHymn(input);
    });
  });

  form.querySelectorAll("input, textarea, select").forEach(function (el) {
    el.addEventListener("input", updatePreview);
    el.addEventListener("change", updatePreview);
  });

  modeInputs.forEach(function (input) {
    input.addEventListener("change", function () {
      loadSpeakers(input.value);
    });
  });

  if (meetingDate) {
    meetingDate.addEventListener("change", function () {
      loadSpeakers();
    });
  }

  const printBtn = document.getElementById("bulletin-print-btn");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      const w = window.open("", "_blank");
      if (!w) return;
      w.document.write(
        "<pre style=\"font-family: Georgia, serif; font-size: 14px; white-space: pre-wrap; padding: 24px;\">" +
          preview.textContent.replace(/&/g, "&amp;").replace(/</g, "&lt;") +
          "</pre>"
      );
      w.document.close();
      w.focus();
      w.print();
    });
  }

  document.querySelectorAll(".hymn-num-input").forEach(lookupHymn);
  loadSpeakers();
  updatePreview();
})();
