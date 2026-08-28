"""
models.py — PawPulse database models
Every table in pawpulse.db is defined here as a Python class.
Flask-SQLAlchemy translates these classes into SQL automatically.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import math

db = SQLAlchemy()


# ──────────────────────────────────────────────────────────────
#  FEEDER — individual feeder OR NGO (is_ngo=True)
#
#  Roles:
#    citizen  → no account, can only report emergencies
#    feeder   → account, is_ngo=False, can register dogs
#    ngo      → account, is_ngo=True,  full dispatch access
# ──────────────────────────────────────────────────────────────
class Feeder(db.Model):
    __tablename__ = "feeder"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    phone         = db.Column(db.String(20))
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    area          = db.Column(db.String(100))
    bio           = db.Column(db.Text)               # short NGO description

    # Role flags
    is_ngo        = db.Column(db.Boolean, default=False)
    is_verified   = db.Column(db.Boolean, default=False)  # admin marks NGO as verified

    # Location — used for dispatch distance calculation
    ngo_lat       = db.Column(db.Float)
    ngo_lng       = db.Column(db.Float)

    # Stats (denormalised for fast dashboard reads)
    cases_handled = db.Column(db.Integer, default=0)

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    dogs               = db.relationship("Dog", backref="feeder", lazy=True)
    assigned_cases     = db.relationship("EmergencyReport",
                                         foreign_keys="EmergencyReport.assigned_ngo_id",
                                         backref="assigned_ngo", lazy=True)

    @property
    def role_label(self):
        if self.is_ngo:
            return "NGO" if self.is_verified else "NGO (pending)"
        return "Feeder"

    def __repr__(self):
        return f"<Feeder id={self.id} name={self.name!r} ngo={self.is_ngo}>"


# ──────────────────────────────────────────────────────────────
#  DOG — the core record
# ──────────────────────────────────────────────────────────────
class Dog(db.Model):
    __tablename__ = "dog"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    breed       = db.Column(db.String(100), default="Indie")
    color       = db.Column(db.String(100))
    description = db.Column(db.Text)

    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    area        = db.Column(db.String(100))

    photo_url   = db.Column(db.String(300))
    qr_code_url = db.Column(db.String(300))

    is_vaccinated = db.Column(db.Boolean, default=False)
    is_sterilised = db.Column(db.Boolean, default=False)
    medical_notes = db.Column(db.Text)

    feeder_id  = db.Column(db.Integer, db.ForeignKey("feeder.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    medical_records = db.relationship("MedicalRecord", backref="dog", lazy=True,
                                      cascade="all, delete-orphan")
    emergencies     = db.relationship("EmergencyReport",
                                      foreign_keys="EmergencyReport.dog_id",
                                      backref="dog", lazy=True)

    def __repr__(self):
        return f"<Dog id={self.id} name={self.name!r}>"

    def to_dict(self):
        return {
            "id":            self.id,
            "name":          self.name,
            "breed":         self.breed,
            "area":          self.area or "",
            "latitude":      self.latitude,
            "longitude":     self.longitude,
            "is_vaccinated": self.is_vaccinated,
            "photo_url":     self.photo_url or "",
            "profile_url":   f"/dogs/{self.id}",
        }


# ──────────────────────────────────────────────────────────────
#  MEDICAL RECORD
# ──────────────────────────────────────────────────────────────
class MedicalRecord(db.Model):
    __tablename__ = "medical_record"

    id          = db.Column(db.Integer, primary_key=True)
    dog_id      = db.Column(db.Integer, db.ForeignKey("dog.id"), nullable=False)
    record_type = db.Column(db.String(50))
    description = db.Column(db.Text, nullable=False)
    vet_name    = db.Column(db.String(100))

    # Cost + OCR verification — Phase 2
    cost              = db.Column(db.Float)
    claimed_cost      = db.Column(db.Float)      # what feeder entered manually
    ocr_amount        = db.Column(db.Float)      # what OCR extracted from receipt
    ocr_status        = db.Column(db.String(20)) # "verified" | "mismatch" | "unreadable" | None
    ocr_raw_text      = db.Column(db.Text)       # raw OCR output for debugging

    receipt_url       = db.Column(db.String(300))
    date              = db.Column(db.Date, default=datetime.utcnow)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<MedicalRecord id={self.id} dog_id={self.dog_id}>"


# ──────────────────────────────────────────────────────────────
#  EMERGENCY REPORT
#  Full dispatch lifecycle: open → assigned → resolved
# ──────────────────────────────────────────────────────────────
class EmergencyReport(db.Model):
    __tablename__ = "emergency_report"

    id             = db.Column(db.Integer, primary_key=True)
    description    = db.Column(db.Text, nullable=False)
    photo_url      = db.Column(db.String(300))

    # Where
    latitude       = db.Column(db.Float)
    longitude      = db.Column(db.Float)
    location_text  = db.Column(db.String(200))

    # Which dog (optional)
    dog_id         = db.Column(db.Integer, db.ForeignKey("dog.id"), nullable=True)

    # Who reported
    reporter_name  = db.Column(db.String(100))
    reporter_phone = db.Column(db.String(20))

    # ── Dispatch tracking ───────────────────────────────────
    status          = db.Column(db.String(20), default="open")
    # Legacy text field kept for backward compat
    assigned_to     = db.Column(db.String(100))
    # FK to the NGO/feeder who is handling it
    assigned_ngo_id = db.Column(db.Integer, db.ForeignKey("feeder.id"), nullable=True)
    assigned_at     = db.Column(db.DateTime)      # when was it assigned
    distance_km     = db.Column(db.Float)         # km from NGO to incident at assignment

    # Resolution
    resolved_at        = db.Column(db.DateTime)
    resolution_notes   = db.Column(db.Text)       # what was done
    next_step          = db.Column(db.String(200)) # e.g. "Follow-up vet visit on 15 June"

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmergencyReport id={self.id} status={self.status!r}>"

    def to_dict(self):
        return {
            "id":            self.id,
            "description":   self.description,
            "location_text": self.location_text or "",
            "latitude":      self.latitude,
            "longitude":     self.longitude,
            "status":        self.status,
            "created_at":    self.created_at.strftime("%d %b %Y"),
        }

    @property
    def time_open_minutes(self):
        """Minutes since report was filed."""
        delta = datetime.utcnow() - self.created_at
        return int(delta.total_seconds() / 60)

    @property
    def time_to_assign_minutes(self):
        """Minutes between report and assignment. None if not yet assigned."""
        if not self.assigned_at:
            return None
        delta = self.assigned_at - self.created_at
        return int(delta.total_seconds() / 60)

    @property
    def time_to_resolve_minutes(self):
        """Minutes between assignment and resolution. None if not resolved."""
        if not self.assigned_at or not self.resolved_at:
            return None
        delta = self.resolved_at - self.assigned_at
        return int(delta.total_seconds() / 60)


# ──────────────────────────────────────────────────────────────
#  HAVERSINE — geodistance helper (no PostGIS needed)
# ──────────────────────────────────────────────────────────────
def haversine_km(lat1, lng1, lat2, lng2):
    """Return great-circle distance in km between two lat/lng points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ──────────────────────────────────────────────────────────────
#  FEEDING LOG — Phase 2
# ──────────────────────────────────────────────────────────────
class FeedingLog(db.Model):
    __tablename__ = "feeding_log"

    id        = db.Column(db.Integer, primary_key=True)
    dog_id    = db.Column(db.Integer, db.ForeignKey("dog.id"), nullable=False)
    feeder_id = db.Column(db.Integer, db.ForeignKey("feeder.id"), nullable=False)
    fed_at    = db.Column(db.DateTime, default=datetime.utcnow)
    notes     = db.Column(db.Text)

    dog    = db.relationship("Dog", backref=db.backref("feeding_logs", order_by="desc(FeedingLog.fed_at)", lazy=True))
    feeder = db.relationship("Feeder", backref=db.backref("feeding_logs", lazy=True))

    def __repr__(self):
        return f"<FeedingLog id={self.id} dog_id={self.dog_id} feeder_id={self.feeder_id}>"

