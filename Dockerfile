# ============================================================
# Dockerfile — Smart Attendance System
# ============================================================
# Base: Python 3.11 slim (Debian Bookworm)
# Database: PostgreSQL via psycopg2-binary (no system deps needed)
# Face recognition: dlib-bin (pre-compiled wheel, no CMake wait)
# ============================================================

FROM python:3.11-slim-bookworm

# ── System dependencies ─────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # dlib native deps
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    # OpenCV headless deps
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
 && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

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
