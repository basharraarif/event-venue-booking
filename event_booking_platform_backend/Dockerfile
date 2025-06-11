# syntax=docker/dockerfile:1

# Stage 1: Build stage (if using multi-stage builds for smaller prod image)
# FROM python:3.10-slim as builder
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1
# WORKDIR /app
# COPY requirements.txt /app/
# RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Stage 2: Production image
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE event_booking_platform_backend.settings # Important for Gunicorn

WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# RUN apt-get update && apt-get install -y --no-install-recommends some-system-lib && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
# RUN pip install --no-cache-dir /wheels/* # If using multi-stage build for wheels
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Create directories for static and media files if they are not mapped via volumes externally
# These RUN commands will create them within the image.
# If using volumes, these might not be strictly necessary inside the Dockerfile
# but good for completeness if the image is run without volumes.
RUN mkdir -p /app/staticfiles /app/media

# Run collectstatic
# This command should be run as the user that will run the application if not root
# For simplicity here, running as root. Consider a non-root user for production.
RUN python manage.py collectstatic --noinput --clear
# --clear is useful to remove stale files before collecting new ones

# Expose port Gunicorn will run on
EXPOSE 8000

# Command to run the application using Gunicorn
# Ensure Gunicorn is in requirements.txt
# The number of workers can be tuned (e.g., (2 x $CPU_CORES) + 1)
# For a simple setup:
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "event_booking_platform_backend.wsgi:application"]

# Example of a more robust CMD with an entrypoint script:
# ENTRYPOINT ["/app/entrypoint.sh"]
# CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "event_booking_platform_backend.wsgi:application"]
# where entrypoint.sh might handle migrations, creating superuser, etc.
# For this task, direct gunicorn CMD is sufficient.
