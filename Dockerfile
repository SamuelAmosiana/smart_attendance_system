# ============================================================
# Dockerfile — Smart Attendance System (Production)
# ============================================================
# Uses requirements-prod.txt which EXCLUDES dlib / face_recognition.
# Those packages require 8GB+ RAM to build and a physical webcam
# to run — neither available on Render free tier.
# The app gracefully degrades: all non-face features work fully.
# ============================================================

FROM python:3.11-slim-bookworm

# ── System dependencies ─────────────────────────────────────
# Minimal set — no dlib/OpenCV build tools needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────
# Use production requirements (no dlib/face_recognition/opencv)
COPY requirements-prod.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements-prod.txt

# ── Application source ──────────────────────────────────────
COPY . .

# ── Runtime directories ─────────────────────────────────────
RUN mkdir -p dataset/faces dataset

# ── Expose port ─────────────────────────────────────────────
EXPOSE 10000

# ── Start command ───────────────────────────────────────────
CMD ["gunicorn", "app:app", \
     "--workers", "2", \
     "--timeout", "120", \
     "--bind", "0.0.0.0:10000"]
