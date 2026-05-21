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
    "intermediate_hymn_num": "",
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
    "intermediate_hymn_num",
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
    intermediate_num = _parse_hymn_num(form.get("intermediate_hymn_num"))
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
        "intermediate_hymn_num": intermediate_num,
        "intermediate_hymn_line": hymn_line(intermediate_num),
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
    if data.get("intermediate_hymn_line"):
        lines.append(f"Intermediate Hymn: {data['intermediate_hymn_line']}")
        lines.append("")
    if data.get("closing_hymn_line"):
        lines.append(f"Closing Hymn {data['closing_hymn_line']}")
    if data.get("benediction"):
        lines.append(f"Benediction: {data['benediction']}")
    return "\n".join(lines).strip() + "\n"


def _iter_bulletin_lines(data: dict) -> list[str]:
    return build_bulletin_text(data).split("\n")


def export_docx(data: dict) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.shared import Inches, Pt

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    body_size = 12
    body_after = 8
    section_gap = 14

    def set_para_spacing(pf, *, after: float = body_after, leading: float = 1.5) -> None:
        pf.space_before = Pt(0)
        pf.space_after = Pt(after)
        pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        pf.line_spacing = leading

    def add_blank(*, after: float = section_gap) -> None:
        p = doc.add_paragraph()
        set_para_spacing(p.paragraph_format, after=after, leading=1.0)

    def add_line(
        text: str,
        *,
        bold: bool = False,
        size: float = body_size,
        center: bool = False,
        after: float = body_after,
        leading: float = 1.5,
    ) -> None:
        p = doc.add_paragraph()
        set_para_spacing(p.paragraph_format, after=after, leading=leading)
        if center:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(text)
        run.bold = bold
        run.font.name = "Times New Roman"
        run.font.size = Pt(size)

    def add_multiline(text: str, **kwargs) -> None:
        for part in (text or "").splitlines():
            part = part.strip()
            if part:
                add_line(part, **kwargs)

    add_line("Sacrament Meeting", bold=True, size=18, center=True, after=8, leading=1.0)
    if data.get("meeting_date_display"):
        add_line(
            data["meeting_date_display"],
            bold=True,
            size=13,
            center=True,
            after=22,
            leading=1.0,
        )
    add_blank()

    if data.get("presiding"):
        add_line(f"Presiding: {data['presiding']}")
    if data.get("conducting"):
        add_line(f"Conducting: {data['conducting']}")
    if data.get("on_the_stand"):
        add_line(f"On the stand: {data['on_the_stand']}")
    add_blank()

    if data.get("welcome_text"):
        add_multiline(data["welcome_text"])
        add_blank()

    if data.get("opening_hymn_line"):
        add_line(f"Opening Hymn: {data['opening_hymn_line']}")
    if data.get("invocation"):
        add_line(f"Invocation: {data['invocation']}")
    add_blank()

    add_line("Branch Business:", bold=True, after=4)
    add_multiline(data.get("branch_business") or "")
    add_blank()

    add_line(f"Stake Business: {data.get('stake_business') or ''}")
    add_blank()

    if data.get("announcements"):
        add_multiline(data["announcements"])
        add_blank()

    if data.get("sacrament_notes"):
        add_multiline(data["sacrament_notes"])
        add_blank()

    if data.get("sacrament_hymn_line"):
        add_line(f"The Sacrament Hymn is {data['sacrament_hymn_line']}")
    add_blank()

    if data.get("speakers_text"):
        add_multiline(data["speakers_text"])
        add_blank()

    if data.get("intermediate_hymn_line"):
        add_line(f"Intermediate Hymn: {data['intermediate_hymn_line']}")
        add_blank()

    if data.get("closing_hymn_line"):
        add_line(f"Closing Hymn {data['closing_hymn_line']}")
    if data.get("benediction"):
        add_line(f"Benediction: {data['benediction']}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def speakers_text_for_talks(talks) -> str:
    names = [_talk_display_name(t) for t in talks]
    names = [n for n in names if n and n != "—"]
    if not names:
        return ""
    if len(names) == 1:
        return f"Our speaker today will be {names[0]}."
    return "Our speakers today will be " + " followed by ".join(names) + "."


def bulletin_person_name(name: str) -> str:
    """Render stored 'Last, First' names as 'First Last' on the bulletin."""
    name = " ".join((name or "").strip().split())
    if not name or "," not in name:
        return name
    last, _, first = name.partition(",")
    last = last.strip()
    first = first.strip()
    if first and last:
        return f"{first} {last}"
    return name


def _talk_display_name(t) -> str:
    if t.member_id and t.member is not None:
        return bulletin_person_name(t.member.full_name)
    return (getattr(t, "speaker_text", None) or "").strip() or "—"
