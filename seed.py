"""
seed.py — Populate PawPulse with realistic demo data.
Run once after migrate.py:
    python seed.py
"""
from werkzeug.security import generate_password_hash
from app import app, make_qr
from models import db, Dog, Feeder, EmergencyReport

# ── Feeders + NGOs ────────────────────────────────────────────
# Each entry now has email + password so models.py NOT NULL is satisfied.
# Login with any of these after seeding.
FEEDERS = [
    {
        "name":          "Anjali Reddy",
        "email":         "anjali@pawpulse.in",
        "phone":         "9876543210",
        "area":          "Banjara Hills",
        "is_ngo":        False,
        "is_verified":   False,
        "ngo_lat":       None,
        "ngo_lng":       None,
        "cases_handled": 0,
    },
    {
        "name":          "Suresh Kumar",
        "email":         "suresh@pawpulse.in",
        "phone":         "9845123456",
        "area":          "Madhapur",
        "is_ngo":        False,
        "is_verified":   False,
        "ngo_lat":       None,
        "ngo_lng":       None,
        "cases_handled": 0,
    },
    {
        "name":          "Priya Sharma",
        "email":         "priya@pawpulse.in",
        "phone":         "9765432198",
        "area":          "Kondapur",
        "is_ngo":        False,
        "is_verified":   False,
        "ngo_lat":       None,
        "ngo_lng":       None,
        "cases_handled": 0,
    },
    {
        # NGO account — use this to test dispatch + NGO dashboard
        "name":          "Animal Aid Hyderabad",
        "email":         "ngo@pawpulse.in",
        "phone":         "9988776655",
        "area":          "Gachibowli",
        "is_ngo":        True,
        "is_verified":   True,
        "ngo_lat":       17.3850,   # Gachibowli coords — enables auto-dispatch
        "ngo_lng":       78.3867,
        "cases_handled": 5,
    },
]

# All seed accounts use the same password for easy testing
SEED_PASSWORD = "pawpulse123"

# ── Dogs ──────────────────────────────────────────────────────
# (name, breed, color, lat, lng, area, vaccinated, sterilised, notes)
DOGS = [
    ("charlie",   "Indie",        "Brown",        17.4156, 78.4347, "Banjara Hills",  True,  True,  "Friendly, sterilised"),
    ("Moti",    "Indie",        "White",        17.4500, 78.3800, "Jubilee Hills",  True,  False, "Limps slightly, monitored"),
    ("Kalu",    "Indie",        "Black",        17.4123, 78.4678, "Madhapur",       False, False, "Very shy, leave food and step back"),
    ("Rani",    "Indie mix",    "Brown-white",  17.4402, 78.3947, "Kondapur",       True,  False, "Nursing pups nearby"),
    ("Tiger",   "Indie",        "Tan",          17.3850, 78.4867, "Gachibowli",     True,  True,  "Playful, knows sit command"),
    ("Bholi",   "Labrador mix", "Yellow",       17.4900, 78.3600, "Begumpet",       True,  True,  "Very gentle, good with kids"),
    ("Rocky",   "Indie",        "Grey",         17.3600, 78.4750, "Tolichowki",     False, False, "Needs rabies booster"),
    ("Simba",   "Indie",        "Brown",        17.4300, 78.4800, "HITEC City",     True,  True,  "Guard dog for the park"),
    ("vanilla",   "Indie",        "Black-white",  17.4050, 78.4600, "Kukatpally",     False, False, "Pregnant, due soon"),
    ("Charlie", "Indie mix",    "Tan",          17.4700, 78.4200, "Secunderabad",   True,  True,  "Old dog, about 10 yrs"),
    ("Pinki",   "Spitz mix",    "White",        17.4250, 78.4550, "Ameerpet",       True,  True,  "Lost eye in accident, adapted well"),
    ("Coffee",    "Indie",        "Brown",      17.3950, 78.4700, "Nanakramguda",   True,  False, "Loves mango season"),
    ("Sheru",   "Indie",        "Brown-black",  17.4600, 78.4900, "Malkajgiri",     False, False, "Aggressive around food"),
    ("Golu",    "Indie",        "White",        17.4150, 78.4200, "Film Nagar",     True,  True,  "Comes to same spot every 6pm"),
    ("Roja",    "Indie mix",    "Red-brown",    17.3750, 78.5100, "LB Nagar",       True,  True,  "Recovered from mange"),
    ("Hero",    "Indie",        "Black",        17.4800, 78.5000, "Uppal",          False, False, "Injured back paw, healing"),
    ("Junior",   "Indie",        "Brown",        17.4000, 78.3900, "Manikonda",      True,  True,  "Feeds from Patel family daily"),
    ("bruno",    "Indie",        "Cream",        17.4350, 78.4700, "Madhapur",       True,  True,  "Follows school kids every morning"),
    ("Tuffie",   "Indie mix",    "Grey-white",   17.4550, 78.4400, "Borabanda",      False, False, "Needs deworming"),
    ("Bunty",   "Indie",        "Tan",          17.3700, 78.4900, "Attapur",        True,  True,  "Local favourite at chai stall"),
]

# ── Emergencies ───────────────────────────────────────────────
EMERGENCIES = [
    {
        "description":   "Dog hit by bike near signal, limping badly on back leg",
        "location_text": "Madhapur main road near Dominos",
        "latitude":      17.4502,
        "longitude":     78.3912,
        "reporter_name": "Ravi Teja",
        "reporter_phone":"9811122233",
        "status":        "open",
    },
    {
        "description":   "Stray with large wound on neck, needs urgent vet attention",
        "location_text": "Kondapur petrol bunk opposite",
        "latitude":      17.4430,
        "longitude":     78.3860,
        "reporter_name": "Sita Devi",
        "reporter_phone":"9822233344",
        "status":        "assigned",
    },
    {
        "description":   "Dog trapped in drain near park, unable to get out",
        "location_text": "Gachibowli stadium road",
        "latitude":      17.3880,
        "longitude":     78.3910,
        "reporter_name": "Anonymous",
        "reporter_phone":"",
        "status":        "resolved",
    },
]


def seed():
    with app.app_context():
        # ── Wipe existing data cleanly ────────────────────────
        from models import FeedingLog, MedicalRecord
        FeedingLog.query.delete()
        MedicalRecord.query.delete()
        EmergencyReport.query.delete()
        Dog.query.delete()
        Feeder.query.delete()
        db.session.commit()

        # ── Create feeders ────────────────────────────────────
        pw_hash = generate_password_hash(SEED_PASSWORD)
        feeder_objects = []
        for f in FEEDERS:
            feeder = Feeder(
                name          = f["name"],
                email         = f["email"],
                phone         = f["phone"],
                area          = f["area"],
                is_ngo        = f["is_ngo"],
                is_verified   = f["is_verified"],
                ngo_lat       = f["ngo_lat"],
                ngo_lng       = f["ngo_lng"],
                cases_handled = f["cases_handled"],
                password_hash = pw_hash,
            )
            db.session.add(feeder)
            feeder_objects.append(feeder)
        db.session.commit()

        # ── Create dogs ───────────────────────────────────────
        for i, (name, breed, color, lat, lng, area, vacc, steril, notes) in enumerate(DOGS):
            feeder = feeder_objects[i % len(feeder_objects)]
            dog = Dog(
                name          = name,
                breed         = breed,
                color         = color,
                latitude      = lat,
                longitude     = lng,
                area          = area,
                is_vaccinated = vacc,
                is_sterilised = steril,
                medical_notes = notes,
                feeder_id     = feeder.id,
            )
            db.session.add(dog)
        db.session.commit()

        # ── Generate QR codes ─────────────────────────────────
        for dog in Dog.query.all():
            dog.qr_code_url = make_qr(dog.id)
        db.session.commit()

        # ── Create emergencies ────────────────────────────────
        ngo    = feeder_objects[-1]   # Animal Aid NGO
        dogs   = Dog.query.all()

        for i, e in enumerate(EMERGENCIES):
            report = EmergencyReport(
                dog_id          = dogs[i].id if i < len(dogs) else None,
                description     = e["description"],
                location_text   = e["location_text"],
                latitude        = e["latitude"],
                longitude       = e["longitude"],
                reporter_name   = e["reporter_name"],
                reporter_phone  = e["reporter_phone"],
                status          = e["status"],
            )
            # Assign the second case to the NGO so the dispatch page is demo-ready
            if e["status"] == "assigned":
                from datetime import datetime
                report.assigned_ngo_id = ngo.id
                report.assigned_to     = ngo.name
                report.assigned_at     = datetime.utcnow()
                report.distance_km     = 1.4
            if e["status"] == "resolved":
                from datetime import datetime
                report.assigned_ngo_id   = ngo.id
                report.assigned_to       = ngo.name
                report.assigned_at       = datetime.utcnow()
                report.resolved_at       = datetime.utcnow()
                report.resolution_notes  = "Dog rescued and taken to CUPA clinic. Leg treated."
                report.next_step         = "Follow-up vet visit in 7 days"
            db.session.add(report)

        db.session.commit()

        # ── Summary ───────────────────────────────────────────
        print(f"\n✓ Seeded {Dog.query.count()} dogs")
        print(f"✓ Seeded {Feeder.query.count()} feeders/NGOs")
        print(f"✓ Seeded {EmergencyReport.query.count()} emergency reports")
        print(f"\nDemo login credentials (password for all: '{SEED_PASSWORD}'):")
        for f in Feeder.query.all():
            role = "NGO ✓" if f.is_ngo else "Feeder"
            print(f"  {f.email:<30} [{role}]")
        print("\nRun: flask run")


if __name__ == "__main__":
    seed()