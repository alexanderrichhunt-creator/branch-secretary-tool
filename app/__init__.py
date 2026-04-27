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
        _maybe_init_admin()

    app.jinja_env.globals["now"] = lambda: datetime.now(tz=timezone.utc)
    app.jinja_env.globals["member_label"] = _member_label
    return app


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
