import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    database_url = os.environ.get("DATABASE_URL", "sqlite:///data.db")
    # Render/Neon commonly provide "postgres://" or "postgresql://".
    # SQLAlchemy defaults those to the psycopg2 driver, but this project uses psycopg (v3).
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://") :]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://") :]

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401
    from .routes import main_bp
    from .auth import auth_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")

    with app.app_context():
        db.create_all()
        _apply_schema_patches()
        _maybe_init_admin()

    app.jinja_env.globals["now"] = lambda: datetime.now(tz=timezone.utc)
    app.jinja_env.globals["member_label"] = _member_label
    app.jinja_env.globals["talk_speaker_label"] = _talk_speaker_label
    app.jinja_env.globals["interview_who_label"] = _interview_who_label
    return app


def _apply_schema_patches():
    """Add columns and relax NOT NULL for existing DBs (Postgres + SQLite)."""
    from sqlalchemy import inspect, text

    engine = db.engine
    dialect = engine.dialect.name
    with engine.begin() as conn:
        if dialect == "postgresql":
            conn.execute(
                text("ALTER TABLE talk ADD COLUMN IF NOT EXISTS speaker_text VARCHAR(256)")
            )
            conn.execute(
                text("ALTER TABLE interview ADD COLUMN IF NOT EXISTS who_text VARCHAR(256)")
            )
            conn.execute(text("ALTER TABLE talk ALTER COLUMN member_id DROP NOT NULL"))
        elif dialect == "sqlite":
            _sqlite_patch_talk_interview_schema(conn, engine, inspect)


def _sqlite_patch_talk_interview_schema(conn, engine, sa_inspect):
    from sqlalchemy import text

    insp = sa_inspect(engine)
    if "talk" in insp.get_table_names():
        cols = {c["name"]: c for c in insp.get_columns("talk")}
        if "speaker_text" not in cols:
            conn.execute(text("ALTER TABLE talk ADD COLUMN speaker_text VARCHAR(256)"))
        cols = {c["name"]: c for c in sa_inspect(engine).get_columns("talk")}
        mcol = cols.get("member_id")
        if mcol is not None and mcol.get("nullable") is False:
            # Relax NOT NULL on member_id by rebuilding the table (keeps all rows).
            conn.execute(
                text(
                    """
                CREATE TABLE talk__new (
                  id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                  talk_date DATE NOT NULL,
                  topic VARCHAR(256) NOT NULL,
                  notes TEXT,
                  created_at DATETIME NOT NULL,
                  member_id INTEGER REFERENCES member(id),
                  speaker_text VARCHAR(256)
                )
                """
                )
            )
            conn.execute(
                text(
                    """
                INSERT INTO talk__new (id, talk_date, topic, notes, created_at, member_id, speaker_text)
                SELECT id, talk_date, topic, notes, created_at, member_id, speaker_text
                FROM talk
                """
                )
            )
            conn.execute(text("DROP TABLE talk"))
            conn.execute(text("ALTER TABLE talk__new RENAME TO talk"))
    insp = sa_inspect(engine)
    if "interview" in insp.get_table_names():
        cols_i = {c["name"] for c in insp.get_columns("interview")}
        if "who_text" not in cols_i:
            conn.execute(text("ALTER TABLE interview ADD COLUMN who_text VARCHAR(256)"))


def _talk_speaker_label(talk) -> str:
    if talk.member_id and talk.member is not None:
        return _member_label(talk.member)
    s = (getattr(talk, "speaker_text", None) or "").strip()
    return s or "—"


def _interview_who_label(interview) -> str:
    if interview.member_id and interview.member is not None:
        return _member_label(interview.member)
    s = (getattr(interview, "who_text", None) or "").strip()
    return s or "—"


def _calc_age(birthdate: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))


def _member_label(member) -> str:
    # Works for Member objects; keeps templates simple.
    name = getattr(member, "full_name", None) or ""
    bday = getattr(member, "birthdate", None)
    if not name:
        return ""
    if not bday:
        return name
    try:
        age = _calc_age(bday)
        return f"{name} ({age})"
    except Exception:
        return name


def _maybe_init_admin():
    from .models import User
    from werkzeug.security import generate_password_hash

    email = os.environ.get("INIT_ADMIN_EMAIL")
    password = os.environ.get("INIT_ADMIN_PASSWORD")
    if not email or not password:
        return

    existing = User.query.filter_by(email=email.lower().strip()).first()
    if existing:
        return

    user = User(
        email=email.lower().strip(),
        password_hash=generate_password_hash(password),
        role="admin",
    )
    db.session.add(user)
    db.session.commit()
