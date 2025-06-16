# Testing Strategy & Status

This document outlines the current testing strategy, summarizes observed test coverage based on code review, identifies gaps, and proposes test cases for the Event Booking Platform.

**NOTE:** Execution of most test suites (backend pytest, frontend Jest) is currently blocked in the development sandbox due to environment limitations affecting package managers (npm, poetry) and potentially database connectivity for backend tests. The information below is based on code review and prior test suite structure.

## 1. Backend Testing (Django/pytest)

### 1.1. Current Coverage (Based on Review)

*   **Core (`core/`):**
    *   **Models (`test_models.py`):** Good coverage for User, Role models, including custom methods.
    *   **Permissions (`test_permissions.py`):** Comprehensive tests for `IsEventOrganizer`, `IsVenueManager`, and other custom permission classes. Scenarios include various user roles and object ownership.
    *   **Email Utilities (`test_email_utils.py`):** Unit tests for email sending functions (e.g., `send_booking_confirmation_email`, `send_new_user_registration_email`), mocking `EmailMultiAlternatives`. Tests cover correct template usage and context.
    *   **Signals (`test_signals.py` or similar):** (Assumed, need to verify) Tests for signals like new user registration email dispatch.
*   **Venues (`venues/`):**
    *   **Models (`test_models.py`):** Tests for `Venue` model logic.
    *   **Serializers (`test_serializers.py`):** Tests for `VenueSerializer` validation and representation.
    *   **Views (`test_views.py`):** Extensive tests for `VenueViewSet` covering CRUD operations, filtering, and permissions (e.g., only venue managers or admins can edit/delete).
*   **Events (`events/`):**
    *   **Models (`test_models.py`):** Tests for `Event` model logic, including `effective_capacity`.
    *   **Serializers (`test_serializers.py`):** Tests for `EventSerializer`.
    *   **Views (`test_views.py`):** Extensive tests for `EventViewSet` covering CRUD, filtering, and permissions (e.g., only event organizers or admins can edit/delete).
*   **Bookings (`bookings/`):**
    *   **Models (`test_models.py`):** Comprehensive tests for `Booking` model logic, especially `save()` method for `total_price` calculation and `price_per_ticket_at_booking` snapshotting.
    *   **Serializers (`test_serializers.py`):** Extensive tests for `BookingSerializer`, particularly validation logic for:
        *   Event capacity checks (honoring `event.max_capacity` and `venue.capacity`).
        *   Ticket price snapshotting and `total_price` calculation.
    *   **Views (`test_views.py`):** Tests for `BookingViewSet` covering user booking creation, listing own bookings, admin viewing all bookings, and cancellation logic.
*   **Payments (`payments/`):**
    *   **Models (`test_models.py`):** Tests for the `Payment` model.
    *   **Views (`test_views.py`):** Unit tests for `CreatePaymentIntentView` (mocking Stripe API, checking booking ownership) and `StripeWebhookView` (mocking Stripe event verification, checking booking status updates and email dispatch triggers).

### 1.2. Identified Gaps & Proposed New Tests (Backend)

*   **Integration Tests (Cross-App):**
    *   **Full Booking Flow:** An integration test simulating:
        1.  User registers.
        2.  User logs in.
        3.  User books an event (triggering capacity check, price snapshot).
        4.  (Mocked) Payment Intent creation.
        5.  (Mocked) Stripe webhook updates payment status.
        6.  Booking status becomes 'confirmed'.
        7.  Email notification dispatch (mocked).
    *   **Role-Based Access Across Apps:** Tests ensuring an `event_organizer` cannot manage venues they don't own (if that's the rule), and vice-versa.
*   **Email Content Tests:** While email dispatch is tested, detailed content checking of rendered email templates (HTML and text) for various scenarios could be added.
*   **Concurrency Tests:** (Advanced) Tests for potential race conditions in booking capacity checks if `select_for_update` is implemented.
*   **Management Commands:** If any custom management commands exist or are added, they need tests.
*   **Celery Tasks (if applicable):** If asynchronous tasks (e.g., for email sending at scale) are used, those need testing.

## 2. Frontend Testing (Next.js/Jest/RTL/Cypress)

### 2.1. Current Coverage (Based on Review)

*   **Services:**
    *   `authService.ts`: Tests for login, registration, logout functions (mocking API calls).
    *   `eventService.ts`, `venueService.ts`, `bookingService.ts`: Tests for CRUD operations (mocking API calls).
    *   `PaymentService.ts`: Tests for `createPaymentIntent`, `confirmCardPayment` (mocking API calls and Stripe SDK).
*   **Components:**
    *   Auth Components (`LoginForm.tsx`, `RegistrationForm.tsx`): Unit/integration tests for form interactions, validation, and API calls.
    *   Event/Venue Components (`EventCard.tsx`, `VenueList.tsx`, `EventDetailBooking.tsx`, etc.): Tests for rendering, basic interactions.
    *   Payment Components (`CheckoutPage.tsx`, `CheckoutForm.tsx`, `PaymentStatusPage.tsx`): Comprehensive tests covering Stripe Elements loading, form submission, API calls, error handling, and rendering of payment status.
*   **Contexts (`AuthContext.tsx`):** Tests for context provider logic and state changes.
*   **Cypress E2E Tests (existing, from file structure):**
    *   `event_booking_flow.cy.ts`
    *   `event_create.cy.ts`, `event_edit.cy.ts`
    *   `user_registration.cy.ts`
    *   `venue_create.cy.ts`, `venue_edit.cy.ts`
    *   `venues_list.cy.ts`
    *   (Status unknown due to execution blockage)

### 2.2. Identified Gaps & Proposed New Tests (Frontend)

*   **Unit/Component Tests:**
    *   **Email Notification Related UI:** If any UI components are added to manage email preferences or display email-related statuses, they will need tests.
    *   **Error Boundary Components:** Test error boundary components to ensure they catch errors and render fallback UI.
    *   **Complex State Logic:** Components with complex local state or interactions may need more granular tests.
*   **Integration Tests (Jest/RTL):**
    *   Test interactions between multiple components, e.g., a filter component updating a list component.
    *   Test full form submission flows within components, mocking context providers and API calls.
*   **End-to-End Tests (Cypress):**
    *   **Payment Flow with Stripe:** A full E2E test for the payment flow, interacting with (mocked or test mode) Stripe Elements. This is critical.
    *   **Email Confirmation E2E (Conceptual):** If possible with tools like MailHog API in a test environment, E2E tests could check if registration or booking emails are sent (though content verification is hard E2E).
    *   **Role-Based UI Elements:** E2E tests to verify that users with different roles (e.g., admin, event organizer, regular user) see the correct UI elements and have the correct permissions on the frontend.
    *   **Edge Cases and Error States:** E2E tests for network errors, API errors, and how the frontend handles them.

## 3. CI/CD Test Execution

*   The `.github/workflows/ci.yml` file has been updated to:
    *   Use Poetry for backend dependency installation and test execution (`poetry run pytest`).
    *   Use `npm ci` for frontend dependency installation.
    *   Run frontend tests using `npm test`.
    *   Include `npm audit` for vulnerability scanning in the frontend.
*   **Current Blocker:** The sandbox environment prevents successful execution of these test commands. In a stable CI environment, these configurations should allow tests to run.

This document should be updated as test coverage improves and new features are added.
