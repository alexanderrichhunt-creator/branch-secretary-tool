from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import func

from . import db
from .models import Member, Talk

TALK_RECENCY_RED_DAYS = 92
TALK_RECENCY_YELLOW_DAYS = 183

STATUS_NEVER = "never"
STATUS_AVAILABLE = "available"
STATUS_CONSIDER = "consider"
STATUS_RECENT = "recent"

STATUS_LABELS = {
    STATUS_NEVER: "Never spoke",
    STATUS_AVAILABLE: "Available",
    STATUS_CONSIDER: "Consider waiting",
    STATUS_RECENT: "Spoke recently",
}


def member_talk_recency(exclude_talk_id: int | None = None) -> dict[str, dict]:
    """Last talk date per member for scheduling hints."""
    today = date.today()
    q = db.session.query(Talk.member_id, func.max(Talk.talk_date)).filter(Talk.member_id.isnot(None))
    if exclude_talk_id:
        q = q.filter(Talk.id != exclude_talk_id)
    rows = q.group_by(Talk.member_id).all()
    out: dict[str, dict] = {}
    for member_id, last_talk in rows:
        if not member_id or not last_talk:
            continue
        out[str(member_id)] = {
            "last_talk_date": last_talk.isoformat(),
            "days_since": (today - last_talk).days,
        }
    return out


def talk_availability_status(days_since: int | None) -> str:
    if days_since is None:
        return STATUS_NEVER
    if days_since <= TALK_RECENCY_RED_DAYS:
        return STATUS_RECENT
    if days_since <= TALK_RECENCY_YELLOW_DAYS:
        return STATUS_CONSIDER
    return STATUS_AVAILABLE


def _pool_sort_key(status: str, days_since: int | None, name: str) -> tuple:
    tier = {
        STATUS_NEVER: 0,
        STATUS_AVAILABLE: 1,
        STATUS_CONSIDER: 2,
        STATUS_RECENT: 3,
    }.get(status, 4)
    if status == STATUS_NEVER:
        secondary = 0
    elif status == STATUS_AVAILABLE:
        secondary = -(days_since or 0)
    elif status == STATUS_CONSIDER:
        secondary = days_since or 0
    else:
        secondary = -(days_since or 0)
    return (tier, secondary, name.lower())


def last_talk_summary(recency: dict | None) -> str:
    if not recency or not recency.get("last_talk_date"):
        return "No prior talk"
    days = recency.get("days_since", 0)
    if days <= 0:
        return "Last spoke today"
    if days == 1:
        return "Last spoke 1 day ago"
    if days < 45:
        return f"Last spoke {days} days ago"
    months = max(1, round(days / 30.44))
    if months == 1:
        return "Last spoke about 1 month ago"
    return f"Last spoke about {months} months ago"


def build_speaker_pool(*, regular_only: bool = True) -> list[dict]:
    """Regular attendees with talk recency, best scheduling candidates first."""
    recency = member_talk_recency()
    query = Member.query
    if regular_only:
        query = query.filter(Member.is_regular_attendee.is_(True))
    members = query.order_by(Member.full_name.asc()).all()

    pool: list[dict] = []
    for member in members:
        info = recency.get(str(member.id))
        days_since = info.get("days_since") if info else None
        last_talk_date = info.get("last_talk_date") if info else None
        if not last_talk_date:
            days_since = None
        status = talk_availability_status(days_since)
        pool.append(
            {
                "member": member,
                "member_id": member.id,
                "name": member.full_name,
                "group_label": member.group_label or "",
                "is_regular_attendee": bool(member.is_regular_attendee),
                "last_talk_date": last_talk_date,
                "last_talk_display": (
                    datetime.strptime(last_talk_date, "%Y-%m-%d").strftime("%b %d, %Y")
                    if last_talk_date
                    else ""
                ),
                "days_since": days_since,
                "status": status,
                "status_label": STATUS_LABELS[status],
                "last_talk_summary": last_talk_summary(info),
                "sort_key": _pool_sort_key(status, days_since, member.full_name),
            }
        )

    pool.sort(key=lambda row: row["sort_key"])
    return pool


def split_speaker_pool_by_group(pool: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split a speaker pool into adult and youth lists (preserves sort order)."""
    youth: list[dict] = []
    adult: list[dict] = []
    for row in pool:
        if (row.get("group_label") or "").strip().lower() == "youth":
            youth.append(row)
        else:
            adult.append(row)
    return adult, youth


def members_for_talk_select() -> tuple[list[dict], list[Member]]:
    """Speaker pool rows first, then members not marked as regular attendees."""
    pool = build_speaker_pool(regular_only=True)
    others = (
        Member.query.filter(Member.is_regular_attendee.is_(False))
        .order_by(Member.full_name.asc())
        .all()
    )
    return pool, others
