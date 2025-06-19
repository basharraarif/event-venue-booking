# Stripe Checkout Manual Testing Plan

This document outlines the manual testing plan for the Stripe checkout integration in the Event Booking Platform.

## Prerequisites

1.  **Backend Server Running:** The Django backend server must be running and accessible, with Stripe API keys (test mode) correctly configured.
2.  **Frontend Server Running:** The frontend application (e.g., React, Vue, Angular) must be running and able to communicate with the backend.
3.  **User Accounts:**
    - At least one registered and logged-in user account is required to make bookings.
    - Ensure the user has a verified email if required by the platform's settings.
4.  **Events Requiring Payment:**
    - At least one event must be created in the system that has a ticket price greater than 0.
    - This event should be active and available for booking.
5.  **Test Stripe Account:** Access to the Stripe dashboard (test mode) to view payment intents, payments, and customer objects to verify backend operations.
6.  **Stripe Test Cards:** A list of Stripe's test card numbers for various scenarios (successful payment, failed payment, 3D Secure, etc.). Refer to Stripe's official documentation for the most up-to-date test card numbers.

## Test Scenarios

---

### 1. Successful Payment

- **Objective:** Verify that a user can successfully pay for a booking and the booking status is updated.
- **Steps:**
  1.  Log in to the frontend application as a registered user.
  2.  Navigate to the events page and select an event that requires payment.
  3.  Attempt to book a ticket for the event.
  4.  Confirm the booking details. The booking status should initially be 'pending_payment' (or similar).
  5.  Proceed to the payment page/Stripe Checkout.
  6.  Enter a valid Stripe test card number for successful payments (e.g., `4242 4242 4242 4242` with any valid CVC/expiry).
  7.  Complete the Stripe Checkout process.
- **Expected Results:**
  - **UI:**
    - User is redirected to a success page or shown a success message.
    - The booking details page should show the booking status updated to 'confirmed' or 'paid'.
  - **Backend:**
    - A Stripe PaymentIntent should be created and marked as 'succeeded'.
    - A corresponding payment record should be created in the database, linked to the booking.
    - The booking status in the database should be updated from 'pending_payment' to 'confirmed' (or equivalent).
    - An email confirmation (if implemented) might be sent to the user.
  - **Stripe Dashboard:**
    - A successful payment and charge should be visible.
    - A customer object might be created or updated for the user.

---

### 2. Payment Failure: Insufficient Funds

- **Objective:** Verify that the system correctly handles a payment decline due to insufficient funds.
- **Steps:**
  1.  Log in to the frontend application.
  2.  Create a booking for a paid event to reach the 'pending_payment' status.
  3.  Proceed to Stripe Checkout.
  4.  Enter a Stripe test card number that simulates insufficient funds (refer to Stripe documentation).
  5.  Attempt to complete the payment.
- **Expected Results:**
  - **UI:**
    - Stripe Checkout should display an appropriate error message (e.g., "Your card has insufficient funds.").
    - The user should remain on the payment page or be redirected to a payment failure page.
    - An option to try payment again with a different card might be available.
    - The booking status on the UI should remain 'pending_payment'.
  - **Backend:**
    - The Stripe PaymentIntent should be marked as 'requires_payment_method' or reflect the failure.
    - The booking status in the database should remain 'pending_payment'.
    - No new successful payment record should be created for this attempt.
  - **Stripe Dashboard:**
    - A failed payment attempt should be visible, with the reason noted as insufficient funds.

---

### 3. Payment Failure: Generic Decline

- **Objective:** Verify that the system correctly handles a generic card decline.
- **Steps:**
  1.  Log in to the frontend application.
  2.  Create a booking for a paid event to reach the 'pending_payment' status.
  3.  Proceed to Stripe Checkout.
  4.  Enter a Stripe test card number that simulates a generic decline (refer to Stripe documentation, e.g., a card specifically for declines).
  5.  Attempt to complete the payment.
- **Expected Results:**
  - **UI:**
    - Stripe Checkout should display a generic error message (e.g., "Your card was declined.").
    - The user should remain on the payment page or be redirected to a payment failure page.
    - The booking status on the UI should remain 'pending_payment'.
  - **Backend:**
    - The Stripe PaymentIntent should reflect the failed status.
    - The booking status in the database should remain 'pending_payment'.
  - **Stripe Dashboard:**
    - A failed payment attempt should be visible with the reason "Generic decline" or similar.

---

### 4. Payment Requiring 3D Secure Authentication

- **Objective:** Verify the handling of payments that require 3D Secure (SCA) authentication.
- **Steps:**
  1.  Log in to the frontend application.
  2.  Create a booking for a paid event to reach the 'pending_payment' status.
  3.  Proceed to Stripe Checkout.
  4.  Enter a Stripe test card number that simulates a requirement for 3D Secure authentication (refer to Stripe documentation).
  5.  Stripe Checkout should present a mock 3D Secure authentication modal/window.
  6.  Successfully complete the mock authentication (e.g., by clicking "Complete Authentication" or similar button provided by Stripe's test environment).
- **Expected Results:**

  - **UI:**
    - After successful 3D Secure authentication, the payment should proceed.
    - User is redirected to a success page or shown a success message.
    - The booking details page should show the booking status updated to 'confirmed' or 'paid'.
  - **Backend:**
    - The Stripe PaymentIntent should be 'succeeded' after authentication.
    - A payment record should be created and the booking status updated to 'confirmed'.
  - **Stripe Dashboard:**
    - The payment should be visible and marked as successful, potentially indicating it went through 3D Secure.

- **Sub-Scenario: 3D Secure Authentication Failure**
  - **Steps:**
    1.  Follow steps 1-4 above.
    2.  In the mock 3D Secure authentication modal, choose to fail the authentication (if Stripe's test environment provides such an option).
  - **Expected Results:**
    - **UI:** Stripe Checkout should display an authentication failed message. The user remains on the payment page. Booking status remains 'pending_payment'.
    - **Backend:** PaymentIntent status reflects the authentication failure. Booking status remains 'pending_payment'.
    - **Stripe Dashboard:** Payment attempt shows authentication failure.

---

### 5. Attempting to Pay for a Booking Not in 'Pending Payment' Status

- **Objective:** Verify that the system prevents payment attempts for bookings that are not in a state expecting payment (e.g., already confirmed, cancelled, or expired).
- **Steps:**
  1.  **Scenario A: Confirmed Booking**
      a. Successfully complete a booking and payment for an event.
      b. Try to access the payment URL/initiate payment for this already confirmed booking again (e.g., through browser history or a direct link if guessable, or if the UI mistakenly allows it).
  2.  **Scenario B: Cancelled Booking**
      a. Book an event and then cancel it (if cancellation is possible before payment).
      b. Attempt to initiate payment for this cancelled booking.
- **Expected Results:**
  - **UI:**
    - The user should be shown an appropriate message (e.g., "This booking does not require payment," "Booking already confirmed," "Booking cancelled," or "Invalid booking state").
    - The user should NOT be redirected to Stripe Checkout.
    - Alternatively, if redirected to a generic payment page, that page should detect the invalid state and prevent proceeding to Stripe.
  - **Backend:**
    - The backend should validate the booking status before creating/processing a Stripe PaymentIntent.
    - If the booking is not in 'pending_payment' status, the backend should return an error response.
    - No new PaymentIntent should be created for Stripe.
    - The booking status in the database should remain unchanged (e.g., 'confirmed' or 'cancelled').

---

### 6. Handling of Network Errors

- **Objective:** Verify graceful handling of network issues during the payment process.
- **Sub-Scenario 6.1: Network Error During Payment Intent Creation**

  - **Steps:**
    1.  Log in and select an event for booking.
    2.  Before clicking the button that initiates payment (which calls the backend to create a PaymentIntent):
        - Simulate a network disconnection (e.g., turn off Wi-Fi, use browser developer tools to go offline).
    3.  Click the "Proceed to Payment" button.
  - **Expected Results:**
    - **UI:**
      - An informative error message should be displayed (e.g., "Network error. Please check your connection and try again.").
      - The user should not be redirected to a broken Stripe page.
      - The application should remain in a stable state.
    - **Backend:**
      - The request to create the PaymentIntent will fail; no PaymentIntent is created on Stripe's side.
      - Booking status remains 'pending_payment' or whatever it was before the attempt.
  - **Steps (Post-Error):**
    1.  Restore the network connection.
    2.  Attempt to proceed to payment again.
  - **Expected Results (Post-Error):**
    - The payment process should now proceed normally (leading to successful payment or other defined scenarios).

- **Sub-Scenario 6.2: Network Error After Stripe Checkout Redirect, Before Payment Confirmation Callback**
  - **Note:** This is harder to test manually but consider the implications. The payment might go through on Stripe's side, but the frontend might not receive immediate confirmation.
  - **Conceptual Steps (if testable):**
    1.  Initiate payment and get redirected to Stripe Checkout.
    2.  Enter card details.
    3.  Before Stripe redirects back to your site's success/failure URL, simulate a network disconnection for the client.
    4.  Complete payment on Stripe's side (if it allows).
  - **Expected Results:**
    - **UI (upon network restoration):**
      - The application should ideally have a mechanism (e.g., when the user revisits the booking or the page is refreshed) to re-check the booking status from the backend.
      - If payment was successful (verified by backend checking with Stripe via webhooks or direct API calls), the UI should reflect the 'confirmed' status.
      - If payment failed or is indeterminate from the frontend's perspective, it might show 'pending_payment' or an option to check status.
    - **Backend:**
      - Relies heavily on Stripe Webhooks to update the booking status reliably, irrespective of frontend connectivity during the callback.
      - The booking status should accurately reflect the payment outcome received via webhook.
  - **Verification:**
    - Check Stripe Dashboard for payment status.
    - Check backend database for booking status and payment record after webhook processing time.

## Notes

- **Stripe Test Card Numbers:** Always refer to the official Stripe documentation for the most current list of test card numbers: [https://stripe.com/docs/testing](https://stripe.com/docs/testing)
  - General Success: `4242 4242 4242 4242` (any future date, any 3-digit CVC)
  - Cards for specific declines (e.g., insufficient funds, card declined)
  - Cards for 3D Secure / SCA
- **Backend Logs:** Monitor backend server logs for any errors or unexpected behavior during testing.
- **Browser Console:** Monitor the browser's developer console for frontend errors or warnings.
- **Webhook Delays:** Be aware that webhook delivery can have slight delays. When verifying backend status changes that depend on webhooks, allow a reasonable amount of time. Consider using the Stripe CLI to monitor webhook events locally during development.
- **Idempotency:** Test creating a booking and initiating payment, then abandoning it, and trying to pay for the _same_ booking again. The system should ideally use the existing PaymentIntent or handle it gracefully.
- **Currency:** Ensure tests are conducted with the currency configured for the event/platform. Stripe test cards generally work across currencies.

This testing plan should be updated as new features are added or existing checkout flows are modified.
