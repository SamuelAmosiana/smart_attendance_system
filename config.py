# ============================================================
# config.py — Application Configuration
# ============================================================
# Centralises all app settings. Edit this file to match
# your local MySQL credentials before running the app.
# ============================================================

import os

class Config:
    # ----------------------------------------------------------
    # Flask secret key — used for session signing.
    # Change this to a long random string in production.
    # ----------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "smart_attendance_secret_key_2024")

    # ----------------------------------------------------------
    # MySQL Database settings
    # ----------------------------------------------------------
    DB_HOST     = os.environ.get("DB_HOST",     "localhost")
    DB_PORT     = int(os.environ.get("DB_PORT", 3306))
    DB_USER     = os.environ.get("DB_USER",     "root")        # Change to your MySQL user
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")            # Change to your MySQL password
    DB_NAME     = os.environ.get("DB_NAME",     "smart_attendance_db")

    # ----------------------------------------------------------
    # Face Recognition settings
    # ----------------------------------------------------------
    # HOG model is CPU-friendly (no GPU required)
    FACE_DETECTION_MODEL    = "hog"
    # Number of video frames to skip between recognition passes
    FRAME_SKIP              = 3
    # Resize factor — smaller = faster processing on low-end CPUs
    FRAME_RESIZE_SCALE      = 0.5
    # Tolerance for face matching — lower = stricter (0.4–0.6 recommended)
    FACE_RECOGNITION_TOLERANCE = 0.5

    # ----------------------------------------------------------
    # File-system paths
    # ----------------------------------------------------------
    BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
    DATASET_DIR     = os.path.join(BASE_DIR, "dataset", "faces")
    ENCODINGS_FILE  = os.path.join(BASE_DIR, "dataset", "encodings.pkl")

    # ----------------------------------------------------------
    # Upload constraints
    # ----------------------------------------------------------
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB max upload size
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
