from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .models import Interview, Member, Talk, parse_us_date


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

    # Recent speakers: members with a talk in the last 6 months.
    cutoff = today - timedelta(days=183)
    recent_talks = (
        Talk.query.filter(Talk.talk_date >= cutoff)
        .order_by(Talk.talk_date.desc())
        .limit(400)
        .all()
    )
    last_talk_by_member = {}
    recent_speakers = []
    for t in recent_talks:
        if t.member_id in last_talk_by_member:
            continue
        last_talk_by_member[t.member_id] = t.talk_date
        recent_speakers.append(t.member)
        if len(recent_speakers) >= 12:
            break

    upcoming_interviews = (
        Interview.query.filter(Interview.starts_at >= datetime.now() - timedelta(hours=2))
        .order_by(Interview.starts_at.asc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        suggested=recent_speakers,
        last_talk_by_member=last_talk_by_member,
        upcoming_interviews=upcoming_interviews,
        today=today,
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


@main_bp.get("/talks")
@login_required
def talks():
    talks = Talk.query.order_by(Talk.talk_date.desc()).limit(200).all()
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template("talks.html", talks=talks, members=members)


@main_bp.post("/talks/add")
@login_required
def add_talk():
    member_id = int(request.form.get("member_id") or "0")
    talk_date_raw = (request.form.get("talk_date") or "").strip()
    topic = (request.form.get("topic") or "").strip()
    notes = (request.form.get("notes") or "").strip() or None

    if member_id and talk_date_raw and topic:
        talk_date = datetime.strptime(talk_date_raw, "%Y-%m-%d").date()
        t = Talk(member_id=member_id, talk_date=talk_date, topic=topic, notes=notes)
        db.session.add(t)
        db.session.commit()
    return redirect(url_for("main.talks"))


@main_bp.get("/interviews")
@login_required
def interviews():
    interviews = Interview.query.order_by(Interview.starts_at.desc()).limit(200).all()
    members = Member.query.order_by(Member.full_name.asc()).all()
    return render_template("interviews.html", interviews=interviews, members=members)


@main_bp.post("/interviews/add")
@login_required
def add_interview():
    member_id_raw = (request.form.get("member_id") or "").strip()
    starts_at_raw = (request.form.get("starts_at") or "").strip()
    duration_minutes = int(request.form.get("duration_minutes") or "15")
    purpose = (request.form.get("purpose") or "Interview").strip() or "Interview"
    notes = (request.form.get("notes") or "").strip() or None

    if starts_at_raw:
        starts_at = datetime.strptime(starts_at_raw, "%Y-%m-%dT%H:%M")
        member_id = int(member_id_raw) if member_id_raw else None
        i = Interview(
            member_id=member_id,
            starts_at=starts_at,
            duration_minutes=max(5, min(duration_minutes, 180)),
            purpose=purpose,
            notes=notes,
        )
        db.session.add(i)
        db.session.commit()
    return redirect(url_for("main.interviews"))


@main_bp.get("/calendar")
@login_required
def calendar():
    return render_template("calendar.html")


@main_bp.get("/api/events")
@login_required
def api_events():
    # FullCalendar expects ISO date strings.
    talks = Talk.query.all()
    interviews = Interview.query.all()

    events = []
    for t in talks:
        events.append(
            {
                "id": f"talk-{t.id}",
                "title": f"Talk: {t.member.full_name} — {t.topic}",
                "start": t.talk_date.isoformat(),
                "allDay": True,
                "backgroundColor": "#2563eb",
                "borderColor": "#1d4ed8",
            }
        )
    for i in interviews:
        title = f"Interview: {i.purpose}"
        if i.member:
            title = f"Interview: {i.member.full_name} — {i.purpose}"
        end = i.starts_at + timedelta(minutes=i.duration_minutes)
        events.append(
            {
                "id": f"interview-{i.id}",
                "title": title,
                "start": i.starts_at.isoformat(),
                "end": end.isoformat(),
                "allDay": False,
                "backgroundColor": "#16a34a",
                "borderColor": "#15803d",
            }
        )

    return jsonify(events)
