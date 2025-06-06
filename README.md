# Event & Venue Booking Management SaaS Platform (Phase 1)

## Project Overview

This project is a Software as a Service (SaaS) platform designed to manage event and venue bookings. Phase 1 focuses on core venue management functionalities and basic user authentication, providing a foundation for future expansion into event booking, user roles, and more advanced features.

The platform consists of a Django REST Framework backend and a Next.js frontend, containerized using Docker for ease of development and deployment.

## Features (Phase 1 Focus)

*   **Venue Management:**
    *   CRUD operations for venues (Create, Read, Update, Delete).
    *   Filtering venues by capacity, availability, and price via the UI.
    *   Searching venues by name, address, and amenities via the UI.
*   **User Authentication:**
    *   Basic user registration (username, email, password).
    *   Token-based authentication (login/logout).
    *   Protected routes for venue creation and editing.
*   **Containerization:**
    *   Dockerized backend and frontend applications.
    *   Docker Compose setup for local development environment including PostgreSQL database and Redis cache.
*   **API Documentation:**
    *   Automated API schema generation and UI (Swagger/ReDoc) via `drf-spectacular`.
*   **CI/CD:**
    *   Initial GitHub Actions workflow for linting, testing, and building Docker images.
*   **Testing:**
    *   Unit tests for backend models, serializers, and views (Pytest).
    *   Unit tests for frontend components and pages (Jest & React Testing Library).
    *   Basic E2E test structure for frontend (Cypress).

## Tech Stack (Phase 1)

*   **Backend:** Django, Django REST Framework, `dj-rest-auth`, `django-allauth`, `drf-spectacular`
*   **Frontend:** Next.js, React, TypeScript, Axios, Tailwind CSS
*   **Database:** PostgreSQL
*   **Cache:** Redis
*   **Containerization:** Docker, Docker Compose
*   **Testing:** Pytest (Backend), Jest & React Testing Library (Frontend), Cypress (Frontend E2E)
*   **CI/CD:** GitHub Actions

## Prerequisites

*   Git
*   Docker Desktop (or Docker Engine + Docker Compose CLI)

## Getting Started / Local Development Setup

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory_name>
    ```

2.  **Set Up Environment Files:**

    *   **Backend:**
        *   Navigate to the `event_booking_platform_backend` directory.
        *   Copy the example environment file:
            ```bash
            cp .env.example .env
            ```
        *   Review `event_booking_platform_backend/.env`. The defaults are configured to work with the Docker Compose setup (e.g., database connection). You might want to change `SECRET_KEY` for your local instance.

    *   **Frontend:**
        *   Navigate to the `event_booking_platform_frontend` directory.
        *   Copy the example environment file:
            ```bash
            cp .env.local.example .env.local
            ```
        *   Review `event_booking_platform_frontend/.env.local`. The `NEXT_PUBLIC_API_BASE_URL` should default to `http://localhost:8000/api`, which is correct for the Docker Compose setup.

3.  **Build and Run the Application (Docker Compose):**
    From the project root directory:
    ```bash
    docker-compose up --build -d
    ```
    This command will build the Docker images (if not already built or if changes are detected) and start all services (backend, frontend, database, cache) in detached mode.

4.  **Accessing the Application:**
    *   **Frontend:** Open your browser and go to `http://localhost:3000`
    *   **Backend API:** Accessible at `http://localhost:8000/api/`
    *   **API Documentation (Swagger UI):** `http://localhost:8000/api/schema/swagger-ui/`
    *   **API Documentation (ReDoc):** `http://localhost:8000/api/schema/redoc/`

5.  **Stopping the Application:**
    To stop all running services:
    ```bash
    docker-compose down
    ```
    To stop and remove volumes (e.g., database data):
    ```bash
    docker-compose down -v
    ```

## Running Tests

Tests can be run inside their respective Docker containers to ensure a consistent environment.

*   **Backend (Pytest):**
    ```bash
    docker-compose exec backend pytest
    ```
    To include coverage:
    ```bash
    docker-compose exec backend pytest --cov=.
    ```

*   **Frontend (Jest/RTL):**
    ```bash
    docker-compose exec frontend npm test
    ```
    (Note: Previous subtasks identified potential instabilities with Jest execution in the sandbox environment. This command is the standard way to run it.)

*   **Frontend (Cypress E2E - Interactive):**
    Ensure the application is running via `docker-compose up`. Then, open Cypress:
    ```bash
    # In event_booking_platform_frontend directory
    npm run cypress:open
    # Or from project root:
    # (cd event_booking_platform_frontend && npm run cypress:open)
    ```
*   **Frontend (Cypress E2E - Headless):**
    ```bash
    docker-compose exec frontend npm run cypress:run
    ```

## API Documentation

The backend API documentation is automatically generated using `drf-spectacular` and is available when the application is running:

*   **Swagger UI:** `http://localhost:8000/api/schema/swagger-ui/`
*   **ReDoc:** `http://localhost:8000/api/schema/redoc/`
*   **Schema File (OpenAPI 3.0.0):** `http://localhost:8000/api/schema/`

## Project Structure (Overview)

```
.
├── .github/workflows/         # GitHub Actions CI/CD pipelines
├── event_booking_platform_backend/  # Django REST Framework backend
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.example
│   ├── .flake8
│   ├── manage.py
│   ├── requirements.txt
│   ├── pytest.ini
│   └── ... (other Django app and project folders: core, venues, etc.)
├── event_booking_platform_frontend/ # Next.js frontend
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── .env.local.example
│   ├── package.json
│   ├── tsconfig.json
│   ├── jest.config.js
│   ├── cypress.config.ts
│   ├── src/
│   └── ... (other Next.js files and folders)
├── docker-compose.yml         # Docker Compose configuration for local development
└── README.md                  # This file
```

## Contributing

We welcome contributions to enhance the Event & Venue Booking Management SaaS Platform! To contribute, please follow these steps:

1.  **Fork the Repository:** Create your own fork of the project on GitHub.
2.  **Create a Branch:** Before making any changes, create a new branch from the `develop` branch (or `main` if `develop` doesn't exist/isn't primary):
    *   For new features: `git checkout -b feature/your-descriptive-feature-name`
    *   For bug fixes: `git checkout -b fix/your-bug-fix-description`
3.  **Make Your Changes:** Implement your feature or bug fix.
4.  **Write Clear Commit Messages:** Follow standard commit message conventions. Briefly explain the "what" and "why" of your changes.
5.  **Run Tests:** Ensure all tests pass before submitting your changes.
    *   **Backend Tests:** From the project root, run `docker-compose exec backend pytest`
    *   **Frontend Unit Tests:** From the project root, run `docker-compose exec frontend npm test`
    *   **Frontend E2E Tests:** Ensure the application is running (e.g., via `docker-compose up -d`). Then, from the `event_booking_platform_frontend` directory, you can run `npm run cypress:open` for interactive mode or `npm run cypress:run` for headless mode. These are also run in CI.
6.  **Push Your Changes:** Push your branch to your forked repository: `git push origin feature/your-descriptive-feature-name`
7.  **Submit a Pull Request:** Open a pull request from your forked repository's branch to the main project's `develop` branch (or `main` if that's the target).
    *   Provide a clear title and description for your pull request, outlining the changes made and any relevant context.

We appreciate your contributions to making this platform better!
```
