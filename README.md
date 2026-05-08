# 🐾 PawPulse

> A geospatial, QR-based rescue and donation platform that gives every stray dog a digital identity — connecting feeders, NGOs, donors, and citizens across Hyderabad.

![Python](https://img.shields.io/badge/Python-3.10+-b08050?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-b08050?style=flat-square&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-b08050?style=flat-square&logo=sqlite&logoColor=white)
![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9-b08050?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-b08050?style=flat-square)

---

## The problem

Stray dog welfare in India is fragmented. There are no shared records of dogs, no transparency in donations, no fast way to report injured animals, and no coordination between the people who care. Feeders work in isolation. NGOs don't know what's already been done. Donors have no way to verify their money reached the right place.

PawPulse solves all of this in one platform.

---

## What it does

### 🪪 QR-based dog identity
Every registered stray dog gets a permanent digital profile with a generated QR code. Anyone who scans it — a vet, a new feeder, a donor — instantly sees the dog's photo, vaccination history, medical records, assigned feeder, and active emergencies. No app needed to scan.

### 🗺️ Real-time geospatial map
A full-screen live map built with Leaflet.js shows every registered dog and open emergency pinned to their exact location. Filters by dogs, emergencies, or both. Auto-refreshes every 30 seconds. Clicking any pin opens a popup with profile link or case details.

### 🚨 Emergency reporting and auto-dispatch
Any citizen can report an injured dog with a photo, GPS pin, and description — no account needed. The moment a report is submitted, the system calculates the haversine distance between the incident and every registered NGO, auto-assigns the nearest one, logs the assignment time and distance, and redirects to a dispatch detail page.

### 📋 Full dispatch timeline
Every emergency has a dedicated page showing the complete lifecycle — time reported, time assigned, responder name, clickable phone and email pulled from their profile, distance from incident, resolution notes, and next-step instructions. NGOs can take cases, reassign to closer responders, and mark resolved with notes.

### 🏥 Medical record tracking
Feeders and NGOs can add vet records to any dog's profile — vaccination, surgery, checkup, medication — with date, vet name, cost, and receipt upload. All records appear in a chronological timeline on the dog's public profile.

### 👤 Role-based access
Three access levels enforced with Python decorators: anonymous citizens can report emergencies, registered feeders can manage dogs and records, NGOs get full dispatch access and a dedicated dashboard with their assigned cases and response metrics.

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Flask + Flask-SQLAlchemy | Lightweight, Python-native, fast to iterate |
| Database | SQLite (dev) / PostgreSQL (prod) | Zero setup locally, Postgres-ready for deploy |
| Auth | Werkzeug password hashing + Flask session | Secure, no external dependencies |
| Maps | Leaflet.js + CartoDB Voyager tiles | Open source, warm tile style, no API key needed |
| QR codes | `qrcode` + Pillow | Two lines of Python, no service dependency |
| Distance | Haversine formula (pure Python) | No PostGIS needed, mathematically precise |
| Frontend | Jinja2 + vanilla JS | No frontend build step, ships fast |
| Fonts | Playfair Display + Nunito (Google Fonts) | Editorial warmth, high readability |
| Deployment | Render.com (free tier) | Push-to-deploy from GitHub |

---

## Project structure

```
pawpulse/
│
├── app.py              # All routes, auth logic, dispatch, API endpoints
├── models.py           # SQLAlchemy models: Feeder, Dog, MedicalRecord, EmergencyReport
├── auth.py             # Role decorators: @login_required, @ngo_required
├── config.py           # App config, upload limits, secret key
├── seed.py             # Populates DB with 20 Hyderabad dogs + demo accounts
├── migrate.py          # Safe column migrations for existing databases
├── requirements.txt    # All Python dependencies
├── .env                # Secret key (never committed)
├── .gitignore
│
├── templates/
│   ├── base.html           # Nav, flash messages, paw watermark layout
│   ├── index.html          # Homepage with live stats + dog grid
│   ├── map.html            # Full-screen Leaflet map with floating panels
│   ├── login.html          # Auth
│   ├── register.html       # Role selector (feeder vs NGO)
│   ├── dashboard.html      # Role-aware dashboard with KPIs
│   ├── profile.html        # Edit profile + NGO location picker
│   ├── register_dog.html   # Dog registration with click-to-pin map
│   ├── dog_profile.html    # Public profile — QR, medical timeline, emergencies
│   ├── emergency.html      # Emergency report form with GPS
│   ├── emergencies.html    # Filterable case list
│   └── dispatch.html       # Full dispatch timeline for one emergency
│
└── static/
    ├── css/style.css        # Complete design system (warm earthy palette)
    ├── qr/                  # Auto-generated QR PNGs per dog
    └── uploads/             # Feeder-uploaded photos
```

---

## Getting started

### Prerequisites
- Python 3.10 or higher
- pip
- Git

### 1. Clone the repo

```bash
git clone https://github.com/heydiyacodes/pawpulse.git
cd pawpulse
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Create a `.env` file in the root:

```
SECRET_KEY=your-random-secret-key-here
FLASK_APP=app.py
FLASK_DEBUG=1
```

Generate a secure key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Run the database migration

Only needed if you have an existing `pawpulse.db` from a previous version:

```bash
python migrate.py
```

### 6. Seed demo data

```bash
python seed.py
```

This creates 20 stray dogs across Hyderabad, 4 user accounts, and 3 emergency reports.

Demo accounts (password for all: `pawpulse123`):

| Email | Role |
|---|---|
| `anjali@pawpulse.in` | Feeder |
| `suresh@pawpulse.in` | Feeder |
| `priya@pawpulse.in` | Feeder |
| `ngo@pawpulse.in` | NGO (verified) |

### 7. Run the app

```bash
flask run
```

Open `http://localhost:5000`

---

## Key workflows

### Registering a dog
1. Log in as a feeder or NGO
2. Click **+ Register Dog** in the nav
3. Fill in the dog's name, breed, area, health status
4. Upload a photo
5. Click the map to pin the dog's usual location
6. Submit — a QR code is generated automatically
7. Share or print the QR; scanning it opens the dog's public profile on any phone

### Reporting an emergency
1. Click **🚨 SOS** — no login required
2. Describe what you see
3. Drop a GPS pin or use your location
4. Submit — the system finds the nearest NGO and auto-assigns the case
5. You're redirected to the dispatch page with the responder's contact details

### Handling a case as an NGO
1. Log in as `ngo@pawpulse.in`
2. Dashboard shows your assigned cases with timing and distance
3. Open any case → see full dispatch timeline
4. Take open cases, reassign to closer NGOs, or mark resolved with notes and next steps

### Adding a medical record
1. Open any dog's profile
2. Click **+ Medical Record** (feeders and NGOs only)
3. Select type (vaccination / checkup / surgery / medication)
4. Add date, vet name, cost, and upload a receipt
5. Record appears in the dog's medical timeline immediately

---

## API endpoints

| Method | Endpoint | Auth | Returns |
|---|---|---|---|
| GET | `/api/dogs` | None | All dogs as GeoJSON for Leaflet |
| GET | `/api/emergencies` | None | Open emergencies with coordinates |
| GET | `/api/stats` | None | Live counts: dogs, open, resolved, feeders |
| GET | `/api/me` | Session | Current user's role and verification status |

---

## Role system

```
Anonymous citizen
  └── Can: report emergencies, view map, scan QR codes

Feeder (registered account)
  └── Can: everything above + register dogs, add medical records

NGO (is_ngo=True)
  └── Can: everything above + dispatch cases, reassign, resolve with notes
      └── Verified NGO (is_verified=True): full trust score, appears in auto-dispatch
```

Enforced in Python with decorators in `auth.py`:

```python
@app.route("/dogs/new")
@login_required          # any logged-in user
def register_dog(): ...

@app.route("/dispatch/assign")
@ngo_required            # NGO accounts only
def assign_case(): ...
```

---

## Dispatch algorithm

When an emergency is submitted with a GPS location, PawPulse ranks all registered NGOs by real-world distance using the **Haversine formula** — the same math used to calculate great-circle distance on a sphere:

```python
def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

The nearest NGO with a location set is auto-assigned. The distance in km, assignment timestamp, and responder contact details are all stored on the `EmergencyReport` record and displayed on the dispatch timeline.

---

## Deployment (Render.com)

1. Push your code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Set the following:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
5. Add environment variables in the Render dashboard:
   - `SECRET_KEY` → your generated key
   - `FLASK_DEBUG` → `0`
6. Deploy

Add `gunicorn` to `requirements.txt` before deploying:
```
gunicorn
```

---

## Roadmap

- [x] QR-based dog identity system
- [x] Real-time geospatial map
- [x] Role-based auth (citizen / feeder / NGO)
- [x] Emergency reporting with GPS
- [x] Auto-dispatch to nearest NGO (haversine)
- [x] Full dispatch timeline with responder contacts
- [x] Medical record tracking
- [ ] OCR receipt validation (Google Vision API)
- [ ] Donation system with per-dog tracking
- [ ] NGO admin verification panel
- [ ] Push notifications for new cases
- [ ] Mobile app (React Native)
- [ ] Multi-city support beyond Hyderabad

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "add your feature"`
4. Push: `git push origin feature/your-feature`
5. Open a pull request

---

## License

MIT — do whatever you want with it, just don't sell it without giving back.

---

<div align="center">
  <p>🐾 Built for Hyderabad's street dogs.</p>
  <p>Every stray deserves an identity.</p>
</div>
