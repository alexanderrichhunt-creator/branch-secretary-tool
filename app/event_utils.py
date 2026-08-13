"""Expand branch calendar events (including recurrence) for FullCalendar."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from dateutil.rrule import DAILY, FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rrule

WEEKDAY_CODES = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
WEEKDAY_MAP = {
    "MO": MO,
    "TU": TU,
    "WE": WE,
    "TH": TH,
    "FR": FR,
    "SA": SA,
    "SU": SU,
}
WEEKDAY_NAMES = {
    "MO": "Monday",
    "TU": "Tuesday",
    "WE": "Wednesday",
    "TH": "Thursday",
    "FR": "Friday",
    "SA": "Saturday",
    "SU": "Sunday",
}
NTH_WEEKDAY_CHOICES = (
    (1, "1st"),
    (2, "2nd"),
    (3, "3rd"),
    (4, "4th"),
    (-1, "last"),
)
WEEKLY_PRESETS = {
    "biweekly": 2,
    "every_3_weeks": 3,
    "every_4_weeks": 4,
}
NTH_LABELS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", -1: "last"}

EVENT_CATEGORIES = {
    "leadership": {
        "label": "Leadership Meetings",
        "color": "#4338ca",
        "border": "#3730a3",
    },
    "branch": {
        "label": "Branch Events",
        "color": "#9333ea",
        "border": "#7e22ce",
    },
    "stake": {
        "label": "Stake Events",
        "color": "#d97706",
        "border": "#b45309",
    },
    "youth": {
        "label": "Youth Events",
        "color": "#0891b2",
        "border": "#0e7490",
    },
}

DEFAULT_EVENT_STYLE = {
    "label": "General event",
    "color": "#64748b",
    "border": "#475569",
}

CALENDAR_ITEM_STYLES = {
    "talk": {
        "label": "Talks",
        "color": "#2563eb",
        "border": "#1d4ed8",
    },
    "fast_testimony": {
        "label": "Fast & Testimony",
        "color": "#be185d",
        "border": "#9f1239",
    },
    "branch_conference": {
        "label": "Branch Conference",
        "color": "#0d9488",
        "border": "#0f766e",
    },
    "stake_conference": {
        "label": "Stake Conference",
        "color": "#c2410c",
        "border": "#9a3412",
    },
    "general_conference": {
        "label": "General Conference",
        "color": "#4338ca",
        "border": "#3730a3",
    },
    "interview": {
        "label": "Interviews",
        "color": "#16a34a",
        "border": "#15803d",
    },
    "suggested_talk": {
        "label": "Suggested talks",
        "color": "#7c3aed",
        "border": "#6d28d9",
    },
    "general": {
        "label": "General events",
        "color": DEFAULT_EVENT_STYLE["color"],
        "border": DEFAULT_EVENT_STYLE["border"],
    },
}


def normalize_event_category(raw: str | None) -> str | None:
    slug = (raw or "").strip().lower()
    return slug if slug in EVENT_CATEGORIES else None


def event_category_meta(slug: str | None) -> dict:
    if slug and slug in EVENT_CATEGORIES:
        return EVENT_CATEGORIES[slug]
    return DEFAULT_EVENT_STYLE


def event_category_label(slug: str | None) -> str:
    return event_category_meta(slug)["label"]


def event_category_colors(slug: str | None) -> tuple[str, str]:
    meta = event_category_meta(slug)
    return meta["color"], meta["border"]


def calendar_item_style(kind: str) -> dict:
    return CALENDAR_ITEM_STYLES.get(kind, CALENDAR_ITEM_STYLES["general"])


def calendar_item_colors(kind: str) -> tuple[str, str]:
    meta = calendar_item_style(kind)
    return meta["color"], meta["border"]


def parse_calendar_range(start_raw: str | None, end_raw: str | None) -> tuple[datetime, datetime]:
    """Parse FullCalendar fetch range; fall back to a sensible window."""
    default_start = datetime.combine(date.today() - timedelta(days=90), time.min)
    default_end = datetime.combine(date.today() + timedelta(days=365), time.max)
    start = _parse_iso_datetime(start_raw) or default_start
    end = _parse_iso_datetime(end_raw) or default_end
    if end < start:
        start, end = end, start
    return start, end


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1]
        if "T" in raw:
            return datetime.fromisoformat(raw[:19])
        return datetime.combine(date.fromisoformat(raw[:10]), time.min)
    except Exception:
        return None


def event_duration(event) -> timedelta:
    if getattr(event, "all_day", False):
        return timedelta(days=1)
    end_at = getattr(event, "end_at", None)
    if end_at and end_at > event.starts_at:
        return end_at - event.starts_at
    minutes = getattr(event, "duration_minutes", None) or 60
    return timedelta(minutes=minutes)


@dataclass(frozen=True)
class RecurrenceSpec:
    freq: str | None
    interval: int = 1
    byweekday: str | None = None
    until: date | None = None
    bysetpos: int | None = None


def weekday_nth_from_date(d: date) -> tuple[int, str]:
    """Return (1-4 or -1 for last, weekday code) for a calendar date."""
    n = (d.day - 1) // 7 + 1
    code = WEEKDAY_CODES[d.weekday()]
    if n >= 5:
        return -1, code
    return n, code


def _weekday_codes(raw: str | None) -> list[str]:
    return [code for code in (raw or "").split(",") if code in WEEKDAY_MAP]


def _normalize_recurrence_freq(freq_name: str | None, interval: int) -> tuple[str | None, int]:
    freq = (freq_name or "").strip().lower()
    if not freq or freq == "none":
        return None, max(1, interval)
    if freq == "monthly_nth":
        return "monthly", 1
    if freq in WEEKLY_PRESETS:
        return "weekly", WEEKLY_PRESETS[freq]
    return freq, max(1, interval)


def recurrence_option(obj) -> str:
    """Form <option> value that matches a stored recurrence."""
    freq = (getattr(obj, "recurrence_freq", None) or "").strip().lower()
    interval = max(1, int(getattr(obj, "recurrence_interval", None) or 1))
    bysetpos = getattr(obj, "recurrence_bysetpos", None)
    if not freq:
        return "none"
    if freq == "daily":
        return "daily"
    if freq == "weekly":
        inverse = {weeks: key for key, weeks in WEEKLY_PRESETS.items()}
        return inverse.get(interval, "weekly")
    if freq == "monthly":
        return "monthly_nth" if bysetpos else "monthly"
    return freq


def build_recurrence_rule(event):
    interval = max(1, int(getattr(event, "recurrence_interval", None) or 1))
    freq_name, interval = _normalize_recurrence_freq(
        getattr(event, "recurrence_freq", None), interval
    )
    if not freq_name:
        return None

    freq = {"daily": DAILY, "weekly": WEEKLY, "monthly": MONTHLY}.get(freq_name)
    if freq is None:
        return None

    kwargs: dict = {"freq": freq, "interval": interval, "dtstart": event.starts_at}

    until = getattr(event, "recurrence_until", None)
    if until:
        kwargs["until"] = datetime.combine(until, time(23, 59, 59))

    weekday_codes = _weekday_codes(getattr(event, "recurrence_byweekday", None))
    bysetpos = getattr(event, "recurrence_bysetpos", None)
    try:
        bysetpos = int(bysetpos) if bysetpos is not None else None
    except (TypeError, ValueError):
        bysetpos = None
    if bysetpos not in (1, 2, 3, 4, 5, -1):
        bysetpos = None

    if freq_name == "monthly" and bysetpos and weekday_codes:
        kwargs["byweekday"] = [WEEKDAY_MAP[code](bysetpos) for code in weekday_codes]
    elif freq_name == "weekly" and weekday_codes:
        kwargs["byweekday"] = [WEEKDAY_MAP[code] for code in weekday_codes]

    return rrule(**kwargs)


def iter_event_occurrences(event, range_start: datetime, range_end: datetime):
    """Yield (starts_at, ends_at) tuples for an event within the given range."""
    duration = event_duration(event)
    rule = build_recurrence_rule(event)
    all_day = bool(getattr(event, "all_day", False))

    if rule is None:
        occ_start = event.starts_at
        occ_end = occ_start + duration if not all_day else occ_start + timedelta(days=1)
        if _occurrence_overlaps(occ_start, occ_end, all_day, range_start, range_end):
            yield occ_start, occ_end
        return

    for occ_start in rule.between(range_start, range_end, inc=True):
        if all_day:
            occ_start = datetime.combine(occ_start.date(), time.min)
            occ_end = occ_start + timedelta(days=1)
        else:
            base_time = event.starts_at.time()
            occ_start = datetime.combine(occ_start.date(), base_time)
            occ_end = occ_start + duration
        if _occurrence_overlaps(occ_start, occ_end, all_day, range_start, range_end):
            yield occ_start, occ_end


def _occurrence_overlaps(
    occ_start: datetime,
    occ_end: datetime,
    all_day: bool,
    range_start: datetime,
    range_end: datetime,
) -> bool:
    if all_day:
        occ_end = occ_start + timedelta(days=1)
    return occ_start < range_end and occ_end > range_start


def _day_names(raw: str | None) -> str:
    names = [WEEKDAY_NAMES.get(code, code) for code in _weekday_codes(raw)]
    return ", ".join(names)


def recurrence_label(event) -> str:
    interval = max(1, int(getattr(event, "recurrence_interval", None) or 1))
    freq, interval = _normalize_recurrence_freq(getattr(event, "recurrence_freq", None), interval)
    if not freq:
        return ""
    day_names = _day_names(getattr(event, "recurrence_byweekday", None))
    if freq == "daily":
        label = "Daily" if interval == 1 else f"Every {interval} days"
    elif freq == "weekly":
        if day_names:
            label = f"Weekly on {day_names}" if interval == 1 else f"Every {interval} weeks on {day_names}"
        else:
            label = "Weekly" if interval == 1 else f"Every {interval} weeks"
    elif freq == "monthly":
        try:
            bysetpos = int(getattr(event, "recurrence_bysetpos", None))
        except (TypeError, ValueError):
            bysetpos = None
        if bysetpos in NTH_LABELS and day_names:
            label = f"Monthly on the {NTH_LABELS[bysetpos]} {day_names}"
        else:
            label = "Monthly" if interval == 1 else f"Every {interval} months"
    else:
        label = freq.title()

    until = getattr(event, "recurrence_until", None)
    if until:
        label += f" until {until.strftime('%b %d, %Y')}"
    return label


def _parse_bysetpos(raw: str | None) -> int | None:
    try:
        value = int((raw or "").strip())
    except (TypeError, ValueError):
        return None
    return value if value in (1, 2, 3, 4, 5, -1) else None


def parse_recurrence_form(form) -> RecurrenceSpec:
    raw_freq = (form.get("recurrence_freq") or "").strip().lower()
    try:
        raw_interval = max(1, int(form.get("recurrence_interval") or "1"))
    except (TypeError, ValueError):
        raw_interval = 1
    freq, interval = _normalize_recurrence_freq(raw_freq, raw_interval)
    if not freq:
        return RecurrenceSpec(None)

    until_raw = (form.get("recurrence_until") or "").strip()
    until = None
    if until_raw:
        try:
            until = datetime.strptime(until_raw, "%Y-%m-%d").date()
        except Exception:
            until = None

    byweekday = None
    bysetpos = None
    if freq == "weekly":
        selected = [code for code in form.getlist("recurrence_byweekday") if code in WEEKDAY_MAP]
        if selected:
            byweekday = ",".join(selected)
    elif raw_freq == "monthly_nth":
        nth_day = (form.get("recurrence_nth_weekday") or "").strip().upper()
        byweekday = nth_day if nth_day in WEEKDAY_MAP else None
        bysetpos = _parse_bysetpos(form.get("recurrence_bysetpos")) or 1

    return RecurrenceSpec(
        freq=freq,
        interval=interval,
        byweekday=byweekday,
        until=until,
        bysetpos=bysetpos,
    )
