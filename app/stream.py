"""Stream program export for OBS automation.

Provides a stable, stream-shaped JSON payload and API-key authentication
so a local controller does not need a human login session.
"""

from __future__ import annotations

import hmac
import secrets
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, current_app, jsonify, request

from .hymns import HYMN_BOOK_HYMNS, hymn_display, hymn_lyrics, hymn_title, parse_hymn_number

stream_bp = Blueprint("stream", __name__)


def stream_api_key_configured() -> bool:
    return bool((current_app.config.get("STREAM_API_KEY") or "").strip())


def _extract_stream_api_key() -> str:
    """Accept Bearer token, X-Stream-Api-Key header, or api_key query param."""
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()

    header_key = (request.headers.get("X-Stream-Api-Key") or "").strip()
    if header_key:
        return header_key

    return (request.args.get("api_key") or "").strip()


def check_stream_api_key():
    """Validate STREAM_API_KEY. Returns a Flask (response, status) on failure, else None."""
    expected = (current_app.config.get("STREAM_API_KEY") or "").strip()
    if not expected:
        return (
            jsonify(
                {
                    "error": "stream_api_disabled",
                    "message": (
                        "Stream API is not configured. Set STREAM_API_KEY in the "
                        "server environment, then redeploy."
                    ),
                }
            ),
            503,
        )

    provided = _extract_stream_api_key()
    if not provided or not hmac.compare_digest(provided, expected):
        return (
            jsonify(
                {
                    "error": "unauthorized",
                    "message": (
                        "Invalid or missing stream API key. Send "
                        "Authorization: Bearer <key> or X-Stream-Api-Key."
                    ),
                }
            ),
            401,
        )
    return None


def require_stream_api_key(view: Callable):
    """Decorator: require STREAM_API_KEY for machine access (not flask-login)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        denied = check_stream_api_key()
        if denied is not None:
            return denied
        return view(*args, **kwargs)

    return wrapped


def _hymn_payload(num_raw: str | None, title_raw: str | None, *, book: str = HYMN_BOOK_HYMNS) -> dict[str, Any] | None:
    num_raw = (num_raw or "").strip()
    title_raw = (title_raw or "").strip()
    if not num_raw and not title_raw:
        return None

    number = parse_hymn_number(num_raw)
    resolved_title = title_raw or (hymn_title(number, book) if number else "")
    line = hymn_display(num_raw, resolved_title)
    lyrics = hymn_lyrics(number, book) if number else ""

    return {
        "number": str(number) if number else (num_raw.lstrip("#") or None),
        "title": resolved_title,
        "line": line,
        "book": book,
        "lyrics": lyrics or None,
        "has_lyrics": bool(lyrics),
    }


def _speaker_display_name(talk) -> str:
    from .bulletin import bulletin_person_name

    if getattr(talk, "member_id", None) and getattr(talk, "member", None) is not None:
        return bulletin_person_name(talk.member.full_name)
    text = (getattr(talk, "speaker_text", None) or "").strip()
    return text or "—"


def _speakers_payload(talks: list) -> tuple[list[dict[str, Any]], str | None, dict | None]:
    from .bulletin import is_special_meeting_talk, sort_assigned_talks, special_meeting_kind, special_meeting_meta
    from .callings import format_speaker_with_calling

    assigned = sort_assigned_talks(talks)
    speakers: list[dict[str, Any]] = []
    for index, talk in enumerate(assigned, start=1):
        order = getattr(talk, "sort_order", 0) or 0
        calling = (getattr(talk, "calling", None) or "").strip() or None
        name = _speaker_display_name(talk)
        speakers.append(
            {
                "order": order if order > 0 else index,
                "index": index,
                "id": getattr(talk, "id", None),
                "name": name,
                "calling": calling,
                "display_name": format_speaker_with_calling(name, calling),
                "topic": (getattr(talk, "topic", None) or "").strip() or None,
                "notes": (getattr(talk, "notes", None) or "").strip() or None,
                "member_id": getattr(talk, "member_id", None),
                "is_special": False,
            }
        )

    # If the whole meeting is special (fast/testimony, conference), expose that
    # as meeting metadata rather than fake speakers — but still list any non-special talks.
    special_kinds = [special_meeting_kind(t) for t in talks if is_special_meeting_talk(t)]
    special_kind = next((k for k in special_kinds if k), None)
    special_meta = special_meeting_meta(special_kind) if special_kind else None

    return speakers, special_kind, special_meta


def _build_stream_cues(
    *,
    hymns: dict[str, Any],
    speakers: list[dict[str, Any]],
    is_special: bool,
    special_label: str | None,
    speakers_mode: str,
) -> list[dict[str, Any]]:
    """Ordered operator cues for OBS scene switching (hints only)."""
    cues: list[dict[str, Any]] = [
        {
            "id": "pre_service",
            "label": "Pre-service / welcome",
            "scene_hint": "lobby",
        }
    ]

    if hymns.get("opening"):
        cues.append(
            {
                "id": "opening_hymn",
                "label": f"Opening hymn: {hymns['opening'].get('line') or hymns['opening'].get('title')}",
                "scene_hint": "hymn",
                "hymn_key": "opening",
            }
        )

    cues.append(
        {
            "id": "live_open",
            "label": "Live — conducting / business",
            "scene_hint": "live",
        }
    )

    if hymns.get("sacrament"):
        cues.append(
            {
                "id": "sacrament_hymn",
                "label": f"Sacrament hymn: {hymns['sacrament'].get('line') or hymns['sacrament'].get('title')}",
                "scene_hint": "hymn",
                "hymn_key": "sacrament",
            }
        )

    cues.append(
        {
            "id": "sacrament",
            "label": "Sacrament (pause live feed)",
            "scene_hint": "sacrament",
        }
    )

    cues.append(
        {
            "id": "live_resume",
            "label": "Resume live after sacrament",
            "scene_hint": "live",
        }
    )

    if is_special:
        cues.append(
            {
                "id": "special_meeting",
                "label": special_label or speakers_mode.replace("_", " ").title(),
                "scene_hint": "live",
                "speakers_mode": speakers_mode,
            }
        )
    else:
        for speaker in speakers:
            display = speaker.get("display_name") or speaker["name"]
            cues.append(
                {
                    "id": f"speaker_{speaker['index']}",
                    "label": f"Speaker {speaker['index']}: {display}",
                    "scene_hint": "speaker",
                    "speaker_index": speaker["index"],
                    "speaker_name": display,
                    "calling": speaker.get("calling"),
                    "topic": speaker.get("topic"),
                }
            )
            # Intermediate hymn sits after the first speaker when present.
            if speaker["index"] == 1 and hymns.get("intermediate") and len(speakers) >= 2:
                cues.append(
                    {
                        "id": "intermediate_hymn",
                        "label": (
                            f"Intermediate hymn: "
                            f"{hymns['intermediate'].get('line') or hymns['intermediate'].get('title')}"
                        ),
                        "scene_hint": "hymn",
                        "hymn_key": "intermediate",
                    }
                )

    if hymns.get("closing"):
        cues.append(
            {
                "id": "closing_hymn",
                "label": f"Closing hymn: {hymns['closing'].get('line') or hymns['closing'].get('title')}",
                "scene_hint": "hymn",
                "hymn_key": "closing",
            }
        )

    cues.append(
        {
            "id": "intermission",
            "label": "Between meetings",
            "scene_hint": "intermission",
        }
    )
    cues.append(
        {
            "id": "sunday_school",
            "label": "Sunday School (live only)",
            "scene_hint": "sunday_school",
        }
    )
    return cues


def build_stream_program(meeting_date: date, talks: list, *, saved_row=None) -> dict[str, Any]:
    """Assemble OBS-ready program JSON for one sacrament meeting date."""
    from .bulletin import (
        _format_meeting_date,
        bulletin_person_name,
        compose_bulletin_defaults_for_date,
        has_intermediate_hymn,
    )

    bulletin = compose_bulletin_defaults_for_date(meeting_date, talks, saved_row=saved_row)

    # Compose hymn lines the same way the bulletin export does when titles are present.
    for num_key, title_key, line_key in (
        ("opening_hymn_num", "opening_hymn_title", "opening_hymn_line"),
        ("sacrament_hymn_num", "sacrament_hymn_title", "sacrament_hymn_line"),
        ("intermediate_hymn_num", "intermediate_hymn_title", "intermediate_hymn_line"),
        ("closing_hymn_num", "closing_hymn_title", "closing_hymn_line"),
    ):
        if not bulletin.get(line_key):
            bulletin[line_key] = hymn_display(bulletin.get(num_key), bulletin.get(title_key))

    hymns = {
        "opening": _hymn_payload(bulletin.get("opening_hymn_num"), bulletin.get("opening_hymn_title")),
        "sacrament": _hymn_payload(bulletin.get("sacrament_hymn_num"), bulletin.get("sacrament_hymn_title")),
        "intermediate": _hymn_payload(
            bulletin.get("intermediate_hymn_num"), bulletin.get("intermediate_hymn_title")
        ),
        "closing": _hymn_payload(bulletin.get("closing_hymn_num"), bulletin.get("closing_hymn_title")),
    }

    speakers, special_kind, special_meta = _speakers_payload(talks)
    speakers_mode = (bulletin.get("speakers_mode") or "talks").strip()
    is_special = bool(special_kind) or speakers_mode in {
        "fast_testimony",
        "branch_conference",
        "stake_conference",
        "general_conference",
    }
    special_label = (special_meta or {}).get("label") if special_meta else None
    if is_special and not special_label:
        special_label = speakers_mode.replace("_", " ").title()

    def _person(value: str | None) -> str:
        return bulletin_person_name(value or "") if value else ""

    meeting = {
        "type": "sacrament",
        "speakers_mode": speakers_mode,
        "is_first_sacrament_sunday": bool(bulletin.get("is_first_sacrament_sunday")),
        "is_special": is_special,
        "special_kind": special_kind,
        "special_label": special_label,
        "presiding": _person(bulletin.get("presiding")),
        "conducting": _person(bulletin.get("conducting")),
        "on_the_stand": _person(bulletin.get("on_the_stand")),
        "invocation": (bulletin.get("invocation") or "").strip() or None,
        "benediction": (bulletin.get("benediction") or "").strip() or None,
        "welcome_text": (bulletin.get("welcome_text") or "").strip() or None,
        "branch_business": (bulletin.get("branch_business") or "").strip() or None,
        "stake_business": (bulletin.get("stake_business") or "").strip() or None,
        "announcements": (bulletin.get("announcements") or "").strip() or None,
        "sacrament_notes": (bulletin.get("sacrament_notes") or "").strip() or None,
        "speakers_text": (bulletin.get("speakers_text") or "").strip() or None,
        "has_intermediate_hymn": has_intermediate_hymn(
            {
                "intermediate_hymn_line": bulletin.get("intermediate_hymn_line")
                or hymn_display(
                    bulletin.get("intermediate_hymn_num"),
                    bulletin.get("intermediate_hymn_title"),
                )
            }
        ),
    }

    return {
        "schema_version": 1,
        "date": meeting_date.isoformat(),
        "date_display": _format_meeting_date(meeting_date),
        "meeting": meeting,
        "hymns": hymns,
        "speakers": speakers,
        "stream_cues": _build_stream_cues(
            hymns=hymns,
            speakers=speakers,
            is_special=is_special,
            special_label=special_label,
            speakers_mode=speakers_mode,
        ),
        "bulletin_saved": bool(bulletin.get("saved")),
        "bulletin_updated_at": bulletin.get("updated_at"),
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def generate_stream_api_key() -> str:
    """Helper for admins generating a new key offline."""
    return secrets.token_urlsafe(32)


def _week_start_sunday(d: date) -> date:
    # Monday=0 … Sunday=6 → back up to Sunday
    return d - timedelta(days=(d.weekday() + 1) % 7)


def _talks_for_stream_date(talk_date: date) -> list:
    """Talks on this date, or elsewhere in the same Sunday-based week."""
    from .bulletin import talk_sort_key
    from .models import Talk

    talks = Talk.query.filter_by(talk_date=talk_date).all()
    if not talks:
        week_start = _week_start_sunday(talk_date)
        week_end = week_start + timedelta(days=6)
        talks = Talk.query.filter(Talk.talk_date >= week_start, Talk.talk_date <= week_end).all()
    return sorted(talks, key=talk_sort_key)


@stream_bp.get("/api/stream/program")
def api_stream_program():
    """OBS-ready sacrament program for a date (API key auth, not session login).

    Auth (any one):
      Authorization: Bearer <STREAM_API_KEY>
      X-Stream-Api-Key: <STREAM_API_KEY>
      ?api_key=<STREAM_API_KEY>  (convenient for quick tests; prefer headers)

    Query:
      date=YYYY-MM-DD  (optional; defaults to next/this sacrament Sunday)
    """
    from .bulletin import default_sacrament_sunday
    from .models import BulletinDraft

    denied = check_stream_api_key()
    if denied is not None:
        return denied

    raw = (request.args.get("date") or "").strip()
    if raw:
        try:
            meeting_date = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"error": "invalid_date", "message": "Use date=YYYY-MM-DD."}), 400
    else:
        meeting_date = default_sacrament_sunday()

    talks = _talks_for_stream_date(meeting_date)
    saved_row = BulletinDraft.query.filter_by(meeting_date=meeting_date).first()
    payload = build_stream_program(meeting_date, talks, saved_row=saved_row)
    return jsonify(payload)
