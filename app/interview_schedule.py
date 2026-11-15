"""Split stored interviews into upcoming and past lists.

Interview times are naive wall-clock values typed by the secretary. The branch
is in America/Chicago, and the server clock is UTC, so "later today" is decided
in Central time rather than by comparing those values to UTC.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .event_utils import iter_event_occurrences

APP_TIMEZONE = ZoneInfo("America/Chicago")
# Enough recent history to scan, without letting years of interviews fill the page.
PAST_INTERVIEW_PREVIEW = 6


@dataclass(frozen=True)
class InterviewEntry:
    interview: object
    when: datetime


def app_now() -> datetime:
    """Naive Central-time clock, comparable with stored interview times."""
    return datetime.now(APP_TIMEZONE).replace(tzinfo=None)


def next_interview_at(interview, after: datetime) -> datetime | None:
    """Next start at or after ``after``.

    A one-off interview returns its start only when that start is still ahead.
    A series returns the next occurrence, not the original series start.
    """
    if not getattr(interview, "recurrence_freq", None):
        starts_at = interview.starts_at
        return starts_at if starts_at >= after else None

    horizon = after + timedelta(days=400)
    for occ_start, _occ_end in iter_event_occurrences(interview, after, horizon):
        if occ_start >= after:
            return occ_start
    return None


def _past_when(interview) -> datetime:
    """Sort key for an interview that is already over.

    An ended series is ordered by its last day, at the usual meeting time.
    """
    until = getattr(interview, "recurrence_until", None)
    if until is not None:
        return datetime.combine(until, interview.starts_at.time())
    return interview.starts_at


def partition_interviews(interviews, now: datetime) -> tuple[list[InterviewEntry], list[InterviewEntry]]:
    """Upcoming soonest-first, past most-recent-first.

    ``now`` is a naive Central-time wall clock. A start later today is upcoming.
    An open series contributes its next occurrence, not the day the series began.
    """
    upcoming: list[InterviewEntry] = []
    past: list[InterviewEntry] = []
    for interview in interviews:
        if getattr(interview, "recurrence_freq", None):
            nxt = next_interview_at(interview, now)
            if nxt is not None:
                upcoming.append(InterviewEntry(interview, nxt))
            else:
                past.append(InterviewEntry(interview, _past_when(interview)))
            continue
        if interview.starts_at >= now:
            upcoming.append(InterviewEntry(interview, interview.starts_at))
        else:
            past.append(InterviewEntry(interview, interview.starts_at))

    def _tie(entry: InterviewEntry) -> int:
        return getattr(entry.interview, "id", 0) or 0

    upcoming.sort(key=lambda entry: (entry.when, _tie(entry)))
    past.sort(key=lambda entry: (entry.when, _tie(entry)), reverse=True)
    return upcoming, past
