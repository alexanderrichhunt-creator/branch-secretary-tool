from __future__ import annotations

import io
import re
from datetime import date, datetime

from .hymns import HYMN_BOOK_CHILDREN, HYMN_BOOK_HYMNS, hymn_book_label, hymn_display, hymn_title

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def _split_trailing_url_punctuation(url: str) -> tuple[str, str]:
    trailing = ""
    while url and url[-1] in ".,);":
        trailing = url[-1] + trailing
        url = url[:-1]
    return url, trailing


DEFAULT_BAPTISM = {
    "service_date": "",
    "service_time": "",
    "location": "",
    "presiding": "",
    "conducting": "",
    "welcome_text": "We welcome you to this baptismal service.",
    "opening_hymn_num": "2",
    "opening_hymn_title": "",
    "opening_hymn_book": HYMN_BOOK_CHILDREN,
    "invocation": "(by invitation)",
    "speaker_1": "",
    "speaker_1_topic": "",
    "speaker_2": "",
    "speaker_2_topic": "",
    "musical_number": "",
    "candidate_name": "",
    "baptism_by": "",
    "confirmation_by": "",
    "confirmation_text": (
        "Following the baptism, [candidate] will be confirmed a member of The Church of Jesus Christ "
        "of Latter-day Saints and receive the gift of the Holy Ghost."
    ),
    "closing_hymn_num": "120",
    "closing_hymn_title": "",
    "closing_hymn_book": HYMN_BOOK_CHILDREN,
    "benediction": "(by invitation)",
    "reception_notes": "",
}

SAVABLE_BAPTISM_KEYS = (
    "presiding",
    "conducting",
    "welcome_text",
    "opening_hymn_num",
    "opening_hymn_title",
    "opening_hymn_book",
    "invocation",
    "speaker_1",
    "speaker_1_topic",
    "speaker_2",
    "speaker_2_topic",
    "musical_number",
    "confirmation_text",
    "closing_hymn_num",
    "closing_hymn_title",
    "closing_hymn_book",
    "benediction",
    "reception_notes",
    "location",
)


def get_branch_baptism_defaults() -> dict:
    from .models import BaptismDefaults

    merged = dict(DEFAULT_BAPTISM)
    row = BaptismDefaults.query.get(1)
    if not row:
        return merged
    for key in SAVABLE_BAPTISM_KEYS:
        merged[key] = getattr(row, key) or ""
    return merged


def has_saved_baptism_defaults() -> bool:
    from .models import BaptismDefaults

    return BaptismDefaults.query.get(1) is not None


def save_branch_baptism_defaults(form) -> None:
    from . import db
    from .models import BaptismDefaults

    row = BaptismDefaults.query.get(1)
    if not row:
        row = BaptismDefaults(id=1)
        db.session.add(row)
    for key in SAVABLE_BAPTISM_KEYS:
        setattr(row, key, (form.get(key) or "").strip())
    row.updated_at = datetime.utcnow()
    db.session.commit()


def resolved_hymn_title(defaults: dict, num_key: str, title_key: str, book_key: str) -> str:
    saved = (defaults.get(title_key) or "").strip()
    if saved:
        return saved
    num_raw = (defaults.get(num_key) or "").strip()
    try:
        number = int(num_raw.lstrip("#"))
    except ValueError:
        return ""
    book = (defaults.get(book_key) or HYMN_BOOK_HYMNS).strip()
    return hymn_title(number, book)


def _format_service_date(d: date | str | None) -> str:
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return d
    if not d:
        return ""
    return d.strftime("%A, %B %d, %Y").replace(" 0", " ")


def _format_service_time(raw: str | None) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    try:
        t = datetime.strptime(raw, "%H:%M").time()
        return t.strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return raw


def _hymn_line_from_form(form, num_key: str, title_key: str, book_key: str) -> str:
    from .hymns import normalize_hymn_book

    num = (form.get(num_key) or "").strip()
    title = (form.get(title_key) or "").strip()
    book = normalize_hymn_book(form.get(book_key))
    label = hymn_book_label(book) if book == HYMN_BOOK_CHILDREN else None
    return hymn_display(num, title, book_label=label)


def baptism_from_form(form) -> dict:
    from .hymns import normalize_hymn_book

    service_date_raw = (form.get("service_date") or "").strip()
    service_date = None
    if service_date_raw:
        try:
            service_date = datetime.strptime(service_date_raw, "%Y-%m-%d").date()
        except ValueError:
            service_date = None

    opening_book = normalize_hymn_book(form.get("opening_hymn_book"))
    closing_book = normalize_hymn_book(form.get("closing_hymn_book"))
    opening_label = hymn_book_label(opening_book) if opening_book == HYMN_BOOK_CHILDREN else None
    closing_label = hymn_book_label(closing_book) if closing_book == HYMN_BOOK_CHILDREN else None

    candidate = (form.get("candidate_name") or "").strip()
    confirmation_text = (form.get("confirmation_text") or "").strip()
    if candidate and "[candidate]" in confirmation_text:
        confirmation_text = confirmation_text.replace("[candidate]", candidate)

    return {
        "service_date": service_date,
        "service_date_display": _format_service_date(service_date or service_date_raw),
        "service_time_display": _format_service_time(form.get("service_time")),
        "location": (form.get("location") or "").strip(),
        "presiding": (form.get("presiding") or "").strip(),
        "conducting": (form.get("conducting") or "").strip(),
        "welcome_text": (form.get("welcome_text") or "").strip(),
        "opening_hymn_line": hymn_display(
            (form.get("opening_hymn_num") or "").strip(),
            (form.get("opening_hymn_title") or "").strip(),
            book_label=opening_label,
        ),
        "invocation": (form.get("invocation") or "").strip(),
        "speaker_1": (form.get("speaker_1") or "").strip(),
        "speaker_1_topic": (form.get("speaker_1_topic") or "").strip(),
        "speaker_2": (form.get("speaker_2") or "").strip(),
        "speaker_2_topic": (form.get("speaker_2_topic") or "").strip(),
        "musical_number": (form.get("musical_number") or "").strip(),
        "candidate_name": candidate,
        "baptism_by": (form.get("baptism_by") or "").strip(),
        "confirmation_by": (form.get("confirmation_by") or "").strip(),
        "confirmation_text": confirmation_text,
        "closing_hymn_line": hymn_display(
            (form.get("closing_hymn_num") or "").strip(),
            (form.get("closing_hymn_title") or "").strip(),
            book_label=closing_label,
        ),
        "benediction": (form.get("benediction") or "").strip(),
        "reception_notes": (form.get("reception_notes") or "").strip(),
    }


def build_baptism_text(data: dict) -> str:
    lines = ["Baptismal Service", ""]

    if data.get("service_date_display"):
        line = data["service_date_display"]
        if data.get("service_time_display"):
            line += f" at {data['service_time_display']}"
        lines.append(line)
    if data.get("location"):
        lines.append(data["location"])
    lines.append("")

    for label, key in (
        ("Presiding", "presiding"),
        ("Conducting", "conducting"),
    ):
        if data.get(key):
            lines.append(f"{label}: {data[key]}")

    if data.get("welcome_text"):
        lines.append("")
        lines.append(data["welcome_text"])

    lines.append("")
    if data.get("opening_hymn_line"):
        lines.append(f"Opening Hymn: {data['opening_hymn_line']}")
    if data.get("invocation"):
        lines.append(f"Invocation: {data['invocation']}")

    lines.append("")
    if data.get("speaker_1"):
        talk = data["speaker_1"]
        if data.get("speaker_1_topic"):
            talk += f" — {data['speaker_1_topic']}"
        lines.append(f"Talk: {talk}")
    if data.get("speaker_2"):
        talk = data["speaker_2"]
        if data.get("speaker_2_topic"):
            talk += f" — {data['speaker_2_topic']}"
        lines.append(f"Talk: {talk}")
    if data.get("musical_number"):
        lines.append(f"Musical number: {data['musical_number']}")

    lines.append("")
    if data.get("candidate_name"):
        lines.append(f"Baptism of {data['candidate_name']}")
    if data.get("baptism_by"):
        lines.append(f"Baptism performed by {data['baptism_by']}")

    lines.append("")
    if data.get("confirmation_text"):
        lines.append(data["confirmation_text"])
    if data.get("confirmation_by"):
        lines.append(f"Confirmation by {data['confirmation_by']}")

    lines.append("")
    if data.get("closing_hymn_line"):
        lines.append(f"Closing Hymn: {data['closing_hymn_line']}")
    if data.get("benediction"):
        lines.append(f"Benediction: {data['benediction']}")

    if data.get("reception_notes"):
        lines.append("")
        lines.append(data["reception_notes"])

    return "\n".join(lines).strip() + "\n"


def export_docx(data: dict) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.shared import Inches, Pt

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    body_size = 11
    body_after = 4
    section_after = 8
    leading = 1.22

    def set_para_spacing(pf, *, after: float = body_after, leading_val: float = leading) -> None:
        pf.space_before = Pt(0)
        pf.space_after = Pt(after)
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = leading_val

    def add_line(text: str, *, bold: bool = False, center: bool = False, after: float = body_after) -> None:
        p = doc.add_paragraph()
        set_para_spacing(p.paragraph_format, after=after, leading_val=leading)
        if center:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = bold
        run.font.name = "Times New Roman"
        run.font.size = Pt(body_size)

    def add_labeled_line(label: str, value: str, *, separator: str = ": ", after: float = body_after) -> None:
        if not value:
            return
        p = doc.add_paragraph()
        set_para_spacing(p.paragraph_format, after=after, leading_val=leading)
        label_run = p.add_run(label + separator)
        label_run.bold = True
        label_run.font.name = "Times New Roman"
        label_run.font.size = Pt(body_size)
        value_run = p.add_run(value)
        value_run.font.name = "Times New Roman"
        value_run.font.size = Pt(body_size)

    def add_multiline(text: str, *, after_last: float = section_after) -> None:
        parts = [part.strip() for part in (text or "").splitlines() if part.strip()]
        for i, part in enumerate(parts):
            add_line(part, after=after_last if i == len(parts) - 1 else body_after)

    add_line("Baptismal Service", bold=True, center=True, after=3)

    subtitle_parts = []
    if data.get("service_date_display"):
        subtitle = data["service_date_display"]
        if data.get("service_time_display"):
            subtitle += f" at {data['service_time_display']}"
        subtitle_parts.append(subtitle)
    if data.get("location"):
        subtitle_parts.append(data["location"])
    if subtitle_parts:
        add_line("\n".join(subtitle_parts), bold=True, center=True, after=12)

    add_labeled_line("Presiding", data.get("presiding") or "", after=body_after)
    add_labeled_line("Conducting", data.get("conducting") or "", after=section_after)

    if data.get("welcome_text"):
        add_multiline(data["welcome_text"], after_last=section_after)

    add_labeled_line("Opening Hymn", data.get("opening_hymn_line") or "", after=body_after)
    add_labeled_line("Invocation", data.get("invocation") or "", after=section_after)

    if data.get("speaker_1"):
        talk = data["speaker_1"]
        if data.get("speaker_1_topic"):
            talk += f" — {data['speaker_1_topic']}"
        add_labeled_line("Talk", talk, after=body_after)
    if data.get("speaker_2"):
        talk = data["speaker_2"]
        if data.get("speaker_2_topic"):
            talk += f" — {data['speaker_2_topic']}"
        add_labeled_line("Talk", talk, after=body_after)
    if data.get("musical_number"):
        add_labeled_line("Musical number", data["musical_number"], after=section_after)

    if data.get("candidate_name"):
        add_line(f"Baptism of {data['candidate_name']}", bold=True, after=body_after)
    if data.get("baptism_by"):
        add_labeled_line("Baptism performed by", data["baptism_by"], separator=" ", after=section_after)

    if data.get("confirmation_text"):
        add_multiline(data["confirmation_text"], after_last=body_after)
    if data.get("confirmation_by"):
        add_labeled_line("Confirmation by", data["confirmation_by"], separator=" ", after=section_after)

    add_labeled_line("Closing Hymn", data.get("closing_hymn_line") or "", after=body_after)
    add_labeled_line("Benediction", data.get("benediction") or "", after=section_after)

    if data.get("reception_notes"):
        add_multiline(data["reception_notes"], after_last=body_after)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
