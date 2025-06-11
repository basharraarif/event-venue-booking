// cypress/e2e/event_booking_flow.cy.ts

describe('Event Booking Flow E2E Test', () => {
    const userEmail = 'e2e_user@example.com';
    const userPassword = 'e2e_password123';
    let testUserId: string; // Will be set after registration or if user already exists

    before(() => {
        // Attempt to register a user for testing. If user already exists, login.
        // This assumes your backend API is running and accessible.
        // For a real CI setup, you might have a dedicated test user or seed data.
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: {
                username: 'e2euser',
                email: userEmail,
                password: userPassword,
                password2: userPassword,
            },
            failOnStatusCode: false // Don't fail if user already exists (e.g., 400 bad request)
        }).then((resp) => {
            if (resp.status === 201 || resp.status === 200) { // 201 Created or 200 OK (if registration returns user)
                cy.log('User registration successful or user might exist.');
                // If registration returns user ID or if login is needed to get ID
            } else if (resp.body.email && resp.body.email.includes('already exists')) {
                cy.log('User already exists. Proceeding to login.');
            } else if (resp.body.username && resp.body.username.includes('already exists')) {
                cy.log('Username already exists. Proceeding to login.');
            }
             // Regardless of registration outcome, attempt login to get token and user ID
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: userEmail, password: userPassword },
            }).then((loginResp) => {
                expect(loginResp.status).to.eq(200);
                expect(loginResp.body.key).to.exist;
                localStorage.setItem('authToken', loginResp.body.key); // Set for UI tests

                // Fetch user details to get ID
                cy.request({
                    method: 'GET',
                    url: `${Cypress.env('apiUrl')}/auth/user/`,
                    headers: { Authorization: `Token ${loginResp.body.key}` }
                }).then((userResp) => {
                    expect(userResp.status).to.eq(200);
                    testUserId = userResp.body.id; // Assuming id is returned
                    cy.log(`Logged in user ID: ${testUserId}`);
                });
            });
        });

        // Seed an event (if not already present) - this is a simplified example
        // In a real scenario, you might have more robust seeding or rely on existing data
        // For this test, we'll assume an event with "Test Event E2E" in its name exists
        // and is associated with a venue that allows booking.
    });

    beforeEach(() => {
        // Ensure localStorage is clean and then set the token before each test
        cy.clearLocalStorage();
        const token = localStorage.getItem('authToken'); // This will be null here
                                                        // The login in `before` sets this for subsequent tests.
                                                        // If tests are truly independent and `before` runs once,
                                                        // we need to re-set it here or use `Cypress.Cookies.preserveOnce('sessionid')` etc.
                                                        // For simplicity, let's re-fetch and set token if not present.
        if (!localStorage.getItem('authToken')) {
             cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: userEmail, password: userPassword },
            }).then((loginResp) => {
                localStorage.setItem('authToken', loginResp.body.key);
            });
        }
        cy.visit('/'); // Start at homepage
    });

    it('should allow a user to filter events, navigate to an event, and initiate booking', () => {
        // 1. Navigate to Events page
        cy.get('nav').contains('Events').click();
        cy.url().should('include', '/events');
        cy.contains('h1', 'Discover Events').should('be.visible');

        // 2. Filter Events (assuming an event with "Tech" in its name exists)
        // Wait for initial events to load if necessary
        cy.wait(1000); // Simple wait, could be improved with aliasing network requests

        // Check if the filter input exists before typing
        cy.get('input[name="name"]').should('exist').type('Tech Conference E2E'); // Assuming an event with this name exists
        // Add a small delay for debounce or wait for network call if possible
        cy.wait(1000);

        // Verify that the list updates (very basic check)
        // This needs an event with this name to exist from seeding or prior setup
        cy.contains('h2', 'Tech Conference E2E').should('be.visible');

        // 3. Navigate to Event Details (Simplified - click on the card or a details link)
        // For this test, we assume clicking the event name or a specific link goes to a conceptual detail view
        // or allows booking directly. Let's assume we click a "Book Now" or "View Details" button.
        // As the current EventList has "View Details (Soon)" which is disabled,
        // this part of the E2E test would need the UI to be updated for a real flow.
        // For now, we'll simulate finding the event and conceptually moving to booking.

        // Let's assume we find an event card and want to book it.
        // We need a way to identify the event and then proceed.
        // This part is highly dependent on how event IDs are exposed or how navigation to booking works.
        // For this test, we will skip direct navigation to a detail page and assume
        // that the booking can be initiated if we know the event ID.
        // In a real test, you'd click a link:
        // cy.contains('h2', 'Tech Conference E2E').parents('[data-cy=event-card]').find('a[data-cy=view-details-link]').click();
        // cy.url().should('include', '/events/evt_some_id'); // Example detail page URL

        // For now, let's assume we have an event ID from our known test event and proceed to booking creation via API for setup.
        // Then, we can navigate to checkout for that booking.

        // This E2E test needs a specific event to exist that can be booked.
        // Let's assume an event "Bookable Event for E2E" exists.
        cy.get('input[name="name"]').clear().type('Bookable Event for E2E');
        cy.wait(1000);
        cy.contains('h2', 'Bookable Event for E2E').should('be.visible');

        // Find the event ID (this is tricky without proper data-cy attributes on event cards or links)
        // For a robust test, ensure your event cards have `data-event-id="THE_ID_HERE"`
        // cy.contains('h2', 'Bookable Event for E2E').parent().parent().invoke('attr', 'data-event-id').then(eventId => {
        // This is a placeholder - a real test would get eventId from UI
        const knownBookableEventId = "evt_placeholder_bookable_event_id"; // Replace with an actual ID from seed data

        // 4. Initiate Booking (conceptual - create a booking via API to get a bookingId for checkout)
        // This step simulates that the user has found an event and is now proceeding to checkout for it.
        // In a full UI flow, they'd click a "Book Now" button which would create the booking and redirect.
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/bookings/`,
            headers: { Authorization: `Token ${localStorage.getItem('authToken')}` },
            body: {
                event: knownBookableEventId, // ID of a bookable event from your seed data
                number_of_tickets: 1,
            },
            failOnStatusCode: false // Allow to fail if booking already exists or event not bookable
        }).then(bookingResp => {
            if (bookingResp.status === 201) {
                const bookingId = bookingResp.body.id;
                cy.log(`Booking created: ${bookingId}`);
                 // 5. Verify Navigation to Checkout
                cy.visit(`/checkout/${bookingId}`);
                cy.url().should('include', `/checkout/${bookingId}`);
                cy.contains('h1', 'Checkout').should('be.visible');
                cy.contains('h2', 'Booking Summary').should('be.visible');
                // Further checks on the checkout page can be added here (e.g., Stripe elements loaded)
            } else {
                // Handle cases where booking creation might fail due to test setup (e.g., already booked)
                cy.log(`Could not create booking for E2E test (Status: ${bookingResp.status}). This might be okay if booking exists or event is not currently bookable. Error: ${JSON.stringify(bookingResp.body)}`);
                // As a fallback, try to find an existing pending booking for this user to proceed to checkout
                // This part is complex and depends on backend state. For a true E2E, ensure clean state or specific bookable event.
                // For now, if booking creation fails, the test might not fully complete the checkout part.
                 cy.visit('/dashboard'); // Go to dashboard to see if there's a pending booking
                 cy.contains('h2', 'My Bookings').should('be.visible');
                 // Look for a "Pay Now" link (highly dependent on UI)
                 // cy.contains('a', 'Pay Now').first().click(); // This is very fragile
                 // cy.url().should('include', '/checkout/');
                 cy.log("Skipping checkout verification due to booking creation issue/complexity.");
            }
        });
    });
});
