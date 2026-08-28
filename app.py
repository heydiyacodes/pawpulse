"""
app.py — PawPulse Flask application
Phase 2: auth + roles, dispatch tracking, medical record OCR hooks.
"""

import os
import uuid
import math
import qrcode
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, flash, session, g
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, Dog, Feeder, MedicalRecord, EmergencyReport, FeedingLog, haversine_km

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Import role decorators AFTER app is created
from auth import login_required, ngo_required, verified_ngo_required, get_current_feeder


# ══════════════════════════════════════════════════════════════
#  CONTEXT PROCESSOR — injects current_feeder into every template
# ══════════════════════════════════════════════════════════════

@app.context_processor
def inject_user():
    return {"current_feeder": get_current_feeder()}


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def save_photo(file, subfolder="uploads"):
    """Save an uploaded image; return its /static/… URL or None."""
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(app.root_path, "static", subfolder)
    os.makedirs(folder, exist_ok=True)
    file.save(os.path.join(folder, filename))
    return f"/static/{subfolder}/{filename}"


def make_qr(dog_id):
    """Generate QR code PNG for a dog's public profile URL."""
    base = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    img = qrcode.make(f"{base}/dogs/{dog_id}")
    folder = os.path.join(app.root_path, "static", "qr")
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, f"dog_{dog_id}.png"))
    return f"/static/qr/dog_{dog_id}.png"


def find_nearest_ngos(lat, lng, limit=3):
    """
    Return up to `limit` NGO Feeder objects sorted by km distance
    from (lat, lng). Only returns NGOs that have a location set.
    No PostGIS needed — pure Python haversine.
    """
    ngos = Feeder.query.filter_by(is_ngo=True).all()
    candidates = []
    for ngo in ngos:
        if ngo.ngo_lat and ngo.ngo_lng:
            dist = haversine_km(lat, lng, ngo.ngo_lat, ngo.ngo_lng)
            candidates.append((dist, ngo))
        else:
            # NGOs without a set location still appear, distance unknown
            candidates.append((999, ngo))
    candidates.sort(key=lambda x: x[0])
    return candidates[:limit]


# ══════════════════════════════════════════════════════════════
#  AUTH — register / login / logout
# ══════════════════════════════════════════════════════════════

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        phone    = request.form.get("phone", "").strip()
        area     = request.form.get("area", "").strip()
        password = request.form.get("password", "")
        bio      = request.form.get("bio", "").strip()

        # The role radio sends value="ngo" or "feeder"; hidden checkbox is fallback
        role_select = request.form.get("role_select", "feeder")
        is_ngo = (role_select == "ngo") or (request.form.get("is_ngo") == "on")

        # --- Validation ---
        if not name or not email or not password:
            flash("Name, email and password are required.", "error")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")
        if Feeder.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        feeder = Feeder(
            name=name, email=email, phone=phone,
            area=area, bio=bio, is_ngo=is_ngo,
            is_verified=False,          # NGOs start unverified
            password_hash=generate_password_hash(password),
        )
        db.session.add(feeder)
        db.session.commit()
        session["feeder_id"] = feeder.id

        if is_ngo:
            flash(f"Welcome, {feeder.name}! Your NGO account is pending verification.", "success")
        else:
            flash(f"Welcome to PawPulse, {feeder.name}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        feeder   = Feeder.query.filter_by(email=email).first()

        if not feeder or not check_password_hash(feeder.password_hash, password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["feeder_id"] = feeder.id
        flash(f"Welcome back, {feeder.name}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "success")
    return redirect(url_for("index"))


# ── Profile update (name, phone, area, location) ──────────────

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    feeder = get_current_feeder()
    if request.method == "POST":
        feeder.name  = request.form.get("name", feeder.name).strip()
        feeder.phone = request.form.get("phone", feeder.phone or "").strip()
        feeder.area  = request.form.get("area",  feeder.area  or "").strip()
        feeder.bio   = request.form.get("bio",   feeder.bio   or "").strip()
        try:
            lat = float(request.form.get("ngo_lat") or 0) or None
            lng = float(request.form.get("ngo_lng") or 0) or None
            feeder.ngo_lat = lat
            feeder.ngo_lng = lng
        except ValueError:
            pass
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", feeder=feeder)


# ══════════════════════════════════════════════════════════════
#  ROUTE 1 — HOME
# ══════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template(
        "index.html",
        total_dogs        = Dog.query.count(),
        open_emergencies  = EmergencyReport.query.filter_by(status="open").count(),
        total_feeders     = Feeder.query.count(),
        recent_dogs       = Dog.query.order_by(Dog.created_at.desc()).limit(8).all(),
        recent_emergencies= EmergencyReport.query
                              .filter_by(status="open")
                              .order_by(EmergencyReport.created_at.desc())
                              .limit(3).all(),
    )


# ══════════════════════════════════════════════════════════════
#  ROUTE 2 — DOG REGISTRATION
# ══════════════════════════════════════════════════════════════

@app.route("/dogs/new", methods=["GET", "POST"])
@login_required
def register_dog():
    feeder = get_current_feeder()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Dog name is required.", "error")
            return render_template("register_dog.html")

        try:
            lat = float(request.form.get("latitude") or 17.3850)
            lng = float(request.form.get("longitude") or 78.4867)
        except ValueError:
            lat, lng = 17.3850, 78.4867

        dog = Dog(
            name          = name,
            breed         = request.form.get("breed", "Indie").strip(),
            color         = request.form.get("color", "").strip(),
            description   = request.form.get("description", "").strip(),
            latitude      = lat,
            longitude     = lng,
            area          = request.form.get("area", "").strip(),
            is_vaccinated = request.form.get("is_vaccinated") == "on",
            is_sterilised = request.form.get("is_sterilised") == "on",
            medical_notes = request.form.get("medical_notes", "").strip(),
            feeder_id     = feeder.id,
            photo_url     = save_photo(request.files.get("photo")),
        )
        db.session.add(dog)
        db.session.commit()
        dog.qr_code_url = make_qr(dog.id)
        db.session.commit()

        flash(f"🐾 {dog.name} is now on PawPulse!", "success")
        return redirect(url_for("dog_profile", dog_id=dog.id))

    return render_template("register_dog.html")


# ══════════════════════════════════════════════════════════════
#  ROUTE 3 — DOG PROFILE  (what the QR opens)
# ══════════════════════════════════════════════════════════════

@app.route("/dogs/<int:dog_id>")
def dog_profile(dog_id):
    dog        = Dog.query.get_or_404(dog_id)
    records    = (MedicalRecord.query
                  .filter_by(dog_id=dog_id)
                  .order_by(MedicalRecord.date.desc())
                  .all())
    emergencies = (EmergencyReport.query
                   .filter_by(dog_id=dog_id)
                   .order_by(EmergencyReport.created_at.desc())
                   .all())
    return render_template(
        "dog_profile.html",
        dog=dog, records=records, emergencies=emergencies,
        now=datetime.utcnow(),
    )


# ══════════════════════════════════════════════════════════════
#  ROUTE 4 — MAP
# ══════════════════════════════════════════════════════════════

@app.route("/map")
def map_view():
    return render_template(
        "map.html",
        dog_count  = Dog.query.count(),
        open_count = EmergencyReport.query.filter_by(status="open").count(),
    )


# ══════════════════════════════════════════════════════════════
#  ROUTE 5 — EMERGENCY REPORT
#  Auto-dispatch: after saving, finds nearest NGOs and
#  auto-assigns to the closest one that has a location set.
# ══════════════════════════════════════════════════════════════

@app.route("/emergency", methods=["GET", "POST"])
def report_emergency():
    dogs = Dog.query.order_by(Dog.name).all()
    if request.method == "POST":
        desc = request.form.get("description", "").strip()
        if not desc:
            flash("Please describe the emergency.", "error")
            return render_template("emergency.html", dogs=dogs)

        try:
            lat = float(request.form.get("latitude") or 0) or None
            lng = float(request.form.get("longitude") or 0) or None
        except ValueError:
            lat = lng = None

        report = EmergencyReport(
            description   = desc,
            location_text = request.form.get("location_text", "").strip(),
            latitude      = lat,
            longitude     = lng,
            dog_id        = request.form.get("dog_id") or None,
            reporter_name = request.form.get("reporter_name", "").strip(),
            reporter_phone= request.form.get("reporter_phone", "").strip(),
            photo_url     = save_photo(request.files.get("photo")),
            status        = "open",
        )
        db.session.add(report)
        db.session.commit()

        # ── Auto-dispatch to nearest NGO ──────────────────────
        if lat and lng:
            nearest = find_nearest_ngos(lat, lng, limit=1)
            if nearest:
                dist_km, ngo = nearest[0]
                if dist_km < 999:           # has a real location
                    report.status          = "assigned"
                    report.assigned_ngo_id = ngo.id
                    report.assigned_to     = ngo.name
                    report.assigned_at     = datetime.utcnow()
                    report.distance_km     = round(dist_km, 2)
                    ngo.cases_handled      = (ngo.cases_handled or 0) + 1
                    db.session.commit()
                    flash(
                        f"🚨 Emergency reported and assigned to {ngo.name} "
                        f"({dist_km:.1f} km away).",
                        "success",
                    )
                else:
                    flash("🚨 Emergency reported! We'll assign an NGO shortly.", "success")
            else:
                flash("🚨 Emergency reported! No NGOs with locations found — manual assignment needed.", "success")
        else:
            flash("🚨 Emergency reported! Add a location next time for faster dispatch.", "success")

        return redirect(url_for("dispatch_detail", report_id=report.id))

    return render_template("emergency.html", dogs=dogs)


# ══════════════════════════════════════════════════════════════
#  EMERGENCIES LIST
# ══════════════════════════════════════════════════════════════

@app.route("/emergencies")
def emergencies_list():
    status_filter = request.args.get("status", "all")
    q = EmergencyReport.query.order_by(EmergencyReport.created_at.desc())
    if status_filter != "all":
        q = q.filter_by(status=status_filter)
    return render_template(
        "emergencies.html",
        reports=q.all(),
        status_filter=status_filter,
    )


# ══════════════════════════════════════════════════════════════
#  DISPATCH DETAIL — full timeline for one emergency
# ══════════════════════════════════════════════════════════════

@app.route("/emergencies/<int:report_id>")
def dispatch_detail(report_id):
    report = EmergencyReport.query.get_or_404(report_id)
    # Build sorted list of nearby NGOs for re-assign dropdown
    nearby = []
    if report.latitude and report.longitude:
        nearby = find_nearest_ngos(report.latitude, report.longitude, limit=5)
    return render_template(
        "dispatch.html",
        report=report,
        nearby=nearby,
    )


# ── Status update (take / resolve) ────────────────────────────

@app.route("/emergencies/<int:report_id>/status", methods=["POST"])
@login_required
def update_emergency_status(report_id):
    report     = EmergencyReport.query.get_or_404(report_id)
    new_status = request.form.get("status")
    feeder     = get_current_feeder()

    if new_status == "assigned":
        report.status          = "assigned"
        report.assigned_ngo_id = feeder.id
        report.assigned_to     = feeder.name
        report.assigned_at     = datetime.utcnow()
        if report.latitude and report.longitude and feeder.ngo_lat and feeder.ngo_lng:
            report.distance_km = round(
                haversine_km(report.latitude, report.longitude,
                             feeder.ngo_lat, feeder.ngo_lng), 2
            )
        feeder.cases_handled = (feeder.cases_handled or 0) + 1

    elif new_status == "resolved":
        report.status              = "resolved"
        report.resolved_at         = datetime.utcnow()
        report.resolution_notes    = request.form.get("resolution_notes", "").strip()
        report.next_step           = request.form.get("next_step", "").strip()

    db.session.commit()
    flash(f"Case #{report_id} updated to {new_status}.", "success")

    # Stay on dispatch detail if we came from there
    next_url = request.form.get("next") or url_for("emergencies_list")
    return redirect(next_url)


# ══════════════════════════════════════════════════════════════
#  DASHBOARD — role-aware
# ══════════════════════════════════════════════════════════════

@app.route("/dashboard")
@login_required
def dashboard():
    feeder     = get_current_feeder()
    my_dogs    = Dog.query.filter_by(feeder_id=feeder.id).order_by(Dog.created_at.desc()).all()
    open_cases = (EmergencyReport.query
                  .filter_by(status="open")
                  .order_by(EmergencyReport.created_at.desc())
                  .limit(5).all())

    # Cases assigned to this NGO (feeder)
    my_cases = []
    if feeder.is_ngo:
        my_cases = (EmergencyReport.query
                    .filter_by(assigned_ngo_id=feeder.id)
                    .order_by(EmergencyReport.created_at.desc())
                    .limit(10).all())

    return render_template(
        "dashboard.html",
        feeder      = feeder,
        my_dogs     = my_dogs,
        open_cases  = open_cases,
        my_cases    = my_cases,
        all_dogs    = Dog.query.count(),
        all_open    = EmergencyReport.query.filter_by(status="open").count(),
    )


# ══════════════════════════════════════════════════════════════
#  MEDICAL RECORDS
# ══════════════════════════════════════════════════════════════

@app.route("/dogs/<int:dog_id>/records/add", methods=["POST"])
@login_required
def add_medical_record(dog_id):
    Dog.query.get_or_404(dog_id)
    receipt_url = save_photo(request.files.get("receipt"))
    claimed     = float(request.form.get("cost") or 0) or None

    record = MedicalRecord(
        dog_id       = dog_id,
        record_type  = request.form.get("record_type", "Checkup"),
        description  = request.form.get("description", "").strip(),
        vet_name     = request.form.get("vet_name", "").strip(),
        cost         = claimed,
        claimed_cost = claimed,
        receipt_url  = receipt_url,
        ocr_status   = None,     # OCR runs in Phase 2 session
        date         = datetime.strptime(
                           request.form.get("date") or str(datetime.utcnow().date()),
                           "%Y-%m-%d"
                       ).date(),
    )
    db.session.add(record)
    db.session.commit()
    flash("Medical record added.", "success")
    return redirect(url_for("dog_profile", dog_id=dog_id))


# ══════════════════════════════════════════════════════════════
#  PROFILE PAGE
# ══════════════════════════════════════════════════════════════

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    feeder = get_current_feeder()
    if request.method == "POST":
        feeder.name  = request.form.get("name", "").strip() or feeder.name
        feeder.phone = request.form.get("phone", "").strip()
        feeder.area  = request.form.get("area", "").strip()
        feeder.bio   = request.form.get("bio", "").strip()
        try:
            feeder.ngo_lat = float(request.form.get("ngo_lat") or 0) or None
            feeder.ngo_lng = float(request.form.get("ngo_lng") or 0) or None
        except ValueError:
            pass
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard"))
    return render_template("profile.html", feeder=feeder)


# ══════════════════════════════════════════════════════════════
#  JSON APIs — consumed by Leaflet
# ══════════════════════════════════════════════════════════════

@app.route("/api/dogs")
def api_dogs():
    return jsonify([d.to_dict() for d in Dog.query.all()])


@app.route("/api/emergencies")
def api_emergencies():
    reports = (EmergencyReport.query
               .filter(EmergencyReport.latitude.isnot(None))
               .filter_by(status="open")
               .all())
    return jsonify([r.to_dict() for r in reports])


@app.route("/api/stats")
def api_stats():
    return jsonify({
        "dogs":     Dog.query.count(),
        "open":     EmergencyReport.query.filter_by(status="open").count(),
        "resolved": EmergencyReport.query.filter_by(status="resolved").count(),
        "feeders":  Feeder.query.count(),
    })


# ── Role check API (for frontend UI hints) ────────────────────

@app.route("/api/me")
def api_me():
    f = get_current_feeder()
    if not f:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in":   True,
        "id":          f.id,
        "name":        f.name,
        "is_ngo":      f.is_ngo,
        "is_verified": f.is_verified,
        "role":        f.role_label,
    })


# ══════════════════════════════════════════════════════════════
#  PHASE 2 — FEEDING LOG ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/dogs/<int:dog_id>/feed", methods=["POST"])
@login_required
def feed_dog(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    feeder = get_current_feeder()
    notes = request.form.get("notes", "").strip() or None

    log = FeedingLog(
        dog_id=dog.id,
        feeder_id=feeder.id,
        fed_at=datetime.utcnow(),
        notes=notes
    )
    db.session.add(log)
    db.session.commit()

    flash(f"Logged feeding for {dog.name}!", "success")
    return redirect(url_for("dog_profile", dog_id=dog.id))


@app.route("/api/dogs/<int:dog_id>/feeding-logs")
def api_feeding_logs(dog_id):
    Dog.query.get_or_404(dog_id)
    logs = (FeedingLog.query
            .filter_by(dog_id=dog_id)
            .order_by(FeedingLog.fed_at.desc())
            .limit(10)
            .all())
    return jsonify([{
        "id":          l.id,
        "dog_id":      l.dog_id,
        "feeder_id":   l.feeder_id,
        "feeder_name": l.feeder.name if l.feeder else "Unknown",
        "fed_at":      l.fed_at.strftime("%Y-%m-%d %H:%M:%S"),
        "notes":       l.notes or ""
    } for l in logs])


# ══════════════════════════════════════════════════════════════
#  BOOTSTRAP DB ON STARTUP
# ══════════════════════════════════════════════════════════════

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
