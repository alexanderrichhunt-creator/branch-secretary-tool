(function () {
  const form = document.getElementById("baptism-form");
  const preview = document.getElementById("baptism-preview");
  if (!form || !preview) return;

  function val(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim() : "";
  }

  function bookLabel(book) {
    return book === "children" ? "Children's Songbook" : "";
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
    let confirmation = val("confirmation_text");
    const candidate = val("candidate_name");
    if (candidate) confirmation = confirmation.replace(/\[candidate\]/g, candidate);
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
    if (!target || !numRaw || (target.value || "").trim()) {
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
      if (!(target.value || "").trim()) target.value = data.title || "";
    } catch (e) {
      /* ignore */
    }
    updatePreview();
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
    el.addEventListener("input", updatePreview);
    el.addEventListener("change", updatePreview);
  });

  document.querySelectorAll(".hymn-num-input").forEach(lookupHymn);
  updatePreview();
})();
