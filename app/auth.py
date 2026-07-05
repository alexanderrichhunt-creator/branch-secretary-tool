import os

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from . import db
from .models import User


auth_bp = Blueprint("auth", __name__)

RESET_TOKEN_MAX_AGE = 3600


def _reset_serializer():
    from flask import current_app

    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="password-reset")


def _make_reset_token(user_id: int) -> str:
    return _reset_serializer().dumps({"user_id": user_id})


def _load_reset_token(token: str) -> int | None:
    try:
        data = _reset_serializer().loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    user_id = data.get("user_id") if isinstance(data, dict) else None
    return int(user_id) if user_id else None


def _password_reset_email_configured() -> bool:
    return bool(os.environ.get("MAIL_SERVER", "").strip())


def _send_password_reset_email(to_email: str, reset_url: str) -> bool:
    import smtplib
    from email.message import EmailMessage

    server = os.environ.get("MAIL_SERVER", "").strip()
    if not server:
        return False

    port = int(os.environ.get("MAIL_PORT", "587"))
    username = os.environ.get("MAIL_USERNAME", "").strip()
    password = os.environ.get("MAIL_PASSWORD", "").strip()
    from_addr = os.environ.get("MAIL_FROM", username).strip() or username
    use_tls = os.environ.get("MAIL_USE_TLS", "1").strip().lower() not in ("0", "false", "no")

    if not from_addr:
        return False

    msg = EmailMessage()
    msg["Subject"] = "Reset your Branch Secretary Tool password"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(
        "Use this link to reset your password. It expires in one hour.\n\n"
        f"{reset_url}\n"
    )

    try:
        with smtplib.SMTP(server, port, timeout=15) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)
        return True
    except Exception:
        return False


def _require_admin():
    if getattr(current_user, "role", None) != "admin":
        flash("Only admins can manage user accounts.", "danger")
        return False
    return True


@auth_bp.get("/login")
def login():
    return render_template("auth/login.html")


@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").lower().strip()
    password = request.form.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        flash("Incorrect email or password.", "danger")
        return redirect(url_for("auth.login"))

    login_user(user)
    return redirect(url_for("main.dashboard"))


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.get("/forgot-password")
def forgot_password():
    return render_template("auth/forgot_password.html")


@auth_bp.post("/forgot-password")
def forgot_password_post():
    email = (request.form.get("email") or "").lower().strip()
    if not email:
        flash("Enter your account email.", "warning")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.filter_by(email=email).first()
    if user:
        token = _make_reset_token(user.id)
        reset_url = url_for("auth.reset_password", token=token, _external=True)
        if _password_reset_email_configured():
            if _send_password_reset_email(user.email, reset_url):
                flash("If an account exists for that email, reset instructions were sent.", "success")
            else:
                flash(
                    "We could not send email right now. Ask an administrator to set a new password for you.",
                    "warning",
                )
        else:
            flash(
                "Email reset is not configured for this site. Ask an administrator to set a new password for you.",
                "info",
            )
    else:
        flash("If an account exists for that email, reset instructions were sent.", "success")

    return redirect(url_for("auth.login"))


@auth_bp.get("/reset-password/<token>")
def reset_password(token: str):
    if not _load_reset_token(token):
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))
    return render_template("auth/reset_password.html", token=token)


@auth_bp.post("/reset-password/<token>")
def reset_password_post(token: str):
    user_id = _load_reset_token(token)
    if not user_id:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    new_pw = request.form.get("new_password") or ""
    confirm = request.form.get("new_password_confirm") or ""

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "warning")
        return redirect(url_for("auth.reset_password", token=token))

    if new_pw != confirm:
        flash("New passwords do not match.", "warning")
        return redirect(url_for("auth.reset_password", token=token))

    user = User.query.get(user_id)
    if not user:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    flash("Password updated. You can sign in now.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.get("/create-user")
@login_required
def create_user():
    if not _require_admin():
        return redirect(url_for("main.dashboard"))
    return render_template("auth/create_user.html")


@auth_bp.post("/create-user")
@login_required
def create_user_post():
    if not _require_admin():
        return redirect(url_for("main.dashboard"))

    email = (request.form.get("email") or "").lower().strip()
    password = request.form.get("password") or ""

    if not email or not password:
        flash("Email and password are required.", "danger")
        return redirect(url_for("auth.create_user"))

    existing = User.query.filter_by(email=email).first()
    if existing:
        flash("That email already exists.", "warning")
        return redirect(url_for("auth.create_user"))

    user = User(email=email, password_hash=generate_password_hash(password), role="user")
    db.session.add(user)
    db.session.commit()
    flash("User created.", "success")
    return redirect(url_for("main.admin_users"))


@auth_bp.post("/admin/users/<int:user_id>/reset-password")
@login_required
def admin_reset_user_password(user_id: int):
    if not _require_admin():
        return redirect(url_for("main.dashboard"))

    user = User.query.get_or_404(user_id)
    new_pw = request.form.get("password") or ""

    if len(new_pw) < 8:
        flash("Password must be at least 8 characters.", "warning")
        return redirect(url_for("main.admin_users"))

    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    flash(f"Password updated for {user.email}.", "success")
    return redirect(url_for("main.admin_users"))


@auth_bp.post("/admin/users/<int:user_id>/delete")
@login_required
def admin_delete_user(user_id: int):
    if not _require_admin():
        return redirect(url_for("main.dashboard"))

    if user_id == current_user.id:
        flash("You cannot delete your own account while signed in.", "danger")
        return redirect(url_for("main.admin_users"))

    user = User.query.get_or_404(user_id)

    if user.role == "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            flash("You cannot delete the only admin account.", "danger")
            return redirect(url_for("main.admin_users"))

    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f"Deleted user {email}.", "success")
    return redirect(url_for("main.admin_users"))


@auth_bp.get("/change-password")
@login_required
def change_password():
    return render_template("auth/change_password.html")


@auth_bp.post("/change-password")
@login_required
def change_password_post():
    current_pw = request.form.get("current_password") or ""
    new_pw = request.form.get("new_password") or ""
    confirm = request.form.get("new_password_confirm") or ""

    user = User.query.get(current_user.id)
    if not user or not user.check_password(current_pw):
        flash("Current password is incorrect.", "danger")
        return redirect(url_for("auth.change_password"))

    if len(new_pw) < 8:
        flash("New password must be at least 8 characters.", "warning")
        return redirect(url_for("auth.change_password"))

    if new_pw != confirm:
        flash("New passwords do not match.", "warning")
        return redirect(url_for("auth.change_password"))

    user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    flash("Password updated.", "success")
    return redirect(url_for("main.dashboard"))
