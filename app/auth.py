from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash

from . import db
from .models import User


auth_bp = Blueprint("auth", __name__)


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


@auth_bp.get("/create-user")
@login_required
def create_user():
    from flask_login import current_user

    if current_user.role != "admin":
        flash("Only admins can create new users.", "danger")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/create_user.html")


@auth_bp.post("/create-user")
@login_required
def create_user_post():
    from flask_login import current_user

    if current_user.role != "admin":
        flash("Only admins can create new users.", "danger")
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
    return redirect(url_for("main.dashboard"))


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
