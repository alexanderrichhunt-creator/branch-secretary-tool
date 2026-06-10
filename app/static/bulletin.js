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
  const URL_PATTERN = /https?:\/\/[^\s<>"']+/g;

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

  function programLinesAfterSacrament() {
    const lines = [];
    const intermediate = hymnLine(
      document.getElementById("intermediate_hymn_num"),
      document.getElementById("intermediate_hymn_title")
    );
    const speakersText = val("speakers_text");
    const mode = selectedSpeakersMode();

    if (mode === MODE_FAST) {
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
    lines.push.apply(lines, programLinesAfterSacrament());
    const closing = hymnLine(
      document.getElementById("closing_hymn_num"),
      document.getElementById("closing_hymn_title")
    );
    if (closing) lines.push("Closing Hymn " + closing);
    if (val("benediction")) lines.push("Benediction: " + val("benediction"));

    preview.innerHTML = renderPreviewLines(lines).trim() + "\n";
  }

  async function lookupHymn(input) {
    const targetId = input.getAttribute("data-title-target");
    const target = targetId ? document.getElementById(targetId) : null;
    const numRaw = (input.value || "").trim();
    if (!target) {
      updatePreview();
      return;
    }
    if (!numRaw) {
      target.value = "";
      input.removeAttribute("data-last-hymn-num");
      updatePreview();
      return;
    }
    const n = parseInt(numRaw.replace(/^#/, ""), 10);
    if (!n) {
      updatePreview();
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

  document.querySelectorAll(".hymn-num-input").forEach(function (input) {
    const numRaw = (input.value || "").trim();
    if (numRaw) {
      input.setAttribute("data-last-hymn-num", String(parseInt(numRaw.replace(/^#/, ""), 10) || ""));
    }
    lookupHymn(input);
  });
  loadSpeakers();
  updatePreview();
})();
