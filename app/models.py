from __future__ import annotations

from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash

from . import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="user")  # "admin" or "user"
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(256), nullable=False, index=True)
    gender = db.Column(db.String(16), nullable=True)
    birthdate = db.Column(db.Date, nullable=True)
    group_label = db.Column(db.String(64), nullable=True)  # e.g., Youth / Adult
    is_regular_attendee = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    talks = db.relationship("Talk", back_populates="member", cascade="all, delete-orphan")
    interviews = db.relationship("Interview", back_populates="member", cascade="all, delete-orphan")


class Talk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    talk_date = db.Column(db.Date, nullable=False, index=True)
    topic = db.Column(db.String(256), nullable=False, default="")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Link to a member, OR use speaker_text for generic/one-off entries.
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True, index=True)
    speaker_text = db.Column(db.String(256), nullable=True)
    member = db.relationship("Member", back_populates="talks")


class SuggestedTalk(db.Model):
    """Working list of talk ideas/speakers not yet assigned to a sacrament date."""

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True, index=True)
    speaker_text = db.Column(db.String(256), nullable=True)
    topic = db.Column(db.String(256), nullable=False, default="")
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    member = db.relationship("Member", backref=db.backref("suggested_talks", cascade="all, delete-orphan"))

    def speaker_label(self) -> str:
        if self.member_id and self.member is not None:
            return self.member.full_name
        text = (self.speaker_text or "").strip()
        if text:
            return text
        return "—"


class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=15)
    purpose = db.Column(db.String(256), nullable=False, default="Interview")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True, index=True)
    who_text = db.Column(db.String(256), nullable=True)
    member = db.relationship("Member", back_populates="interviews")


class Event(db.Model):
    """Branch meetings and calendar events (supports simple recurrence)."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(256), nullable=True)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    end_at = db.Column(db.DateTime, nullable=True)
    all_day = db.Column(db.Boolean, nullable=False, default=False)
    recurrence_freq = db.Column(db.String(16), nullable=True)  # daily, weekly, monthly
    recurrence_interval = db.Column(db.Integer, nullable=True, default=1)
    recurrence_byweekday = db.Column(db.String(32), nullable=True)  # MO,TU,...
    recurrence_until = db.Column(db.Date, nullable=True)
    category = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class BulletinDefaults(db.Model):
    """Single-row branch defaults for the bulletin builder (id=1)."""

    __tablename__ = "bulletin_defaults"

    id = db.Column(db.Integer, primary_key=True)
    presiding = db.Column(db.String(512), nullable=False, default="")
    conducting = db.Column(db.String(512), nullable=False, default="")
    on_the_stand = db.Column(db.String(512), nullable=False, default="")
    welcome_text = db.Column(db.Text, nullable=False, default="")
    opening_hymn_num = db.Column(db.String(8), nullable=False, default="6")
    opening_hymn_title = db.Column(db.String(256), nullable=False, default="")
    invocation = db.Column(db.String(256), nullable=False, default="(by invitation)")
    branch_business = db.Column(db.Text, nullable=False, default="")
    stake_business = db.Column(db.String(256), nullable=False, default="(if any)")
    announcements = db.Column(db.Text, nullable=False, default="")
    sacrament_notes = db.Column(db.Text, nullable=False, default="")
    sacrament_hymn_num = db.Column(db.String(8), nullable=False, default="190")
    sacrament_hymn_title = db.Column(db.String(256), nullable=False, default="")
    intermediate_hymn_num = db.Column(db.String(8), nullable=False, default="")
    intermediate_hymn_title = db.Column(db.String(256), nullable=False, default="")
    closing_hymn_num = db.Column(db.String(8), nullable=False, default="141")
    closing_hymn_title = db.Column(db.String(256), nullable=False, default="")
    benediction = db.Column(db.String(256), nullable=False, default="(by invitation)")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class BaptismDefaults(db.Model):
    """Single-row branch defaults for the baptism program builder (id=1)."""

    __tablename__ = "baptism_defaults"

    id = db.Column(db.Integer, primary_key=True)
    presiding = db.Column(db.String(512), nullable=False, default="")
    conducting = db.Column(db.String(512), nullable=False, default="")
    welcome_text = db.Column(db.Text, nullable=False, default="")
    location = db.Column(db.String(256), nullable=False, default="")
    opening_hymn_num = db.Column(db.String(8), nullable=False, default="2")
    opening_hymn_title = db.Column(db.String(256), nullable=False, default="")
    opening_hymn_book = db.Column(db.String(16), nullable=False, default="children")
    invocation = db.Column(db.String(256), nullable=False, default="(by invitation)")
    speaker_1 = db.Column(db.String(256), nullable=False, default="")
    speaker_1_topic = db.Column(db.String(256), nullable=False, default="")
    speaker_2 = db.Column(db.String(256), nullable=False, default="")
    speaker_2_topic = db.Column(db.String(256), nullable=False, default="")
    musical_number = db.Column(db.String(256), nullable=False, default="")
    confirmation_text = db.Column(db.Text, nullable=False, default="")
    closing_hymn_num = db.Column(db.String(8), nullable=False, default="120")
    closing_hymn_title = db.Column(db.String(256), nullable=False, default="")
    closing_hymn_book = db.Column(db.String(16), nullable=False, default="children")
    benediction = db.Column(db.String(256), nullable=False, default="(by invitation)")
    reception_notes = db.Column(db.Text, nullable=False, default="")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def parse_us_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        month, day, year = value.split("/")
        return date(int(year), int(month), int(day))
    except Exception:
        return None
