#!/usr/bin/env bash
# ============================================================
# build.sh — Render build script
# Installs system-level dependencies required by dlib/OpenCV
# then installs Python packages from requirements.txt
# ============================================================

set -e   # Exit immediately on any error

echo "=== Installing system dependencies ==="
apt-get update -y
apt-get install -y \
  cmake \
  build-essential \
  libopenblas-dev \
  liblapack-dev \
  libx11-dev \
  libgtk-3-dev \
  libboost-python-dev

echo "=== Upgrading pip ==="
pip install --upgrade pip

echo "=== Installing Python packages ==="
pip install -r requirements.txt

echo "=== Build complete ==="
