# ============================================================
# config.py — Application Configuration
# ============================================================
# Reads DATABASE_URL (injected by Render) for PostgreSQL.
# Falls back to individual DB_* vars for local development.
# ============================================================

import os
import urllib.parse

class Config:
    # ----------------------------------------------------------
    # Flask secret key
    # ----------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart_attendance_secret_key_2024")

    # ----------------------------------------------------------
    # Database — Render injects DATABASE_URL automatically.
    # Parse it so the rest of the app can use individual fields.
    # ----------------------------------------------------------
    _db_url = os.environ.get("DATABASE_URL", "")

    if _db_url:
        # Render uses "postgres://" — psycopg2 requires "postgresql://"
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        _parsed   = urllib.parse.urlparse(_db_url)
        DB_HOST   = _parsed.hostname
        DB_PORT   = _parsed.port or 5432
        DB_USER   = _parsed.username
        DB_PASSWORD = _parsed.password
        DB_NAME   = _parsed.path.lstrip("/")
        DATABASE_URL = _db_url
    else:
        # Local fallback (XAMPP / local Postgres)
        DB_HOST     = os.environ.get("DB_HOST",     "localhost")
        DB_PORT     = int(os.environ.get("DB_PORT", 5432))
        DB_USER     = os.environ.get("DB_USER",     "postgres")
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
        DB_NAME     = os.environ.get("DB_NAME",     "smart_attendance_db")
        DATABASE_URL = (
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )

    # ----------------------------------------------------------
    # Face Recognition settings
    # ----------------------------------------------------------
    FACE_DETECTION_MODEL        = "hog"
    FRAME_SKIP                  = 3
    FRAME_RESIZE_SCALE          = 0.5
    FACE_RECOGNITION_TOLERANCE  = 0.5

    # ----------------------------------------------------------
    # File-system paths
    # ----------------------------------------------------------
    BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
    DATASET_DIR     = os.path.join(BASE_DIR, "dataset", "faces")
    ENCODINGS_FILE  = os.path.join(BASE_DIR, "dataset", "encodings.pkl")

    # ----------------------------------------------------------
    # Upload constraints
    # ----------------------------------------------------------
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
