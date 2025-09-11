#!/usr/-bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr poppler-utils

# --- THIS IS THE FIX ---
# Upgrade pip and its tools first
pip install --upgrade pip setuptools wheel

# Now, install the project dependencies
pip install -r requirements.txt
