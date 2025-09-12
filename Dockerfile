# --- PASTE THIS ENTIRE BLOCK INTO your Dockerfile ---

# Use an official, lean Python runtime as a base
FROM python:3.11-slim

# Set environment variables for best practices
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# --- THE CRITICAL STEP ---
# Install all system dependencies your app needs (Poppler, Tesseract, and compilers)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker's caching
COPY backend/requirements.txt .

# Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your backend application code into the container
COPY backend/ .

# The command to run your app using a production-grade Gunicorn server
# It automatically uses the PORT that Render provides
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --timeout 120