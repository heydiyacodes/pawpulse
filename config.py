import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    
    # Read DATABASE_URL from environment (Render sets this)
    # Fall back to SQLite for local development
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        # Render gives postgres://, SQLAlchemy 2.0+ needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Local development uses SQLite
        SQLALCHEMY_DATABASE_URI = "sqlite:///pawpulse.db"
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
    QR_FOLDER = os.path.join(os.path.dirname(__file__), "static", "qr")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}