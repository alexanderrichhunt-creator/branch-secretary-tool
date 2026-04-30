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
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    talks = db.relationship("Talk", back_populates="member", cascade="all, delete-orphan")
    interviews = db.relationship("Interview", back_populates="member", cascade="all, delete-orphan")


class Talk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    talk_date = db.Column(db.Date, nullable=False, index=True)
    topic = db.Column(db.String(256), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Link to a member, OR use speaker_text for generic/one-off entries.
    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True, index=True)
    speaker_text = db.Column(db.String(256), nullable=True)
    member = db.relationship("Member", back_populates="talks")


class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    duration_minutes = db.Column(db.Integer, nullable=False, default=15)
    purpose = db.Column(db.String(256), nullable=False, default="Interview")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    member_id = db.Column(db.Integer, db.ForeignKey("member.id"), nullable=True, index=True)
    # When no member is selected, e.g. "Visiting high councilor" or a generic label.
    who_text = db.Column(db.String(256), nullable=True)
    member = db.relationship("Member", back_populates="interviews")


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
