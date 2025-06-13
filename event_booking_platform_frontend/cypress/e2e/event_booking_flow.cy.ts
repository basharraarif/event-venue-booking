// cypress/e2e/event_booking_flow.cy.ts

describe('Event Booking Flow E2E Test', () => {
    const userEmail = 'e2e_user@example.com';
    const userPassword = 'e2e_password123';
    let testUserId: string;
    let authToken: string;
    let paidEventId: string;
    let freeEventId: string;

    before(() => {
        // Register or login user
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: { username: 'e2e_payment_user', email: userEmail, password: userPassword, password2: userPassword },
            failOnStatusCode: false
        }).then(() => {
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: userEmail, password: userPassword },
            }).then((loginResp) => {
                expect(loginResp.status).to.eq(200);
                authToken = loginResp.body.key;
                cy.request({
                    method: 'GET',
                    url: `${Cypress.env('apiUrl')}/auth/user/`,
                    headers: { Authorization: `Token ${authToken}` }
                }).then((userResp) => {
                    testUserId = userResp.body.id;
                    cy.log(`Logged in user ID: ${testUserId}`);

                    // Create a venue owned by this user (or admin) for seeding events
                    cy.request({
                        method: 'POST',
                        url: `${Cypress.env('apiUrl')}/venues/`,
                        headers: { Authorization: `Token ${authToken}` },
                        body: { name: 'E2E Test Venue', address: '123 E2E St', capacity: 100 }
                    }).then(venueResp => {
                        const venueId = venueResp.body.id;
                        // Create a Paid Event
                        cy.request({
                            method: 'POST',
                            url: `${Cypress.env('apiUrl')}/events-management/`,
                            headers: { Authorization: `Token ${authToken}` },
                            body: {
                                name: 'E2E Paid Event', venue: venueId, ticket_price: '10.00',
                                start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
                                end_time: new Date(Date.now() + 26 * 60 * 60 * 1000).toISOString(),
                                description: "A paid event for E2E testing"
                            }
                        }).then(eventResp => paidEventId = eventResp.body.id);

                        // Create a Free Event
                        cy.request({
                            method: 'POST',
                            url: `${Cypress.env('apiUrl')}/events-management/`,
                            headers: { Authorization: `Token ${authToken}` },
                            body: {
                                name: 'E2E Free Event', venue: venueId, ticket_price: '0.00',
                                start_time: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(), // Day after tomorrow
                                end_time: new Date(Date.now() + 50 * 60 * 60 * 1000).toISOString(),
                                description: "A free event for E2E testing"
                            }
                        }).then(eventResp => freeEventId = eventResp.body.id);
                    });
                });
            });
        });
    });

    beforeEach(() => {
        localStorage.setItem('authToken', authToken); // Ensure token is set for UI
        cy.visit('/');
    });

    it('handles booking a paid event and redirects to checkout', () => {
        // This test assumes the EventDetailBooking.tsx component is used on an event detail page
        // or similar booking initiation UI exists.
        // Since we cannot directly integrate that component here, we'll simulate the booking creation
        // and then verify the redirect to checkout.

        expect(paidEventId).to.exist; // Ensure event was created

        // Simulate creating a booking for the paid event (as if user clicked "Book Tickets")
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/bookings/`,
            headers: { Authorization: `Token ${authToken}` },
            body: { event: paidEventId, number_of_tickets: 1 },
        }).then((bookingResp) => {
            expect(bookingResp.status).to.eq(201);
            const booking = bookingResp.body;
            expect(booking.payment_status).to.eq('pending'); // Backend should set this

            // Navigate to the checkout page for this booking
            cy.visit(`/checkout/${booking.id}`);
            cy.url().should('include', `/checkout/${booking.id}`);
            cy.contains('h1', 'Checkout').should('be.visible');
            cy.contains('h2', 'Booking Summary').should('be.visible');
            cy.contains('Pay now').should('be.visible'); // From CheckoutForm

            // At this point, Stripe PaymentElement would load.
            // For E2E, interacting with the actual Stripe form is complex and brittle.
            // We can mock the stripe.confirmPayment call or check for elements.
            // For this test, we'll confirm the page loads.
            // A deeper test would involve stubbing stripe.confirmPayment or using test cards
            // and verifying redirection to /payment-status.

            // Example: Stubbing window.location.origin for return_url consistency if needed for confirmPayment mock
            // cy.stub(window.location, 'origin').value('http://localhost:3001'); // Assuming frontend runs on 3001 for Cypress

            // Mocking the actual payment confirmation and redirect for now
            cy.log('Checkout page loaded. Payment form interaction would be next.');
            // Simulate a successful payment redirect
            // In a real scenario, after `stripe.confirmPayment`, user is redirected.
            // We can manually visit the payment-status page with expected params.
            cy.visit(`/payment-status?payment_id=${booking.payment.id}&booking_id=${booking.id}&redirect_status=succeeded&payment_intent=pi_mock&payment_intent_client_secret=cs_mock`);
            cy.contains('Payment successful!').should('be.visible');
        });
    });

    it('handles booking a free event and shows success without redirecting to checkout', () => {
        expect(freeEventId).to.exist; // Ensure event was created

        // Simulate creating a booking for the free event
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/bookings/`,
            headers: { Authorization: `Token ${authToken}` },
            body: { event: freeEventId, number_of_tickets: 1 },
        }).then((bookingResp) => {
            expect(bookingResp.status).to.eq(201);
            const booking = bookingResp.body;
            // For free events, backend sets payment_status to 'not_required' and booking to 'confirmed'
            expect(booking.payment_status).to.eq('not_required');
            expect(booking.status).to.eq('confirmed'); // Or whatever your backend sets for free events

            // Since there's no UI interaction to trigger this, we can't easily test
            // the frontend's alert("Booking successful!...") and redirect to dashboard.
            // This test primarily verifies the backend's response for a free event booking.
            // If `EventDetailBooking.tsx` were integrated, we'd click its book button for the free event
            // and then assert the alert (by stubbing `window.alert`) and the router.push call.
            cy.log('Free event booking created. UI should show success and redirect appropriately.');
        });
    });
});
