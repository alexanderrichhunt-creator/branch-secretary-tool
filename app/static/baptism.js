(function () {
  const form = document.getElementById("baptism-form");
  const preview = document.getElementById("baptism-preview");
  if (!form || !preview) return;

  const confirmationEl = document.getElementById("confirmation_text");
  const candidateEl = document.getElementById("candidate_name");
  const templateEl = document.getElementById("baptism-confirmation-template");

  const DEFAULT_CONFIRMATION_TEMPLATE =
    "Following the baptism, [candidate] will be confirmed a member of The Church of Jesus Christ " +
    "of Latter-day Saints and receive the gift of the Holy Ghost.";

  let confirmationTemplate = DEFAULT_CONFIRMATION_TEMPLATE;

  if (templateEl) {
    try {
      confirmationTemplate = JSON.parse(templateEl.textContent || '""') || DEFAULT_CONFIRMATION_TEMPLATE;
    } catch (e) {
      confirmationTemplate = DEFAULT_CONFIRMATION_TEMPLATE;
    }
  }

  function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  function resolveConfirmationText(candidate, template) {
    template = (template || DEFAULT_CONFIRMATION_TEMPLATE).trim();
    if (!candidate) return template;
    if (template.indexOf("[candidate]") >= 0) {
      return template.replace(/\[candidate\]/g, candidate);
    }
    return template;
  }

  function syncConfirmationField() {
    if (!confirmationEl) return;
    const candidate = val("candidate_name");
    confirmationEl.value = resolveConfirmationText(candidate, confirmationTemplate);
  }

  function hymnLine(prefix) {
    const numRaw = val(prefix + "_hymn_num");
    const title = val(prefix + "_hymn_title");
    const book = val(prefix + "_hymn_book");
    const label = book === "children" ? " (Children's Songbook)" : "";
    if (numRaw && title) {
      const num = numRaw.startsWith("#") ? numRaw : "#" + numRaw;
      return num + "  " + title + label;
    }
    if (title) return title + label;
    if (numRaw) return (numRaw.startsWith("#") ? numRaw : "#" + numRaw) + label;
    return "";
  }

  function formatTime(raw) {
    if (!raw) return "";
    const parts = raw.split(":");
    if (parts.length < 2) return raw;
    const d = new Date();
    d.setHours(Number(parts[0]), Number(parts[1]), 0, 0);
    return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", hour12: true });
  }

  function formatDate(iso) {
    if (!iso) return "";
    const parts = iso.split("-");
    if (parts.length !== 3) return iso;
    const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
    return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  }

  function updatePreview() {
    const lines = ["Baptismal Service", ""];

    const dateLine = formatDate(val("service_date"));
    const timeLine = formatTime(val("service_time"));
    if (dateLine) lines.push(timeLine ? dateLine + " at " + timeLine : dateLine);
    if (val("location")) lines.push(val("location"));
    lines.push("");

    if (val("presiding")) lines.push("Presiding: " + val("presiding"));
    if (val("conducting")) lines.push("Conducting: " + val("conducting"));
    if (val("welcome_text")) {
      lines.push("");
      lines.push(val("welcome_text"));
    }

    lines.push("");
    const opening = hymnLine("opening");
    if (opening) lines.push("Opening Hymn: " + opening);
    if (val("invocation")) lines.push("Invocation: " + val("invocation"));

    lines.push("");
    if (val("speaker_1")) {
      let talk = val("speaker_1");
      if (val("speaker_1_topic")) talk += " — " + val("speaker_1_topic");
      lines.push("Talk: " + talk);
    }
    if (val("speaker_2")) {
      let talk = val("speaker_2");
      if (val("speaker_2_topic")) talk += " — " + val("speaker_2_topic");
      lines.push("Talk: " + talk);
    }
    if (val("musical_number")) lines.push("Musical number: " + val("musical_number"));

    lines.push("");
    if (val("candidate_name")) lines.push("Baptism of " + val("candidate_name"));
    if (val("baptism_by")) lines.push("Baptism performed by " + val("baptism_by"));

    lines.push("");
    const confirmation = confirmationEl ? confirmationEl.value.trim() : "";
    if (confirmation) lines.push(confirmation);
    if (val("confirmation_by")) lines.push("Confirmation by " + val("confirmation_by"));

    lines.push("");
    const closing = hymnLine("closing");
    if (closing) lines.push("Closing Hymn: " + closing);
    if (val("benediction")) lines.push("Benediction: " + val("benediction"));
    if (val("reception_notes")) {
      lines.push("");
      lines.push(val("reception_notes"));
    }

    preview.textContent = lines.join("\n").trim() + "\n";
  }

  async function lookupHymn(input) {
    const targetId = input.getAttribute("data-title-target");
    const bookTargetId = input.getAttribute("data-book-target");
    const target = targetId ? document.getElementById(targetId) : null;
    const bookEl = bookTargetId ? document.getElementById(bookTargetId) : null;
    const numRaw = (input.value || "").trim();
    if (!target) {
      updatePreview();
      return;
    }
    if (!numRaw) {
      target.value = "";
      updatePreview();
      return;
    }
    const n = parseInt(numRaw.replace(/^#/, ""), 10);
    if (!n) {
      updatePreview();
      return;
    }
    const book = bookEl ? bookEl.value : "hymns";
    try {
      const res = await fetch("/api/hymn/" + n + "?book=" + encodeURIComponent(book));
      if (!res.ok) return;
      const data = await res.json();
      target.value = data.title || "";
    } catch (e) {
      /* ignore */
    }
    updatePreview();
  }

  if (candidateEl) {
    candidateEl.addEventListener("input", function () {
      syncConfirmationField();
      updatePreview();
    });
    candidateEl.addEventListener("change", function () {
      syncConfirmationField();
      updatePreview();
    });
  }

  document.querySelectorAll(".hymn-book-select").forEach(function (select) {
    select.addEventListener("change", function () {
      const prefix = select.getAttribute("data-prefix");
      const num = document.getElementById(prefix + "_hymn_num");
      if (num) lookupHymn(num);
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
    if (el === confirmationEl) return;
    el.addEventListener("input", updatePreview);
    el.addEventListener("change", updatePreview);
  });

  if (confirmationEl) {
    confirmationEl.addEventListener("input", function () {
      confirmationTemplate = confirmationEl.value;
      updatePreview();
    });
  }

  document.querySelectorAll(".hymn-num-input").forEach(function (input) {
    lookupHymn(input);
  });
  syncConfirmationField();
  updatePreview();
})();
