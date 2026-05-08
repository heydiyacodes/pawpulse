"""
migrate.py — Safe database migration for PawPulse Phase 2.

Run ONCE on your existing database before starting the app:
    python migrate.py

This script only ADDS new columns. It never deletes or modifies
existing data. Safe to run multiple times — skips columns that
already exist.
"""

from app import app
from models import db


def col_exists(cur, table, col):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())


MIGRATIONS = [
    # (table, column_name, sqlite_type)

    # Feeder — new role + dispatch fields
    ("feeder", "is_verified",   "BOOLEAN DEFAULT 0"),
    ("feeder", "ngo_lat",       "REAL"),
    ("feeder", "ngo_lng",       "REAL"),
    ("feeder", "cases_handled", "INTEGER DEFAULT 0"),
    ("feeder", "bio",           "TEXT"),

    # EmergencyReport — full dispatch lifecycle
    ("emergency_report", "assigned_ngo_id",  "INTEGER"),
    ("emergency_report", "assigned_at",       "DATETIME"),
    ("emergency_report", "distance_km",       "REAL"),
    ("emergency_report", "resolution_notes",  "TEXT"),
    ("emergency_report", "next_step",         "VARCHAR(200)"),

    # MedicalRecord — OCR fields (used in Phase 2 OCR session)
    ("medical_record", "claimed_cost",  "REAL"),
    ("medical_record", "ocr_amount",    "REAL"),
    ("medical_record", "ocr_status",    "VARCHAR(20)"),
    ("medical_record", "ocr_raw_text",  "TEXT"),
]


def run():
    with app.app_context():
        conn = db.engine.raw_connection()
        cur  = conn.cursor()
        added, skipped = [], []

        for table, col, coltype in MIGRATIONS:
            if col_exists(cur, table, col):
                skipped.append(f"{table}.{col}")
            else:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
                added.append(f"{table}.{col}")

        conn.commit()
        conn.close()

        if added:
            print(f"✓ Added {len(added)} column(s):")
            for c in added:
                print(f"    + {c}")
        if skipped:
            print(f"  Skipped {len(skipped)} already-existing column(s).")

        print("\nMigration complete. You can now run: flask run")


if __name__ == "__main__":
    run()
