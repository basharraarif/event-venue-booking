# Deployment Readiness Checklist & Validation

This document outlines QA/UAT checklists, validation notes for functionality, performance, and security, and considerations for deployment configurations.

## 1. Quality Assurance (QA) Checklist

This checklist is for internal verification of functionality and stability.

**Environment:** Staging or a production-like environment.

### 1.1. Core Functionality
- [ ] **User Authentication:**
    - [ ] User registration (successful, email sent - if MailHog accessible) *(Verified as implemented and tested, including email sending via signals)*
    - [ ] User login (successful with correct credentials) *(Core Django/dj_rest_auth functionality, assumed tested)*
    - [ ] User logout *(Core Django/dj_rest_auth functionality, assumed tested)*
    - [ ] Password reset flow (email sent, link works - if MailHog accessible) *(Handled by django-allauth, templates verified)*
    - [ ] Protected routes are inaccessible to unauthenticated users. *(Standard DRF permission behavior, verified in specific ViewSet permission tests)*
- [ ] **Venue Management (Admin/Venue Manager Role):**
    - [ ] Create new venue (all fields, image upload if applicable) *(Functionality implemented; image upload not specified but core CRUD is present. Permissions for Venue Manager tested)*
    - [ ] View venue list (check filtering: capacity, amenities, search) *(Functionality implemented, filtering capabilities present)*
    - [ ] View venue details *(Functionality implemented)*
    - [ ] Update existing venue *(Functionality implemented, permissions for Venue Manager tested)*
    - [ ] Delete venue *(Functionality implemented, permissions for Venue Manager tested)*
- [ ] **Event Management (Admin/Event Organizer Role):**
    - [ ] Create new event (linking to venue, setting ticket price, capacity) *(Functionality implemented; capacity handling via `max_capacity` on Event model. Permissions for Event Organizer tested)*
    - [ ] View event list (check filtering: date, category, venue, search) *(Functionality implemented, filtering capabilities present)*
    - [ ] View event details *(Functionality implemented)*
    - [ ] Update existing event *(Functionality implemented, permissions for Event Organizer tested)*
    - [ ] Delete event *(Functionality implemented, permissions for Event Organizer tested)*
- [ ] **Booking Management (User Role):**
    - [ ] User can view event details and available tickets. *(Functionality implemented)*
    - [ ] User can create a booking for an event. *(Functionality implemented and tested)*
    - [ ] Booking correctly calculates `total_price` based on `price_per_ticket_at_booking`. *(Verified, price snapshotting implemented and tested)*
    - [ ] Event capacity prevents overbooking. *(Verified, implemented and tested in BookingSerializer and views)*
    - [ ] User can view their own bookings. *(Verified, implemented via `BookingViewSet.get_queryset`)*
    - [ ] User can cancel their own booking (if allowed by status). *(Verified, implemented and tested)*
- [ ] **Booking Management (Admin Role):**
    - [ ] Admin can view all bookings. *(Verified, implemented via `BookingViewSet.get_queryset`)*
    - [ ] Admin can manage/update booking status (e.g., manually confirm). *(General update capability via API, specific admin actions for status not detailed but possible via PATCH)*

### 1.2. Payment Integration (Stripe)
- [ ] **Payment Intent Creation:**
    - [ ] Initiating a booking for a paid event successfully creates a PaymentIntent. *(Backend logic verified: Booking becomes PENDING_PAYMENT; frontend calls CreatePaymentIntentView. Integration test covers this flow.)*
    - [ ] Frontend receives `client_secret`. *(CreatePaymentIntentView confirmed to return client_secret. Frontend part is conceptual.)*
- [ ] **Stripe Elements Form:** *(Frontend specific, conceptual verification)*
    - [ ] Payment form loads correctly with Stripe Elements.
    - [ ] Card input is PCI compliant (hosted by Stripe).
    - [ ] Form validation for card details works.
- [ ] **Payment Submission & Confirmation:** *(Partially backend, partially frontend)*
    - [ ] Successful payment submission updates booking status to 'confirmed'. *(Backend webhook logic verified and tested)*
    - [ ] Failed payment submission shows an error and booking status remains 'pending' or 'failed'. *(Backend webhook logic for failure verified and tested. Booking status remains PENDING_PAYMENT, Payment status becomes 'failed')*
    - [ ] User is redirected to appropriate success/failure page. *(Frontend specific)*
- [ ] **Webhook Handling:**
    - [ ] (Requires Stripe CLI or ngrok for local testing) Stripe webhooks for `payment_intent.succeeded` and `payment_intent.payment_failed` are received by the backend. *(Webhook view implemented and unit tested with mocked Stripe events)*
    - [ ] Webhooks correctly update booking and payment status. *(Verified in unit and integration tests)*

### 1.3. Email Notifications
- [ ] **Registration Email:** Sent upon new user registration. *(Verified, implemented via signals, tested)*
- [ ] **Booking Confirmation Email:** Sent after successful booking (and payment, if applicable). *(Verified, implemented, tested)*
- [ ] **Booking Pending Email:** (Added item) Sent when a booking requires payment. *(Verified, implemented, tested)*
- [ ] **Booking Cancellation Email:** Sent after user cancels a booking. *(Verified, implemented, tested)*
- [ ] **Payment Success Email:** Sent after payment webhook confirms success (usually triggers Booking Confirmation email). *(Verified, implemented, tested)*
- [ ] **Payment Failure Email:** Sent after payment webhook confirms failure. *(Verified, implemented, tested)*
- [ ] (Verify email content and links in a tool like MailHog if testing locally/staging) *(Note: Email content verification is manual/visual)*

### 1.4. Role-Based Access Control
- [ ] **Venue Manager:**
    - [ ] Can create/edit/delete their own venues. *(Verified, permissions implemented and tested)*
    - [ ] Cannot edit/delete venues owned by others. *(Verified, permissions implemented and tested)*
    - [ ] Cannot access event creation unless also an Event Organizer. *(Verified by permission logic)*
- [ ] **Event Organizer:**
    - [ ] Can create/edit/delete their own events. *(Verified, permissions implemented and tested)*
    - [ ] Cannot edit/delete events organized by others. *(Verified, permissions implemented and tested)*
    - [ ] Cannot access venue creation unless also a Venue Manager. *(Verified by permission logic)*
- [ ] **Regular User (Customer):**
    - [ ] Can view venues and events. *(Assumed via IsAuthenticatedOrReadOnly on list/retrieve)*
    - [ ] Can make bookings. *(Verified)*
    - [ ] Cannot access admin/management UIs for venues/events. *(Verified by specific role permissions on CUD operations)*
- [ ] **Admin User:**
    - [ ] Has superuser access to all data via Django Admin. *(Standard Django behavior)*
    - [ ] Can perform all actions via API if permission classes allow `IsAdminUser`. *(Verified in permission tests and ViewSet configurations)*

### 1.5. Error Handling & Edge Cases
- [ ] Invalid form submissions show clear error messages (frontend and backend). *(Backend validation by DRF serializers verified. Frontend conceptual.)*
- [ ] API error responses are handled gracefully by the frontend. *(Frontend specific, conceptual)*
- [ ] Test with unexpected inputs or data. *(Unit tests cover some, ongoing process)*
- [ ] Capacity limits are strictly enforced under various booking attempts. *(Verified, implemented and tested, including new test for booking cancelled events)*
- [ ] Price changes for events do not affect already booked ticket prices. *(Verified, implemented and tested)*
- [ ] Payment for bookings on cancelled events is prevented. *(Verified, logic added to CreatePaymentIntentView, test updated/added)*

## 2. User Acceptance Testing (UAT) Checklist

This checklist is for stakeholders or end-users to validate the platform meets business requirements.

**Environment:** Staging or production.

### 2.1. Key User Flows
- [ ] **New User Registration and First Booking:**
    - [ ] User can easily register. *(Backend implemented)*
    - [ ] User can find an event. *(Backend implemented)*
    - [ ] User can understand event details and pricing. *(Backend provides data)*
    - [ ] User can complete the booking and payment process smoothly. *(Backend logic for booking, payment intent, and webhook confirmation implemented)*
    - [ ] User receives confirmation (on-screen and via email). *(Backend sends emails, on-screen is frontend)*
- [ ] **Venue Manager Onboarding and Event Creation (if applicable to UAT users):**
    - [ ] Venue manager can register/be assigned role. *(Backend role system implemented)*
    - [ ] Venue manager can create and manage their venue(s). *(Backend CRUD and permissions for venues implemented)*
    - [ ] Event organizer can create and manage events at their venue(s). *(Backend CRUD and permissions for events implemented. Note: Event Organizers manage events, Venue Managers manage Venues. Organizers can create events at any valid venue they have access to select.)*
- [ ] **Managing Existing Bookings:**
    - [ ] User can view their past and upcoming bookings. *(Backend implemented)*
    - [ ] User can cancel a booking (if applicable). *(Backend implemented)*

### 2.2. Usability & UX *(Primarily frontend, notes for stakeholder validation)*
- [ ] Navigation is intuitive.
- [ ] Information is clearly presented.
- [ ] Forms are easy to understand and complete.
- [ ] Error messages are helpful.
- [ ] The platform is responsive and performs well on common devices/browsers.

### 2.3. Feature Completeness (as per current phase)
- [ ] All agreed-upon features for the current phase are present and working. *(Backend features addressed in previous steps are implemented)*
- [ ] Payment processing is secure and reliable. *(Backend Stripe integration implemented and tested. Reliability includes webhook handling.)*
- [ ] Email notifications are timely and accurate. *(Backend email sending for key events implemented and tested)*

## 3. Functionality, Performance & Security Validation (Notes)

### 3.1. Functionality
*   Based on code implementation, reviews, and recent test expansions, core features (auth, venues, events, bookings), payment integration (Stripe), email notifications for key events, advanced role-based access control (Customer, Event Organizer, Venue Manager, Admin), event capacity management, and ticket price snapshotting are implemented and functional at the backend level.
*   **Critical Test:** Full end-to-end booking flow with real (test mode) Stripe payment has been outlined and implemented as an integration test (`test_full_booking_flow.py`), covering successful and failed payment scenarios.

### 3.2. Performance
*   **Areas to Monitor:**
    *   Database queries for list views (events, venues, bookings) with many entries, especially with complex filters (e.g., by category name, M2M relations, JSON fields like amenities, role-based conditions in `BookingViewSet`). Use Django Debug Toolbar or similar tools to inspect queries.
    *   Booking creation/update under load, particularly the capacity check logic (aggregate SUM query) in `BookingSerializer`.
    *   Frontend rendering speed for large lists or complex pages.
*   **Recommendations:**
    *   **Database Indexing:**
        - **Event:** `name` (text search optimized), `venue_id`, `organizer_id`, `status`, `start_time`, `end_time`. Composite indexes like `(venue_id, start_time)`. Ensure M2M table for `categories` is indexed.
        - **Venue:** `name` (text search optimized), `address` (text search), `capacity`, `owner_id`. For `amenities` (JSONField), use GIN indexes if on PostgreSQL.
        - **Booking:** `event_id`, `user_id`, `status`. Composite `(event_id, status)` for capacity checks. `payment_intent_id` (unique, indexed).
        - **User/Role M2M:** Ensure intermediate table fields are indexed.
        - **Payment:** `stripe_payment_intent_id` (unique, indexed).
    *   **Pagination:** Ensure all list views are paginated (standard in DRF ViewSets).
    *   **Caching:**
        - Use Redis (config present in `settings.py`) for caching frequently accessed, rarely changed data (e.g., category lists, potentially venue/event lists with common filters, specific event/venue details).
        - Implement robust cache invalidation strategies (e.g., on model save/delete signals).
    *   **Concurrency:** For booking capacity checks under high load, consider database-level locking (e.g., `SELECT FOR UPDATE` on Event) or optimistic locking strategies to prevent race conditions. This is a known area for future improvement if high contention is observed.
    *   **Load Testing:** Perform load testing (e.g., using k6, Locust) focusing on booking creation/updates and event listing APIs before high-traffic production launch.

### 3.3. Security
*   **Measures in Place (from review):**
    *   **Input Validation:** Django forms/serializers and DRF validation.
    *   **Authentication & Authorization:** Django's auth system, `dj_rest_auth`, custom role permissions (`IsCustomer`, `IsEventOrganizer`, `IsVenueManager`, `IsAdminUser`).
    *   **CSRF Protection:** Enabled by default. API uses TokenAuthentication, generally mitigating CSRF for API endpoints.
    *   **XSS Protection:** Django templates auto-escape.
    *   **Secrets Management:** `.env` files used for `SECRET_KEY`, `DATABASE_URL`, Stripe keys, email credentials. `settings.py` loads these securely.
    *   **Stripe Integration:** Uses Stripe Elements (PCI compliance for card data handled by Stripe). Webhook signature verification is implemented in `StripeWebhookView`.
    *   **HTTPS:** Recommended for production (see below).
    *   **Dependency Vulnerability Scanning:** `npm audit` for frontend noted. Backend scanning recommended.
*   **Production Security Settings (`settings.py` review):**
    *   `DEBUG = env("DEBUG", default=False)`: **Correct.**
    *   `SECRET_KEY` loaded from env: **Correct.**
    *   `ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[...] if DEBUG else [])`: **Correct.** Must be configured for production.
    *   `SESSION_COOKIE_SECURE = not DEBUG`: **Correct.**
    *   `CSRF_COOKIE_SECURE = not DEBUG`: **Correct.**
    *   `X_FRAME_OPTIONS` (via middleware): **Correct.**
    *   **Recommendations for Production (ensure these are `True` or configured):**
        - `SECURE_SSL_REDIRECT = True`
        - `SECURE_HSTS_SECONDS` (e.g., 3600 initially, then increase to standard values like 31536000)
        - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` (if applicable)
        - `SECURE_HSTS_PRELOAD = True` (after HSTS confirmed working)
        - `SECURE_CONTENT_TYPE_NOSNIFF = True`
        - `SECURE_PROXY_SSL_HEADER` (if behind a reverse proxy terminating SSL)
*   **Further Checks/Recommendations:**
    *   Implement backend dependency vulnerability scanning (e.g., `safety`, Snyk).
    *   Consider implementing `Content-Security-Policy` headers for added XSS protection.
    *   Regularly update dependencies.

## 4. Deployment Configurations & Rollback

### 4.1. Deployment Scripts & Environment
*   **Containerization:** Backend (Django/Gunicorn) and Frontend (Next.js) are containerized. `docker-compose.yml` for local setup.
*   **Production Docker Images:** Dockerfiles seem to follow good practices (e.g., `poetry install --no-dev` for backend implies Poetry is used or intended; `requirements.txt` is primary for now. `npm ci` for frontend). Ensure optimization (multi-stage, non-root).
*   **Environment Variables:**
    *   Backend (`event_booking_platform_backend/.env.example`): Confirmed to cover `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL`, `ALLOWED_HOSTS`, Stripe keys (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`), and Email settings (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `SERVER_EMAIL`). All critical variables are present.
    *   Frontend (`event_booking_platform_frontend/.env.local.example`): Includes necessary public keys and API base URL.
    *   Production values must be securely managed.
*   **Database:** PostgreSQL recommended and configurable via `DATABASE_URL`. Regular backups are crucial.
*   **Static & Media Files (Django):**
    *   `python manage.py collectstatic` is confirmed to be run in the backend Dockerfile. Serving via Nginx or CDN is standard for production.
    *   **Media files (user uploads):** Explicitly state that a persistent cloud storage solution (e.g., AWS S3, Google Cloud Storage) **must** be configured for `MEDIA_ROOT` and `MEDIA_URL` in production, as local storage in containers is ephemeral. (Added emphasis)

### 4.2. Rollback Strategy
*   **Docker Images:** Deploying a previous image tag is a standard rollback method.
*   **Database:**
    *   Regular backups are essential.
    *   Test migrations thoroughly in staging. For complex issues, restoring from backup is often the safest for data integrity.
*   **Blue/Green or Canary Deployments:** Recommended for advanced setups to minimize risk.

This document has been updated based on recent feature completions, testing, and reviews.
