"""
auth.py — Role decorators and session helpers for PawPulse.

Import into app.py with:
    from auth import login_required, ngo_required, get_current_feeder

Usage:
    @app.route("/dogs/new")
    @login_required
    def register_dog(): ...

    @app.route("/dispatch/<id>/assign")
    @ngo_required
    def assign_case(id): ...
"""

from functools import wraps
from flask import session, redirect, url_for, flash, g
from models import Feeder


# ── Session helpers ────────────────────────────────────────────

def get_current_feeder():
    """
    Return the logged-in Feeder object or None.
    Cached on Flask's g object so we only hit the DB once per request.
    """
    if "_feeder" not in g:
        fid = session.get("feeder_id")
        g._feeder = Feeder.query.get(fid) if fid else None
    return g._feeder


# ── Decorators ────────────────────────────────────────────────

def login_required(fn):
    """
    Redirect anonymous users to /login.
    Any logged-in feeder or NGO can pass.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not get_current_feeder():
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def ngo_required(fn):
    """
    Only verified NGO accounts can access this route.
    Feeders see a 'permission denied' flash and are redirected to dashboard.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        feeder = get_current_feeder()
        if not feeder:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        if not feeder.is_ngo:
            flash("This action requires an NGO account.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper


def verified_ngo_required(fn):
    """
    Only NGOs that have been verified by admin can access.
    Unverified NGOs see a pending message.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        feeder = get_current_feeder()
        if not feeder:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        if not feeder.is_ngo:
            flash("This action requires an NGO account.", "error")
            return redirect(url_for("dashboard"))
        if not feeder.is_verified:
            flash("Your NGO account is pending verification. We'll notify you once approved.", "error")
            return redirect(url_for("dashboard"))
        return fn(*args, **kwargs)
    return wrapper
