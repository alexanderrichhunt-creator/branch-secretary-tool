"""Weekly church-cleaning assignments.

Church weeks run Sunday through Saturday, matching the rest of the calendar.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

CLEANING_COLOR = "#3f6212"
CLEANING_BORDER = "#365314"
CLEANING_WASH = "#e7f2d3"
CLEANING_TEXT = "#1a2e05"


def week_start_sunday(d: date) -> date:
    """Sunday that starts the church week containing ``d``."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


def week_end_saturday(week_start: date) -> date:
    return week_start + timedelta(days=6)


def parse_week_start(raw: str | None) -> date | None:
    """Sunday for a ``YYYY-MM-DD`` day or an ISO ``YYYY-Www`` week value.

    An ISO week (Monday–Sunday, as in ``<input type="week">``) maps to the
    Sunday that falls inside that week. That Sunday starts the church week.
    """
    text = (raw or "").strip()
    if not text:
        return None
    upper = text.upper()
    if "-W" in upper:
        try:
            year_s, week_s = upper.split("-W", 1)
            monday = date.fromisocalendar(int(year_s), int(week_s), 1)
        except ValueError:
            return None
        return monday + timedelta(days=6)
    try:
        day = datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None
    return week_start_sunday(day)


def _month_day(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def format_week_range(week_start: date) -> str:
    """Compact range, e.g. ``Oct 25 – 31, 2026`` or ``Oct 25 – Nov 1, 2026``."""
    end = week_end_saturday(week_start)
    if week_start.year == end.year and week_start.month == end.month:
        return f"{_month_day(week_start)} – {end.day}, {end.year}"
    if week_start.year == end.year:
        return f"{_month_day(week_start)} – {_month_day(end)}, {end.year}"
    return f"{_month_day(week_start)}, {week_start.year} – {_month_day(end)}, {end.year}"


def format_week_long(week_start: date) -> str:
    end = week_end_saturday(week_start)
    return (
        f"{week_start.strftime('%A, %B')} {week_start.day} – "
        f"{end.strftime('%A, %B')} {end.day}, {end.year}"
    )


def cleaning_title(names: list[str]) -> str:
    if not names:
        return "Cleaning"
    return "Cleaning: " + ", ".join(names)


# Print columns stay short enough to sit inside one week of day squares.
NAMES_PER_PRINT_COLUMN = 4


def cleaning_name_columns(names: list[str], per_column: int = NAMES_PER_PRINT_COLUMN) -> list[list[str]]:
    """Fill down each column, then start another. At most ``per_column`` names each."""
    size = per_column if per_column > 0 else NAMES_PER_PRINT_COLUMN
    return [list(names[i : i + size]) for i in range(0, len(names), size)]
