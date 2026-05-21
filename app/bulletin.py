from __future__ import annotations

import io
from datetime import date, datetime, timedelta

from .hymns import hymn_line, hymn_title

DEFAULT_BULLETIN = {
    "presiding": "Michael Reynolds, Madisonville Branch President",
    "conducting": "Pat Gaume, 1st Counselor",
    "on_the_stand": "Will Ross, 2nd Counselor, Madisonville Branch Presidency",
    "welcome_text": (
        "Welcome… any visitors who might be in attendance. "
        "Acknowledgment of any Stake visitors."
    ),
    "opening_hymn_num": "6",
    "invocation": "(by invitation)",
    "branch_business": (
        "Seminary Graduation on Sunday, May 17th, 5:00 p.m. at the Creighton Building in Conroe."
    ),
    "stake_business": "(if any)",
    "announcements": (
        "Here is the Zoom Link for the Madisonville Branch. It should activate a few minutes "
        "prior to 10:00 a.m. on Sundays. Copy and paste the Link into your Zoom App.\n"
        "https://zoom.us/j/92713005551\n"
        "Check for other news items at the Madisonville Branch Page on Facebook."
    ),
    "sacrament_notes": (
        "After the singing of the Sacrament Hymn, the Zoom broadcast portion of this meeting "
        "will be turned off; however, it will be turned back on after the Sacrament has been "
        "passed. If you have been authorized to bless the Sacrament during your meeting at home, "
        "please take this as your opportunity to do so."
    ),
    "sacrament_hymn_num": "190",
    "closing_hymn_num": "141",
    "benediction": "(by invitation)",
}

# Fields stored as branch defaults (not meeting_date or speakers_text).
SAVABLE_BULLETIN_KEYS = (
    "presiding",
    "conducting",
    "on_the_stand",
    "welcome_text",
    "opening_hymn_num",
    "invocation",
    "stake_business",
    "announcements",
    "sacrament_notes",
    "sacrament_hymn_num",
    "closing_hymn_num",
    "benediction",
)


def get_branch_bulletin_defaults() -> dict:
    """Built-in template merged with saved branch defaults from the database."""
    from .models import BulletinDefaults

    merged = dict(DEFAULT_BULLETIN)
    row = BulletinDefaults.query.get(1)
    if not row:
        return merged
    for key in SAVABLE_BULLETIN_KEYS:
        merged[key] = getattr(row, key) or ""
    return merged


def has_saved_branch_defaults() -> bool:
    from .models import BulletinDefaults

    return BulletinDefaults.query.get(1) is not None


def save_branch_bulletin_defaults(form) -> None:
    from . import db
    from .models import BulletinDefaults

    row = BulletinDefaults.query.get(1)
    if not row:
        row = BulletinDefaults(id=1)
        db.session.add(row)
    for key in SAVABLE_BULLETIN_KEYS:
        setattr(row, key, (form.get(key) or "").strip())
    row.updated_at = datetime.utcnow()
    db.session.commit()


def default_sacrament_sunday(today: date | None = None) -> date:
    today = today or date.today()
    days_until = (6 - today.weekday()) % 7
    if days_until == 0:
        return today
    return today + timedelta(days=days_until)


def _parse_hymn_num(raw: str | None) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def _format_meeting_date(d: date | str | None) -> str:
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return d
    if not d:
        return ""
    return d.strftime("%B %d, %Y").replace(" 0", " ")


def bulletin_from_form(form) -> dict:
    meeting_date_raw = (form.get("meeting_date") or "").strip()
    meeting_date = None
    if meeting_date_raw:
        try:
            meeting_date = datetime.strptime(meeting_date_raw, "%Y-%m-%d").date()
        except ValueError:
            meeting_date = None

    opening_num = _parse_hymn_num(form.get("opening_hymn_num"))
    sacrament_num = _parse_hymn_num(form.get("sacrament_hymn_num"))
    closing_num = _parse_hymn_num(form.get("closing_hymn_num"))

    return {
        "meeting_date": meeting_date,
        "meeting_date_display": _format_meeting_date(meeting_date or meeting_date_raw),
        "presiding": (form.get("presiding") or "").strip(),
        "conducting": (form.get("conducting") or "").strip(),
        "on_the_stand": (form.get("on_the_stand") or "").strip(),
        "welcome_text": (form.get("welcome_text") or "").strip(),
        "opening_hymn_num": opening_num,
        "opening_hymn_line": hymn_line(opening_num),
        "invocation": (form.get("invocation") or "").strip(),
        "branch_business": (form.get("branch_business") or "").strip(),
        "stake_business": (form.get("stake_business") or "").strip(),
        "announcements": (form.get("announcements") or "").strip(),
        "sacrament_notes": (form.get("sacrament_notes") or "").strip(),
        "sacrament_hymn_num": sacrament_num,
        "sacrament_hymn_line": hymn_line(sacrament_num),
        "speakers_text": (form.get("speakers_text") or "").strip(),
        "closing_hymn_num": closing_num,
        "closing_hymn_line": hymn_line(closing_num),
        "benediction": (form.get("benediction") or "").strip(),
    }


def build_bulletin_text(data: dict) -> str:
    lines = [
        "Sacrament Meeting",
        data.get("meeting_date_display") or "",
        "",
    ]
    if data.get("presiding"):
        lines.append(f"Presiding: {data['presiding']}")
    if data.get("conducting"):
        lines.append(f"Conducting: {data['conducting']}")
    if data.get("on_the_stand"):
        lines.append(f"On the stand: {data['on_the_stand']}")
    lines.append("")
    if data.get("welcome_text"):
        lines.append(data["welcome_text"])
        lines.append("")
    if data.get("opening_hymn_line"):
        lines.append(f"Opening Hymn: {data['opening_hymn_line']}")
    if data.get("invocation"):
        lines.append(f"Invocation: {data['invocation']}")
    lines.append("")
    lines.append("Branch Business:")
    lines.append(data.get("branch_business") or "")
    lines.append("")
    lines.append(f"Stake Business: {data.get('stake_business') or ''}")
    lines.append("")
    if data.get("announcements"):
        lines.append(data["announcements"])
        lines.append("")
    if data.get("sacrament_notes"):
        lines.append(data["sacrament_notes"])
        lines.append("")
    if data.get("sacrament_hymn_line"):
        lines.append(f"The Sacrament Hymn is {data['sacrament_hymn_line']}")
    lines.append("")
    if data.get("speakers_text"):
        lines.append(data["speakers_text"])
        lines.append("")
    if data.get("closing_hymn_line"):
        lines.append(f"Closing Hymn {data['closing_hymn_line']}")
    if data.get("benediction"):
        lines.append(f"Benediction: {data['benediction']}")
    return "\n".join(lines).strip() + "\n"


def export_docx(data: dict) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)

    doc.add_heading("Sacrament Meeting", level=1)
    if data.get("meeting_date_display"):
        p = doc.add_paragraph(data["meeting_date_display"])
        p.runs[0].bold = True

    def add_line(label: str, value: str):
        if not value:
            return
        doc.add_paragraph(f"{label}: {value}")

    add_line("Presiding", data.get("presiding", ""))
    add_line("Conducting", data.get("conducting", ""))
    add_line("On the stand", data.get("on_the_stand", ""))
    doc.add_paragraph("")
    if data.get("welcome_text"):
        doc.add_paragraph(data["welcome_text"])
        doc.add_paragraph("")
    if data.get("opening_hymn_line"):
        doc.add_paragraph(f"Opening Hymn: {data['opening_hymn_line']}")
    add_line("Invocation", data.get("invocation", ""))
    doc.add_paragraph("")
    doc.add_paragraph("Branch Business:")
    doc.add_paragraph(data.get("branch_business") or "")
    doc.add_paragraph("")
    doc.add_paragraph(f"Stake Business: {data.get('stake_business') or ''}")
    doc.add_paragraph("")
    if data.get("announcements"):
        for block in data["announcements"].split("\n"):
            doc.add_paragraph(block)
        doc.add_paragraph("")
    if data.get("sacrament_notes"):
        doc.add_paragraph(data["sacrament_notes"])
        doc.add_paragraph("")
    if data.get("sacrament_hymn_line"):
        doc.add_paragraph(f"The Sacrament Hymn is {data['sacrament_hymn_line']}")
    doc.add_paragraph("")
    if data.get("speakers_text"):
        doc.add_paragraph(data["speakers_text"])
        doc.add_paragraph("")
    if data.get("closing_hymn_line"):
        doc.add_paragraph(f"Closing Hymn {data['closing_hymn_line']}")
    add_line("Benediction", data.get("benediction", ""))

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def export_pdf(data: dict) -> bytes:
    from fpdf import FPDF

    def safe(s: str) -> str:
        return (
            (s or "")
            .replace("…", "...")
            .replace("\u201c", '"')
            .replace("\u201d", '"')
            .replace("\u2019", "'")
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    width = pdf.epw
    for line in build_bulletin_text(data).split("\n"):
        pdf.set_x(pdf.l_margin)
        if not line.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(width, 5.5, safe(line))
    out = pdf.output()
    return out if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")


def speakers_text_for_talks(talks) -> str:
    names = [_talk_display_name(t) for t in talks]
    names = [n for n in names if n and n != "—"]
    if not names:
        return ""
    if len(names) == 1:
        return f"Our speaker today will be {names[0]}."
    return "Our speakers today will be " + " followed by ".join(names) + "."


def _talk_display_name(t) -> str:
    if t.member_id and t.member is not None:
        return t.member.full_name
    return (getattr(t, "speaker_text", None) or "").strip() or "—"
