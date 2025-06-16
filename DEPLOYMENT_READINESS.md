# Deployment Readiness Checklist & Validation

This document outlines QA/UAT checklists, validation notes for functionality, performance, and security, and considerations for deployment configurations.

## 1. Quality Assurance (QA) Checklist

This checklist is for internal verification of functionality and stability.

**Environment:** Staging or a production-like environment.

### 1.1. Core Functionality
- [ ] **User Authentication:**
    - [ ] User registration (successful, email sent - if MailHog accessible)
    - [ ] User login (successful with correct credentials)
    - [ ] User logout
    - [ ] Password reset flow (email sent, link works - if MailHog accessible)
    - [ ] Protected routes are inaccessible to unauthenticated users.
- [ ] **Venue Management (Admin/Venue Manager Role):**
    - [ ] Create new venue (all fields, image upload if applicable)
    - [ ] View venue list (check filtering: capacity, amenities, search)
    - [ ] View venue details
    - [ ] Update existing venue
    - [ ] Delete venue
- [ ] **Event Management (Admin/Event Organizer Role):**
    - [ ] Create new event (linking to venue, setting ticket price, capacity)
    - [ ] View event list (check filtering: date, category, venue, search)
    - [ ] View event details
    - [ ] Update existing event
    - [ ] Delete event
- [ ] **Booking Management (User Role):**
    - [ ] User can view event details and available tickets.
    - [ ] User can create a booking for an event.
    - [ ] Booking correctly calculates `total_price` based on `price_per_ticket_at_booking`.
    - [ ] Event capacity prevents overbooking.
    - [ ] User can view their own bookings.
    - [ ] User can cancel their own booking (if allowed by status).
- [ ] **Booking Management (Admin Role):**
    - [ ] Admin can view all bookings.
    - [ ] Admin can manage/update booking status (e.g., manually confirm).

### 1.2. Payment Integration (Stripe)
- [ ] **Payment Intent Creation:**
    - [ ] Initiating a booking for a paid event successfully creates a PaymentIntent.
    - [ ] Frontend receives `client_secret`.
- [ ] **Stripe Elements Form:**
    - [ ] Payment form loads correctly with Stripe Elements.
    - [ ] Card input is PCI compliant (hosted by Stripe).
    - [ ] Form validation for card details works.
- [ ] **Payment Submission & Confirmation:**
    - [ ] Successful payment submission updates booking status to 'confirmed'.
    - [ ] Failed payment submission shows an error and booking status remains 'pending' or 'failed'.
    - [ ] User is redirected to appropriate success/failure page.
- [ ] **Webhook Handling:**
    - [ ] (Requires Stripe CLI or ngrok for local testing) Stripe webhooks for `payment_intent.succeeded` and `payment_intent.payment_failed` are received by the backend.
    - [ ] Webhooks correctly update booking and payment status.

### 1.3. Email Notifications
- [ ] **Registration Email:** Sent upon new user registration.
- [ ] **Booking Confirmation Email:** Sent after successful booking (and payment, if applicable).
- [ ] **Booking Cancellation Email:** Sent after user cancels a booking.
- [ ] **Payment Success Email:** Sent after payment webhook confirms success.
- [ ] **Payment Failure Email:** Sent after payment webhook confirms failure.
- [ ] (Verify email content and links in a tool like MailHog if testing locally/staging)

### 1.4. Role-Based Access Control
- [ ] **Venue Manager:**
    - [ ] Can create/edit/delete their own venues.
    - [ ] Cannot edit/delete venues owned by others.
    - [ ] Cannot access event creation unless also an Event Organizer.
- [ ] **Event Organizer:**
    - [ ] Can create/edit/delete their own events.
    - [ ] Cannot edit/delete events organized by others.
    - [ ] Cannot access venue creation unless also a Venue Manager.
- [ ] **Regular User (Customer):**
    - [ ] Can view venues and events.
    - [ ] Can make bookings.
    - [ ] Cannot access admin/management UIs for venues/events.
- [ ] **Admin User:**
    - [ ] Has superuser access to all data via Django Admin.
    - [ ] Can perform all actions via API if permission classes allow `IsAdminUser`.

### 1.5. Error Handling & Edge Cases
- [ ] Invalid form submissions show clear error messages (frontend and backend).
- [ ] API error responses are handled gracefully by the frontend.
- [ ] Test with unexpected inputs or data.
- [ ] Capacity limits are strictly enforced under various booking attempts.
- [ ] Price changes for events do not affect already booked ticket prices.

## 2. User Acceptance Testing (UAT) Checklist

This checklist is for stakeholders or end-users to validate the platform meets business requirements.

**Environment:** Staging or production.

### 2.1. Key User Flows
- [ ] **New User Registration and First Booking:**
    - [ ] User can easily register.
    - [ ] User can find an event.
    - [ ] User can understand event details and pricing.
    - [ ] User can complete the booking and payment process smoothly.
    - [ ] User receives confirmation (on-screen and via email).
- [ ] **Venue Manager Onboarding and Event Creation (if applicable to UAT users):**
    - [ ] Venue manager can register/be assigned role.
    - [ ] Venue manager can create and manage their venue(s).
    - [ ] Event organizer can create and manage events at their venue(s).
- [ ] **Managing Existing Bookings:**
    - [ ] User can view their past and upcoming bookings.
    - [ ] User can cancel a booking (if applicable).

### 2.2. Usability & UX
- [ ] Navigation is intuitive.
- [ ] Information is clearly presented.
- [ ] Forms are easy to understand and complete.
- [ ] Error messages are helpful.
- [ ] The platform is responsive and performs well on common devices/browsers.

### 2.3. Feature Completeness (as per current phase)
- [ ] All agreed-upon features for the current phase are present and working.
- [ ] Payment processing is secure and reliable.
- [ ] Email notifications are timely and accurate.

## 3. Functionality, Performance & Security Validation (Notes)

### 3.1. Functionality
*   Based on code implementation and reviews, all core features (auth, venues, events, bookings), payment integration (Stripe), email notifications, role-based access, capacity management, and price snapshotting are expected to be functional.
*   **Critical Test:** Full end-to-end booking flow with real (test mode) Stripe payment.

### 3.2. Performance
*   **Areas to Monitor:**
    *   Database queries for list views (events, venues) with many entries, especially with complex filters. Use Django Debug Toolbar or similar tools to inspect queries.
    *   Booking creation under load (potential for capacity check bottlenecks - though serializer validation is primary).
    *   Frontend rendering speed for large lists or complex pages.
*   **Recommendations:**
    *   Implement database indexing for frequently filtered fields.
    *   Consider pagination for all list views.
    *   Load testing (e.g., using k6, Locust) should be performed before high-traffic production launch, focusing on booking and event listing APIs.

### 3.3. Security
*   **Measures in Place (from review):**
    *   **Input Validation:** Django forms/serializers and frontend form validation.
    *   **Authentication & Authorization:** Django's auth system, `dj-rest-auth`, custom role permissions.
    *   **CSRF Protection:** Enabled by default in Django (ensure frontend sends CSRF token if using session auth for some parts, or relies on token auth which is often exempt for APIs).
    *   **XSS Protection:** Django templates auto-escape. Frontend frameworks like React also help prevent XSS.
    *   **Secrets Management:** Use of `.env` files for secrets. Ensure these are not committed to Git (already in `.gitignore`).
    *   **Stripe Integration:** Uses Stripe Elements for PCI compliance (card details don't hit the server). Webhook signature verification.
    *   **HTTPS:** Should be enforced in production by the load balancer/reverse proxy.
    *   **Dependency Vulnerability Scanning:** `npm audit` added to CI for frontend. Poetry for backend helps manage dependencies (though audit needs separate tool like `safety`).
*   **Further Checks/Recommendations:**
    *   Run security scanning tools (e.g., OWASP ZAP, Snyk for backend dependencies).
    *   Review Django security settings (`settings.py`) against production checklist (e.g., `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`).
    *   Ensure `DEBUG = False` in production.
    *   Regularly update dependencies.

## 4. Deployment Configurations & Rollback

### 4.1. Deployment Scripts & Environment
*   **Containerization:** Backend (Django/Gunicorn) and Frontend (Next.js) are containerized using Docker. `docker-compose.yml` is available for local/dev multi-container setup.
*   **Production Docker Images:** Ensure Dockerfiles are optimized for production (multi-stage builds, non-root users, minimal layers). The current Dockerfiles seem to follow good practices (e.g., `poetry install --no-dev` for backend, `npm ci` for frontend).
*   **Environment Variables:**
    *   Backend (`event_booking_platform_backend/.env.example`): `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL` (if used), `ALLOWED_HOSTS`, Stripe keys (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`), Email settings (`EMAIL_HOST`, etc.).
    *   Frontend (`event_booking_platform_frontend/.env.local.example`): `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`.
    *   All production values must be securely managed (e.g., using platform-specific secret stores).
*   **Database:** PostgreSQL is configured. Ensure production database is regularly backed up.
*   **Static & Media Files (Django):**
    *   `python manage.py collectstatic` is run in backend Dockerfile. Ensure static files are served efficiently in production (e.g., by a reverse proxy like Nginx or a CDN).
    *   Media files (user uploads) need a persistent storage solution (e.g., AWS S3, Google Cloud Storage) and configuration in Django settings.

### 4.2. Rollback Strategy
*   **Docker Images:** If deployment is via Docker, rollback can involve deploying a previously known good image tag.
*   **Database:**
    *   Regular database backups are crucial.
    *   For schema changes (migrations), rollbacks can be complex. Test migrations thoroughly in staging. Have a plan for reverting data if a bad migration is applied (restore from backup is often the safest for complex issues).
*   **Blue/Green or Canary Deployments:** For more advanced setups, consider blue/green or canary deployment strategies to minimize downtime and risk.
