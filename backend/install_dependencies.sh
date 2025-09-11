#!/bin/bash
set -e

# Install system dependencies
apt-get update
apt-get install -y tesseract-ocr poppler-utils

# Install Python dependencies
pip install -r requirements.txt
