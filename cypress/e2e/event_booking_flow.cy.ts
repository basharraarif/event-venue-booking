// cypress/e2e/event_booking_flow.cy.ts

describe('Event Booking Flow with Capacity Checks E2E Test', () => {
    const userEmail = 'e2e_capacity_user@example.com';
    const userPassword = 'e2e_password123';
    let authToken: string;
    let venueId: string;

    // Event IDs to be set by API calls
    let limitedCapacityEventId: string;
    let soldOutEventId: string;
    let highCapacityEventId: string;

    before(() => {
        // Register or login user
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: { username: 'e2e_capacity_user', email: userEmail, password: userPassword, password2: userPassword },
            failOnStatusCode: false
        }).then(() => {
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: userEmail, password: userPassword },
            }).then((loginResp) => {
                expect(loginResp.status).to.eq(200);
                authToken = loginResp.body.key;

                // Create a venue for the events
                cy.request({
                    method: 'POST',
                    url: `${Cypress.env('apiUrl')}/venues/`,
                    headers: { Authorization: `Token ${authToken}` },
                    body: { name: 'E2E Capacity Test Venue', address: '123 Capacity St', capacity: 100 }
                }).then(venueResp => {
                    venueId = venueResp.body.id;

                    // Create Event with Limited Capacity (e.g., 5 total, 2 active bookings)
                    cy.request({
                        method: 'POST',
                        url: `${Cypress.env('apiUrl')}/events-management/`, // Ensure this is the correct events endpoint
                        headers: { Authorization: `Token ${authToken}` },
                        body: {
                            name: 'E2E Limited Capacity Event', venue: venueId, ticket_price: '10.00',
                            start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
                            end_time: new Date(Date.now() + 26 * 60 * 60 * 1000).toISOString(),
                            max_capacity: 5
                        }
                    }).then(eventResp => {
                        limitedCapacityEventId = eventResp.body.id;
                        // Create some existing bookings to make it partially filled
                        // Ensure backend correctly calculates active_tickets_count including these
                        cy.request({ method: 'POST', url: `${Cypress.env('apiUrl')}/bookings/`, headers: { Authorization: `Token ${authToken}` }, body: { event: limitedCapacityEventId, number_of_tickets: 2 } });
                    });

                    // Create Sold Out Event (e.g., capacity 2, 2 active bookings)
                    cy.request({
                        method: 'POST',
                        url: `${Cypress.env('apiUrl')}/events-management/`,
                        headers: { Authorization: `Token ${authToken}` },
                        body: {
                            name: 'E2E Sold Out Event', venue: venueId, ticket_price: '10.00',
                            start_time: new Date(Date.now() + 48 * 60 * 60 * 1000).toISOString(),
                            end_time: new Date(Date.now() + 50 * 60 * 60 * 1000).toISOString(),
                            max_capacity: 2
                        }
                    }).then(eventResp => {
                        soldOutEventId = eventResp.body.id;
                        // Create bookings to fill capacity
                        cy.request({ method: 'POST', url: `${Cypress.env('apiUrl')}/bookings/`, headers: { Authorization: `Token ${authToken}` }, body: { event: soldOutEventId, number_of_tickets: 1 } });
                        cy.request({ method: 'POST', url: `${Cypress.env('apiUrl')}/bookings/`, headers: { Authorization: `Token ${authToken}` }, body: { event: soldOutEventId, number_of_tickets: 1 } });
                    });

                    // Create "High" Capacity Event (effectively unlimited for small bookings)
                     cy.request({
                        method: 'POST',
                        url: `${Cypress.env('apiUrl')}/events-management/`,
                        headers: { Authorization: `Token ${authToken}` },
                        body: {
                            name: 'E2E High Capacity Event', venue: venueId, ticket_price: '10.00',
                            start_time: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
                            end_time: new Date(Date.now() + 74 * 60 * 60 * 1000).toISOString(),
                            max_capacity: 1000
                        }
                    }).then(eventResp => highCapacityEventId = eventResp.body.id);
                });
            });
        });
    });

    beforeEach(() => {
        localStorage.setItem('authToken', authToken);
        // This E2E test assumes that there's a route like /events/detail-test/:eventId
        // which renders the EventDetailBooking.tsx component for testing purposes.
        // In a real application, this would be your actual event detail page.
        // Example: cy.visit(`/events/${limitedCapacityEventId}`);
    });

    context('Event with Limited Capacity (5 total, 2 pre-booked => 3 available)', () => {
        it('displays correct capacity, validates ticket input, and allows booking within limit', () => {
            if (!limitedCapacityEventId) { this.skip(); }
            // For E2E, we need to ensure EventDetailBooking component is rendered for this event.
            // This might mean visiting a specific page that uses this component.
            // Let's assume such a page is at `/events/book/${eventId}` for this test.
            cy.visit(`/events/book/${limitedCapacityEventId}`);

            cy.contains('h2', 'E2E Limited Capacity Event').should('be.visible');
            // Wait for event data and capacity calculations
            cy.contains(/Max Capacity: 5/, {timeout: 10000}).should('be.visible'); // Increased timeout for data loading
            cy.contains(/Tickets Available: 3/).should('be.visible');

            // Attempt to book more than available
            cy.get('input[name="numberOfTickets"]').clear().type('4');
            cy.contains('Only 3 tickets available.').should('be.visible');
            cy.get('button').contains('Book Tickets').should('be.disabled');

            // Attempt to book valid number of tickets
            cy.get('input[name="numberOfTickets"]').clear().type('2');
            cy.contains('Only 3 tickets available.').should('not.exist');
            cy.get('button').contains('Book Tickets').should('not.be.disabled').click();

            cy.url().should('include', '/checkout/');
        });
    });

    context('Sold Out Event', () => {
        it('displays "Sold Out" and disables booking', () => {
            if (!soldOutEventId) { this.skip(); }
            cy.visit(`/events/book/${soldOutEventId}`);

            cy.contains('h2', 'E2E Sold Out Event').should('be.visible');
            cy.contains(/Max Capacity: 2/, {timeout: 10000}).should('be.visible');
            cy.contains(/Tickets Available: Sold Out/).should('be.visible');

            cy.get('input[name="numberOfTickets"]').should('be.disabled'); // Input field should be disabled
            cy.get('button').contains('Sold Out').should('be.disabled');
        });
    });

    context('Event with High (effectively unlimited for test) Capacity', () => {
        it('allows booking and does not show restrictive messages for small numbers', () => {
            if (!highCapacityEventId) { this.skip(); }
            cy.visit(`/events/book/${highCapacityEventId}`);

            cy.contains('h2', 'E2E High Capacity Event').should('be.visible');
            cy.contains(/Max Capacity: 1000/, {timeout: 10000}).should('be.visible');
            cy.contains(/Tickets Available: 1000/).should('be.visible'); // Assuming no prior bookings for this test event

            cy.get('input[name="numberOfTickets"]').clear().type('5');
            cy.get('button').contains('Book Tickets').should('not.be.disabled').click();
            cy.url().should('include', '/checkout/');
        });
    });
});
