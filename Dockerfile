# ============================================================
# Dockerfile — Smart Attendance System
# ============================================================
# Base: Python 3.11 slim (Debian Bookworm)
# Uses dlib-bin (pre-compiled wheel) to avoid the ~20-min
# CMake/C++ compile that causes Render free-tier timeouts.
# ============================================================

FROM python:3.11-slim-bookworm

# ── System dependencies ─────────────────────────────────────
# Required by dlib, OpenCV headless, and mysql-connector
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools (needed by some wheels)
    build-essential \
    # dlib native deps
    libopenblas-dev \
    liblapack-dev \
    # OpenCV headless deps
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    # MySQL client headers
    default-libmysqlclient-dev \
    # Cleanup
 && rm -rf /var/lib/apt/lists/*

# ── Working directory ───────────────────────────────────────
WORKDIR /app

# ── Python dependencies ─────────────────────────────────────
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip and install packages
# dlib-bin ships a pre-compiled wheel — no CMake needed at build time
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# ── Application source ──────────────────────────────────────
COPY . .

# ── Runtime directories ─────────────────────────────────────
# Ensure face dataset and encodings dirs exist inside the container
RUN mkdir -p dataset/faces dataset

# ── Expose port ─────────────────────────────────────────────
EXPOSE 10000

# ── Start command ───────────────────────────────────────────
# Render injects $PORT at runtime; we default to 10000
CMD ["gunicorn", "app:app", \
     "--workers", "2", \
     "--timeout", "120", \
     "--bind", "0.0.0.0:10000"]
