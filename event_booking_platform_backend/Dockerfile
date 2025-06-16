# syntax=docker/dockerfile:1

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE event_booking_platform_backend.settings

WORKDIR /app

# Install system dependencies (if any) - keep this section if needed
# RUN apt-get update && apt-get install -y --no-install-recommends some-system-lib && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy Poetry project files
COPY pyproject.toml poetry.lock* /app/
# If poetry.lock does not exist, this will copy only pyproject.toml.
# poetry.lock* ensures it's copied if present.

# Configure Poetry and install dependencies
# --no-dev: Exclude development dependencies for a smaller production image
# virtualenvs.create false: Install packages directly into the system environment
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-dev

# Copy the rest of the application code
COPY . /app/

# Create directories for static and media files
RUN mkdir -p /app/staticfiles /app/media

# Run collectstatic
RUN poetry run python manage.py collectstatic --noinput --clear
# Note: Using 'poetry run' to ensure it uses the environment Poetry set up.

# Expose port Gunicorn will run on
EXPOSE 8000

# Command to run the application using Gunicorn
# Ensure Gunicorn is in pyproject.toml's main dependencies
CMD ["poetry", "run", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "event_booking_platform_backend.wsgi:application"]
# Using 'poetry run' for gunicorn as well.
