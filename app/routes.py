from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from . import db
from .models import Event, Interview, Member, Talk, User, parse_us_date


def _short_calendar_title(text: str, max_len: int = 40) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _parse_talk_speaker_submission():
    member_raw = (request.form.get("member_id") or "").strip()
    member_id = int(member_raw) if member_raw and int(member_raw) > 0 else None
    speaker_text = (request.form.get("speaker_text") or "").strip() or None
    if member_id:
        speaker_text = None
    return member_id, speaker_text


def _parse_interview_who_submission():
    member_raw = (request.form.get("member_id") or "").strip()
    member_id = int(member_raw) if member_raw and int(member_raw) > 0 else None
    who_text = (request.form.get("who_text") or "").strip() or None
    if member_id:
        who_text = None
    return member_id, who_text


def _parse_interview_schedule_from_form() -> tuple[datetime | None, int | None, str | None]:
    """Parse interview start + duration from datetime-local or calendar date/time fields."""
    starts_at_raw = (request.form.get("starts_at") or "").strip()
    if starts_at_raw:
        try:
            starts_at = datetime.strptime(starts_at_raw, "%Y-%m-%dT%H:%M")
        except Exception:
            return None, None, "Invalid start date & time."
        duration_minutes = int(request.form.get("duration_minutes") or "15")
        return starts_at, max(5, min(duration_minutes, 180)), None

    event_date_raw = (request.form.get("event_date") or "").strip()
    start_time_raw = (request.form.get("start_time") or "").strip()
    end_time_raw = (request.form.get("end_time") or "").strip()
    if not event_date_raw or not start_time_raw:
        return None, None, "Start date & time is required."
    try:
        event_date = datetime.strptime(event_date_raw, "%Y-%m-%d").date()
        start_time = datetime.strptime(start_time_raw, "%H:%M").time()
        starts_at = datetime.combine(event_date, start_time)
    except Exception:
        return None, None, "Invalid start date & time."

    duration_minutes = 15
    if end_time_raw:
        try:
            end_time = datetime.strptime(end_time_raw, "%H:%M").time()
            end_at = datetime.combine(event_date, end_time)
            if end_at <= starts_at:
                end_at += timedelta(days=1)
            duration_minutes = max(5, min(int((end_at - starts_at).total_seconds() // 60), 180))
        except Exception:
            return None, None, "Invalid end time."
    return starts_at, duration_minutes, None


def _talk_speaker_name(t: Talk) -> str:
    if t.member_id and t.member is not None:
        return t.member.full_name
    return (t.speaker_text or "").strip() or "—"


def _talk_calendar_title(t: Talk) -> str:
    speaker = _talk_speaker_name(t)
    topic = (t.topic or "").strip()
    if topic:
        return f"Talk: {speaker} — {topic}"
    return f"Talk: {speaker}"


def _interview_subject_name(i: Interview) -> str:
    if i.member_id and i.member is not None:
        return i.member.full_name
    return (i.who_text or "").strip() or "—"


def _week_start_sunday(d: date) -> date:
    """Sunday-start week containing date d."""
    return d - timedelta(days=(d.weekday() + 1) % 7)


MAX_TALKS_PER_SACRAMENT_WEEK = 4


def _talks_in_week(talk_date: date) -> int:
    week_start = _week_start_sunday(talk_date)
    week_end = week_start + timedelta(days=6)
    return Talk.query.filter(
        Talk.talk_date >= week_start,
        Talk.talk_date <= week_end,
    ).count()


def _build_current_talk_week(recent_talks: list[Talk], today: date) -> dict:
    """Week block for the upcoming/current sacrament Sunday."""
    from .bulletin import default_sacrament_sunday

    sacrament_date = default_sacrament_sunday(today)
    week_start = _week_start_sunday(sacrament_date)
    week_talks = sorted(
        (t for t in recent_talks if _week_start_sunday(t.talk_date) == week_start),
        key=lambda t: t.talk_date,
    )
    return {
        "week_start": week_start,
        "week_end": week_start + timedelta(days=6),
        "sacrament_date": sacrament_date,
        "talks": week_talks,
    }


def _build_talk_sunday_groups(
    recent_talks: list[Talk],
    cutoff: date,
    today: date,
    *,
    exclude_week_start: date | None = None,
) -> list[dict]:
    """Every sacrament Sunday in range, newest first, with talks grouped per week."""
    from .bulletin import default_sacrament_sunday

    by_week: dict[date, list[Talk]] = defaultdict(list)
    for talk in recent_talks:
        by_week[_week_start_sunday(talk.talk_date)].append(talk)

    groups: list[dict] = []
    week_start = _week_start_sunday(default_sacrament_sunday(today))
    cutoff_week = _week_start_sunday(cutoff)
    while week_start >= cutoff_week:
        if exclude_week_start is None or week_start != exclude_week_start:
            talks = sorted(by_week.get(week_start, []), key=lambda t: t.talk_date)
            groups.append(
                {
                    "sacrament_date": week_start,
                    "week_end": week_start + timedelta(days=6),
                    "talks": talks,
                    "month_label": week_start.strftime("%B %Y"),
                }
            )
        week_start -= timedelta(days=7)
    return groups


def _redirect_after_interview_action():
    if (request.form.get("return_to") or "").strip() == "calendar":
        return redirect(url_for("main.calendar"))
    return redirect(url_for("main.interviews"))


def _redirect_after_event_action():
    if (request.form.get("return_to") or "").strip() == "calendar":
        return redirect(url_for("main.calendar"))
    return redirect(url_for("main.events"))


def _parse_event_times_from_form():
    """Parse date, times, and all-day flag from an event form."""
    event_date_raw = (request.form.get("event_date") or "").strip()
    all_day = (request.form.get("all_day") or "").strip() == "1"
    if not event_date_raw:
        return None, None, None, "Date is required."

    try:
        event_date = datetime.strptime(event_date_raw, "%Y-%m-%d").date()
    except Exception:
        return None, None, None, "Invalid date."

    if all_day:
        starts_at = datetime.combine(event_date, datetime.min.time())
        end_at = starts_at + timedelta(days=1)
        return starts_at, end_at, True, None

    start_time_raw = (request.form.get("start_time") or "").strip()
    end_time_raw = (request.form.get("end_time") or "").strip()
    if not start_time_raw or not end_time_raw:
        return None, None, None, "Start and end times are required."

    try:
        start_time = datetime.strptime(start_time_raw, "%H:%M").time()
        end_time = datetime.strptime(end_time_raw, "%H:%M").time()
    except Exception:
        return None, None, None, "Invalid start or end time."

    starts_at = datetime.combine(event_date, start_time)
    end_at = datetime.combine(event_date, end_time)
    if end_at <= starts_at:
        end_at += timedelta(days=1)
    return starts_at, end_at, False, None


def _build_upcoming_schedule_items(limit: int = 12) -> list[dict]:
    from .event_utils import event_category_label, iter_event_occurrences, recurrence_label

    now = datetime.now() - timedelta(hours=2)
    horizon = now + timedelta(days=120)
    items: list[dict] = []

    interviews = (
        Interview.query.filter(Interview.starts_at >= now)
        .order_by(Interview.starts_at.asc())
        .limit(limit * 2)
        .all()
    )
    for interview in interviews:
        items.append(
            {
                "kind": "interview",
                "starts_at": interview.starts_at,
                "all_day": False,
                "title": f"Interview: {_interview_subject_name(interview)}",
                "subtitle": f"{interview.purpose} ({interview.duration_minutes} min)",
                "edit_url": url_for("main.edit_interview", interview_id=interview.id),
            }
        )

    for event in Event.query.order_by(Event.starts_at.asc()).all():
        for occ_start, _occ_end in iter_event_occurrences(event, now, horizon):
            if occ_start < now:
                continue
            repeat = recurrence_label(event)
            category_label = event_category_label(getattr(event, "category", None))
            subtitle_parts = [category_label]
            if repeat:
                subtitle_parts.append(repeat)
            elif event.location:
                subtitle_parts.append(event.location)
            items.append(
                {
                    "kind": "event",
                    "category": getattr(event, "category", None),
                    "starts_at": occ_start,
                    "all_day": event.all_day,
                    "title": event.title,
                    "subtitle": " · ".join(subtitle_parts),
                    "edit_url": url_for("main.edit_event", event_id=event.id),
                }
            )

    items.sort(key=lambda item: item["starts_at"])
    return items[:limit]


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@main_bp.get("/dashboard")
@login_required
def dashboard():
    today = date.today()
    cutoff = today - timedelta(days=183)

    recent_talks = (
        Talk.query.filter(Talk.talk_date >= cutoff)
        .order_by(Talk.talk_date.desc())
        .all()
    )
    current_talk_week = _build_current_talk_week(recent_talks, today)
    talk_sunday_groups = _build_talk_sunday_groups(
        recent_talks,
        cutoff,
        today,
        exclude_week_start=current_talk_week["week_start"],
    )

    upcoming_items = _build_upcoming_schedule_items(limit=12)

    return render_template(
        "dashboard.html",
        talk_sunday_groups=talk_sunday_groups,
        current_talk_week=current_talk_week,
        upcoming_items=upcoming_items,
        today=today,
        cutoff=cutoff,
        max_talks_per_week=MAX_TALKS_PER_SACRAMENT_WEEK,
        members=Member.query.order_by(Member.full_name.asc()).all(),
        member_talk_recency=_member_talk_recency(),
    )


@main_bp.get("/members")
@login_required
def members():
    q = (request.args.get("q") or "").strip()
    query = Member.query
    if q:
        query = query.filter(Member.full_name.ilike(f"%{q}%"))
    members = query.order_by(Member.full_name.asc()).limit(200).all()
    return render_template("members.html", members=members, q=q, today=date.today())


@main_bp.post("/members/import")
@login_required
def import_members_csv():
    """
    Import a CSV with columns like:
      Name, Gender, Birth Date, Category

    This is designed to handle quoted fields that may contain newlines.
    """
    file = request.files.get("file")
    if not file:
        return redirect(url_for("main.members"))

    # Decode as UTF-8 with a fallback that won’t crash on odd characters.
    text = io.TextIOWrapper(file.stream, encoding="utf-8", errors="replace", newline="")
    reader = csv.DictReader(text)

    created = 0
    updated = 0
    skipped = 0

    def _norm_key(k: str) -> str:
        return (k or "").strip().lstrip("\ufeff").lower()

    def _row_get(row_dict: dict, *keys: str) -> str:
        if not row_dict:
            return ""
        normalized = {_norm_key(k): v for k, v in row_dict.items()}
        for k in keys:
            v = normalized.get(_norm_key(k))
            if v is None:
                continue
            return str(v)
        return ""

    for row in reader:
        raw_name = _row_get(
            row,
            "Name",
            "FullName",
            "Full Name",
            "Preferred Name",
            "Member",
            "Member Name",
        ).strip()

        # Fallback: First/Last columns
        if not raw_name:
            first = _row_get(row, "First", "First Name", "Given Name").strip()
            last = _row_get(row, "Last", "Last Name", "Surname", "Family Name").strip()
            raw_name = f"{first} {last}".strip()

        name = " ".join(raw_name.replace("\r", " ").replace("\n", " ").split())
        if not name:
            skipped += 1
            continue

        gender = _row_get(row, "Gender", "Sex").strip() or None
        birthdate = parse_us_date(
            _row_get(row, "Birth Date", "Birthdate", "DOB", "Date of Birth").strip() or None
        )
        group_label = _row_get(row, "Category", "Group", "Class", "Organization").strip() or None

        member = Member.query.filter_by(full_name=name).first()
        if not member:
            member = Member(full_name=name, gender=gender, birthdate=birthdate, group_label=group_label)
            db.session.add(member)
            created += 1
        else:
            # Only fill in blanks (don’t overwrite if you’ve corrected something manually).
            changed = False
            if gender and not member.gender:
                member.gender = gender
                changed = True
            if birthdate and not member.birthdate:
                member.birthdate = birthdate
                changed = True
            if group_label and not member.group_label:
                member.group_label = group_label
                changed = True
            if changed:
                updated += 1
            else:
                skipped += 1

    db.session.commit()
    flash(f"Import complete: {created} created, {updated} updated, {skipped} skipped.", "success")
    return redirect(url_for("main.members"))


@main_bp.post("/members/reset")
@login_required
def reset_members():
    if getattr(current_user, "role", None) != "admin":
        flash("Only admins can delete all members.", "danger")
        return redirect(url_for("main.members"))

    confirm = (request.form.get("confirm") or "").strip()
    if confirm != "DELETE":
        flash('Type DELETE to confirm, then click "Delete all members".', "warning")
        return redirect(url_for("main.members"))

    # Bulk deletes (fast) in child->parent order.
    Talk.query.delete()
    Interview.query.delete()
    Member.query.delete()
    db.session.commit()

    flash("All members (and related talks/interviews) were deleted.", "success")
    return redirect(url_for("main.members"))


@main_bp.post("/members/<int:member_id>/delete")
@login_required
def delete_member(member_id: int):
    if getattr(current_user, "role", None) != "admin":
        flash("Only admins can delete members.", "danger")
        return redirect(url_for("main.members"))

    member = Member.query.get_or_404(member_id)
    name = member.full_name
    db.session.delete(member)
    db.session.commit()

    flash(f"Deleted member: {name}", "success")
    return redirect(url_for("main.members", q=request.args.get("q") or ""))


@main_bp.post("/members/add")
@login_required
def add_member():
    full_name = (request.form.get("full_name") or "").strip()
    gender = (request.form.get("gender") or "").strip() or None
    group_label = (request.form.get("group_label") or "").strip() or None
    birthdate_raw = (request.form.get("birthdate") or "").strip()
    birthdate = None
    if birthdate_raw:
        try:
            birthdate = datetime.strptime(birthdate_raw, "%Y-%m-%d").date()
        except Exception:
            birthdate = None

    if full_name:
        m = Member(full_name=full_name, gender=gender, group_label=group_label, birthdate=birthdate)
        db.session.add(m)
        db.session.commit()
    return redirect(url_for("main.members"))


def _member_talk_recency(exclude_talk_id: int | None = None) -> dict[str, dict]:
    """Last talk date per member for scheduling hints on the talks form."""
    from sqlalchemy import func

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


@main_bp.get("/talks")
@login_required
def talks():
    talks = Talk.query.order_by(Talk.talk_date.desc()).limit(200).all()
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template(
        "talks.html",
        talks=talks,
        members=members,
        member_talk_recency=_member_talk_recency(),
    )


def _redirect_after_talk_action():
    if (request.form.get("return_to") or "").strip() == "dashboard":
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.talks"))


@main_bp.post("/talks/add")
@login_required
def add_talk():
    member_id, speaker_text = _parse_talk_speaker_submission()
    talk_date_raw = (request.form.get("talk_date") or "").strip()
    topic = (request.form.get("topic") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None

    if not talk_date_raw:
        flash("Date is required.", "warning")
        return _redirect_after_talk_action()
    if not member_id and not speaker_text:
        flash("Choose a speaker from the list or type a name.", "warning")
        return _redirect_after_talk_action()
    try:
        talk_date = datetime.strptime(talk_date_raw, "%Y-%m-%d").date()
    except Exception:
        flash("Invalid date.", "warning")
        return _redirect_after_talk_action()
    if _talks_in_week(talk_date) >= MAX_TALKS_PER_SACRAMENT_WEEK:
        flash(
            f"That week already has {MAX_TALKS_PER_SACRAMENT_WEEK} talks logged.",
            "warning",
        )
        return _redirect_after_talk_action()
    t = Talk(
        member_id=member_id,
        speaker_text=speaker_text,
        talk_date=talk_date,
        topic=topic,
        notes=notes,
    )
    db.session.add(t)
    db.session.commit()
    flash("Talk saved.", "success")
    return _redirect_after_talk_action()


@main_bp.get("/talks/<int:talk_id>/edit")
@login_required
def edit_talk(talk_id: int):
    talk = Talk.query.get_or_404(talk_id)
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template(
        "talk_edit.html",
        talk=talk,
        members=members,
        member_talk_recency=_member_talk_recency(exclude_talk_id=talk.id),
    )


@main_bp.post("/talks/<int:talk_id>/edit")
@login_required
def edit_talk_post(talk_id: int):
    talk = Talk.query.get_or_404(talk_id)

    member_id, speaker_text = _parse_talk_speaker_submission()
    talk_date_raw = (request.form.get("talk_date") or "").strip()
    topic = (request.form.get("topic") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None

    if not talk_date_raw:
        flash("Date is required.", "warning")
        return redirect(url_for("main.edit_talk", talk_id=talk_id))
    if not member_id and not speaker_text:
        flash("Choose a speaker or enter a name under “Speaker (free text)”.", "warning")
        return redirect(url_for("main.edit_talk", talk_id=talk_id))

    try:
        talk.talk_date = datetime.strptime(talk_date_raw, "%Y-%m-%d").date()
    except Exception:
        flash("Invalid date.", "warning")
        return redirect(url_for("main.edit_talk", talk_id=talk_id))

    talk.member_id = member_id
    talk.speaker_text = speaker_text
    talk.topic = topic
    talk.notes = notes
    db.session.commit()

    flash("Talk updated.", "success")
    return redirect(url_for("main.talks"))


@main_bp.post("/talks/<int:talk_id>/delete")
@login_required
def delete_talk(talk_id: int):
    talk = Talk.query.get_or_404(talk_id)
    db.session.delete(talk)
    db.session.commit()
    flash("Talk deleted.", "success")
    return redirect(url_for("main.talks"))


@main_bp.get("/interviews")
@login_required
def interviews():
    interviews = Interview.query.order_by(Interview.starts_at.desc()).limit(200).all()
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template("interviews.html", interviews=interviews, members=members)


@main_bp.get("/admin/users")
@login_required
def admin_users():
    if getattr(current_user, "role", None) != "admin":
        flash("Only admins can view user accounts.", "danger")
        return redirect(url_for("main.dashboard"))
    users = User.query.order_by(User.email.asc()).all()
    return render_template("admin/users.html", users=users)


@main_bp.post("/interviews/add")
@login_required
def add_interview():
    member_id, who_text = _parse_interview_who_submission()
    starts_at, duration_minutes, err = _parse_interview_schedule_from_form()
    purpose = (request.form.get("purpose") or "Interview").strip() or "Interview"
    notes = (request.form.get("notes") or "").strip() or None

    if err:
        flash(err, "warning")
        return _redirect_after_interview_action()
    if starts_at is None or duration_minutes is None:
        flash("Start date & time is required.", "warning")
        return _redirect_after_interview_action()
    i = Interview(
        member_id=member_id,
        who_text=who_text,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        purpose=purpose,
        notes=notes,
    )
    db.session.add(i)
    db.session.commit()
    flash("Interview saved.", "success")
    return _redirect_after_interview_action()


@main_bp.get("/interviews/<int:interview_id>/edit")
@login_required
def edit_interview(interview_id: int):
    interview = Interview.query.get_or_404(interview_id)
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template("interview_edit.html", interview=interview, members=members)


@main_bp.post("/interviews/<int:interview_id>/edit")
@login_required
def edit_interview_post(interview_id: int):
    interview = Interview.query.get_or_404(interview_id)

    member_id, who_text = _parse_interview_who_submission()
    starts_at_raw = (request.form.get("starts_at") or "").strip()
    duration_minutes = int(request.form.get("duration_minutes") or "15")
    purpose = (request.form.get("purpose") or "Interview").strip() or "Interview"
    notes = (request.form.get("notes") or "").strip() or None

    if not starts_at_raw:
        flash("Start date & time is required.", "warning")
        return redirect(url_for("main.edit_interview", interview_id=interview_id))

    try:
        starts_at = datetime.strptime(starts_at_raw, "%Y-%m-%dT%H:%M")
    except Exception:
        flash("Invalid start date & time.", "warning")
        return redirect(url_for("main.edit_interview", interview_id=interview_id))

    interview.starts_at = starts_at
    interview.duration_minutes = max(5, min(duration_minutes, 180))
    interview.purpose = purpose
    interview.notes = notes
    interview.member_id = member_id
    interview.who_text = who_text
    db.session.commit()

    flash("Interview updated.", "success")
    return redirect(url_for("main.interviews"))


@main_bp.post("/interviews/<int:interview_id>/delete")
@login_required
def delete_interview(interview_id: int):
    interview = Interview.query.get_or_404(interview_id)
    db.session.delete(interview)
    db.session.commit()
    flash("Interview deleted.", "success")
    return redirect(url_for("main.interviews"))


@main_bp.get("/events")
@login_required
def events():
    branch_events = Event.query.order_by(Event.starts_at.desc()).limit(200).all()
    return render_template("events.html", events=branch_events)


@main_bp.post("/events/add")
@login_required
def add_event():
    from .event_utils import normalize_event_category, parse_recurrence_form

    title = (request.form.get("title") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None
    location = (request.form.get("location") or "").strip() or None
    category = normalize_event_category(request.form.get("category"))
    starts_at, end_at, all_day, err = _parse_event_times_from_form()
    if err:
        flash(err, "warning")
        return _redirect_after_event_action()

    freq, interval, byweekday, until = parse_recurrence_form(request.form)
    if freq == "weekly" and not byweekday:
        weekday_codes = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
        byweekday = weekday_codes[starts_at.weekday()]
    event = Event(
        title=title or "Untitled event",
        notes=notes,
        location=location,
        starts_at=starts_at,
        end_at=end_at,
        all_day=all_day,
        recurrence_freq=freq,
        recurrence_interval=interval,
        recurrence_byweekday=byweekday,
        recurrence_until=until,
        category=category,
    )
    db.session.add(event)
    db.session.commit()
    flash("Event saved.", "success")
    return _redirect_after_event_action()


@main_bp.get("/events/<int:event_id>/edit")
@login_required
def edit_event(event_id: int):
    from .event_utils import WEEKDAY_CODES

    event = Event.query.get_or_404(event_id)
    return render_template("event_edit.html", event=event, weekday_codes=WEEKDAY_CODES)


@main_bp.post("/events/<int:event_id>/edit")
@login_required
def edit_event_post(event_id: int):
    from .event_utils import normalize_event_category, parse_recurrence_form

    event = Event.query.get_or_404(event_id)
    title = (request.form.get("title") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None
    location = (request.form.get("location") or "").strip() or None
    category = normalize_event_category(request.form.get("category"))
    starts_at, end_at, all_day, err = _parse_event_times_from_form()
    if err or not title:
        flash(err or "Title is required.", "warning")
        return redirect(url_for("main.edit_event", event_id=event_id))

    freq, interval, byweekday, until = parse_recurrence_form(request.form)
    if freq == "weekly" and not byweekday:
        weekday_codes = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
        byweekday = weekday_codes[starts_at.weekday()]
    event.title = title
    event.notes = notes
    event.location = location
    event.starts_at = starts_at
    event.end_at = end_at
    event.all_day = all_day
    event.recurrence_freq = freq
    event.recurrence_interval = interval
    event.recurrence_byweekday = byweekday
    event.recurrence_until = until
    event.category = category
    db.session.commit()
    flash("Event updated.", "success")
    return redirect(url_for("main.events"))


@main_bp.post("/events/<int:event_id>/delete")
@login_required
def delete_event(event_id: int):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    flash("Event deleted.", "success")
    return redirect(url_for("main.events"))


@main_bp.get("/calendar")
@login_required
def calendar():
    members = Member.query.order_by(Member.full_name.asc()).all()
    from .event_utils import WEEKDAY_CODES

    return render_template("calendar.html", members=members, weekday_codes=WEEKDAY_CODES)


@main_bp.get("/api/events")
@login_required
def api_events():
    from .event_utils import (
        WEEKDAY_CODES,
        event_category_colors,
        event_category_label,
        iter_event_occurrences,
        parse_calendar_range,
        recurrence_label,
    )

    range_start, range_end = parse_calendar_range(
        request.args.get("start"),
        request.args.get("end"),
    )
    range_start_date = range_start.date()
    range_end_date = range_end.date()

    events = []
    talks = Talk.query.filter(
        Talk.talk_date >= range_start_date,
        Talk.talk_date <= range_end_date,
    ).all()
    interviews = Interview.query.filter(
        Interview.starts_at < range_end,
        Interview.starts_at >= range_start - timedelta(days=1),
    ).all()
    branch_events = Event.query.all()

    for t in talks:
        full_title = _talk_calendar_title(t)
        detail = full_title
        if t.notes:
            detail += "\n\nNotes:\n" + t.notes.strip()
        events.append(
            {
                "id": f"talk-{t.id}",
                "title": _short_calendar_title(full_title),
                "start": t.talk_date.isoformat(),
                "allDay": True,
                "backgroundColor": "#2563eb",
                "borderColor": "#1d4ed8",
                "extendedProps": {
                    "kind": "talk",
                    "editUrl": url_for("main.edit_talk", talk_id=t.id),
                    "fullTitle": full_title,
                    "detailText": detail,
                },
            }
        )
    for i in interviews:
        title_line = f"Interview: {_interview_subject_name(i)} — {i.purpose}"
        detail = title_line + f"\n\nDuration: {i.duration_minutes} minutes"
        if i.notes:
            detail += "\n\nNotes:\n" + i.notes.strip()
        end = i.starts_at + timedelta(minutes=i.duration_minutes)
        events.append(
            {
                "id": f"interview-{i.id}",
                "title": _short_calendar_title(title_line),
                "start": i.starts_at.isoformat(),
                "end": end.isoformat(),
                "allDay": False,
                "backgroundColor": "#16a34a",
                "borderColor": "#15803d",
                "extendedProps": {
                    "kind": "interview",
                    "editUrl": url_for("main.edit_interview", interview_id=i.id),
                    "fullTitle": title_line,
                    "detailText": detail,
                },
            }
        )

    for event in branch_events:
        repeat = recurrence_label(event)
        category_label = event_category_label(getattr(event, "category", None))
        bg, border = event_category_colors(getattr(event, "category", None))
        for occ_start, occ_end in iter_event_occurrences(event, range_start, range_end):
            detail = event.title
            if category_label and category_label != "General event":
                detail += f"\n\nCategory: {category_label}"
            if event.location:
                detail += f"\n\nLocation: {event.location}"
            if repeat:
                detail += f"\n\nRepeats: {repeat}"
            if event.notes:
                detail += "\n\nNotes:\n" + event.notes.strip()

            occ_id = f"event-{event.id}-{occ_start.strftime('%Y%m%d%H%M')}"
            fc_event = {
                "id": occ_id,
                "title": _short_calendar_title(event.title),
                "start": occ_start.date().isoformat() if event.all_day else occ_start.isoformat(),
                "allDay": event.all_day,
                "backgroundColor": bg,
                "borderColor": border,
                "extendedProps": {
                    "kind": "event",
                    "category": getattr(event, "category", None),
                    "categoryLabel": category_label,
                    "editUrl": url_for("main.edit_event", event_id=event.id),
                    "fullTitle": event.title,
                    "detailText": detail,
                },
            }
            if event.all_day:
                fc_event["end"] = occ_end.date().isoformat()
            else:
                fc_event["end"] = occ_end.isoformat()
            events.append(fc_event)

    return jsonify(events)


def _talks_for_bulletin_date(talk_date: date) -> list[Talk]:
    talks = Talk.query.filter_by(talk_date=talk_date).order_by(Talk.id.asc()).all()
    if talks:
        return talks
    week_start = _week_start_sunday(talk_date)
    week_end = week_start + timedelta(days=6)
    return (
        Talk.query.filter(Talk.talk_date >= week_start, Talk.talk_date <= week_end)
        .order_by(Talk.talk_date.asc(), Talk.id.asc())
        .all()
    )


@main_bp.get("/bulletin")
@login_required
def bulletin_builder():
    from .bulletin import (
        _parse_hymn_num,
        default_sacrament_sunday,
        get_branch_bulletin_defaults,
        has_saved_branch_defaults,
        speakers_text_for_talks,
    )
    from .hymns import hymn_title

    meeting_date = default_sacrament_sunday()
    defaults = get_branch_bulletin_defaults()
    defaults["meeting_date"] = meeting_date.isoformat()
    defaults["branch_business"] = ""
    defaults["opening_hymn_title"] = hymn_title(_parse_hymn_num(defaults.get("opening_hymn_num")))
    defaults["sacrament_hymn_title"] = hymn_title(_parse_hymn_num(defaults.get("sacrament_hymn_num")))
    defaults["intermediate_hymn_title"] = hymn_title(_parse_hymn_num(defaults.get("intermediate_hymn_num")))
    defaults["closing_hymn_title"] = hymn_title(_parse_hymn_num(defaults.get("closing_hymn_num")))
    defaults["speakers_text"] = speakers_text_for_talks(_talks_for_bulletin_date(meeting_date))

    return render_template(
        "bulletin.html",
        defaults=defaults,
        has_saved_defaults=has_saved_branch_defaults(),
    )


@main_bp.post("/bulletin/save-defaults")
@login_required
def bulletin_save_defaults():
    from .bulletin import save_branch_bulletin_defaults

    save_branch_bulletin_defaults(request.form)
    flash("Branch bulletin defaults saved. They will load automatically next time.", "success")
    return redirect(url_for("main.bulletin_builder"))


@main_bp.get("/api/bulletin/speakers")
@login_required
def api_bulletin_speakers():
    from .bulletin import speakers_text_for_talks

    raw = (request.args.get("date") or "").strip()
    if not raw:
        return jsonify({"speakers_text": ""})
    try:
        talk_date = datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"speakers_text": ""})
    talks = _talks_for_bulletin_date(talk_date)
    return jsonify({"speakers_text": speakers_text_for_talks(talks)})


@main_bp.get("/api/hymn/<int:number>")
@login_required
def api_hymn(number: int):
    from .hymns import hymn_line, hymn_title

    return jsonify({"number": number, "title": hymn_title(number), "line": hymn_line(number)})


@main_bp.post("/bulletin/export/<fmt>")
@login_required
def bulletin_export(fmt: str):
    from .bulletin import bulletin_from_form, build_bulletin_text, export_docx

    data = bulletin_from_form(request.form)
    meeting_date = data.get("meeting_date")
    suffix = meeting_date.isoformat() if meeting_date else "draft"

    try:
        if fmt == "docx":
            payload = export_docx(data)
            return send_file(
                io.BytesIO(payload),
                as_attachment=True,
                download_name=f"branch-bulletin-{suffix}.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        if fmt == "txt":
            text = build_bulletin_text(data)
            return send_file(
                io.BytesIO(text.encode("utf-8")),
                as_attachment=True,
                download_name=f"branch-bulletin-{suffix}.txt",
                mimetype="text/plain; charset=utf-8",
            )
    except Exception as exc:
        flash(f"Could not create {fmt.upper()} file: {exc}", "danger")
        return redirect(url_for("main.bulletin_builder"))

    flash("Unknown export format.", "warning")
    return redirect(url_for("main.bulletin_builder"))
