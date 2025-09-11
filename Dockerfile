# --- PASTE THIS ENTIRE BLOCK INTO your new Dockerfile ---

# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent caching issues
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install the system dependencies that your PDF processor needs
# This is the step that was failing before
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY backend/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your backend code into the container at /app
COPY backend/ .

# The command to run your app using Gunicorn
# This will use the PORT environment variable that Render provides automatically
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:${PORT}", "--timeout", "120"]