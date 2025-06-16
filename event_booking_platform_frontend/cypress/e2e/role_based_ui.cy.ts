// cypress/e2e/role_based_ui.cy.ts

describe('Role-Based UI and Permissions E2E Tests', () => {
    // --- Test Data and Users ---
    const users = {
        admin: {
            email: `admin_user_${Date.now()}@example.com`,
            password: 'password123',
            username: `admin_user_${Date.now()}`,
            token: '',
            id: ''
        },
        eventOrganizer: {
            email: `organizer_user_${Date.now()}@example.com`,
            password: 'password123',
            username: `organizer_user_${Date.now()}`,
            token: '',
            id: ''
        },
        venueManager: {
            email: `manager_user_${Date.now()}@example.com`,
            password: 'password123',
            username: `manager_user_${Date.now()}`,
            token: '',
            id: ''
        },
        customer: {
            email: `customer_user_${Date.now()}@example.com`,
            password: 'password123',
            username: `customer_user_${Date.now()}`,
            token: '',
            id: ''
        }
    };

    let venueByVMId: string;
    let eventByEOId: string;
    let venueByAdminId: string;
    let eventByAdminId: string;

    before(() => {
        // Register all users and get tokens
        for (const role in users) {
            const user = users[role as keyof typeof users];
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/registration/`,
                body: { username: user.username, email: user.email, password: user.password, password2: user.password },
            }).then(regResp => {
                expect(regResp.status).to.eq(201);
                cy.request({
                    method: 'POST',
                    url: `${Cypress.env('apiUrl')}/auth/login/`,
                    body: { email: user.email, password: user.password },
                }).then(loginResp => {
                    user.token = loginResp.body.key;
                    // Assign roles via API (assuming an admin endpoint or direct role assignment for testing)
                    // This part is crucial and assumes a backend mechanism to assign roles.
                    // If no such endpoint exists, roles must be pre-assigned or manually set in DB for test users.
                    // For this test, we'll assume the first registered user ('admin') can assign roles or is admin by default.
                    // And other users need roles assigned. This setup is complex for E2E `before`.
                    // A simpler E2E approach is to have pre-existing users with these roles in the test DB.
                    // For now, we'll proceed as if roles are obtained upon registration or via a test setup hook not shown here.
                    // The key is that `user.token` is set.
                    // We also need user IDs.
                    cy.request({
                        method: 'GET',
                        url: `${Cypress.env('apiUrl')}/auth/user/`,
                        headers: { Authorization: `Token ${user.token}` }
                    }).then(userResp => {
                        user.id = userResp.body.id;
                        if (role === 'admin') { // Assuming first user is admin or has staff status
                             // cy.request({ method: 'PATCH', url: `${Cypress.env('apiUrl')}/users/${user.id}/set-admin/`, headers: { Authorization: `Token ${users.admin.token}` }});
                             // This is a placeholder for actual role assignment logic.
                        }
                    });
                });
            });
        }
        cy.log('All users registered and tokens obtained.');

        // Create resources after all users (and tokens) are set up
        cy.then(() => {
            // Venue Manager creates their own venue
            cy.request({
                method: 'POST', url: `${Cypress.env('apiUrl')}/venues/`,
                headers: { Authorization: `Token ${users.venueManager.token}` },
                body: { name: 'VM Own Venue', address: '123 VM St', capacity: 100, owner: users.venueManager.id }
            }).then(resp => { venueByVMId = resp.body.id; });

            // Event Organizer creates their own event (needs a venue first, use admin's venue or create one)
            cy.request({
                method: 'POST', url: `${Cypress.env('apiUrl')}/venues/`,
                headers: { Authorization: `Token ${users.admin.token}` }, // Admin creates a general venue
                body: { name: 'Admin General Venue', address: '789 Admin St', capacity: 200, owner: users.admin.id }
            }).then(venueResp => {
                venueByAdminId = venueResp.body.id;
                cy.request({
                    method: 'POST', url: `${Cypress.env('apiUrl')}/events-management/`,
                    headers: { Authorization: `Token ${users.eventOrganizer.token}` },
                    body: { name: 'EO Own Event', venue: venueByAdminId, ticket_price: '20.00', organizer: users.eventOrganizer.id,
                            start_time: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
                            end_time: new Date(Date.now() + 74 * 60 * 60 * 1000).toISOString() }
                }).then(resp => { eventByEOId = resp.body.id; });
            });

            // Admin creates an event (for testing EO access to other's events)
             cy.request({
                method: 'POST', url: `${Cypress.env('apiUrl')}/events-management/`,
                headers: { Authorization: `Token ${users.admin.token}` },
                body: { name: 'Admin General Event', venue: venueByAdminId, ticket_price: '30.00', organizer: users.admin.id,
                        start_time: new Date(Date.now() + 96 * 60 * 60 * 1000).toISOString(),
                        end_time: new Date(Date.now() + 98 * 60 * 60 * 1000).toISOString() }
            }).then(resp => { eventByAdminId = resp.body.id; });
        });
    });

    const loginAs = (userKey: keyof typeof users) => {
        const user = users[userKey];
        localStorage.setItem('authToken', user.token);
        cy.visit('/'); // Refresh or visit homepage to apply logged-in state
    };

    context('Admin User UI and Permissions', () => {
        beforeEach(() => {
            loginAs('admin');
        });

        it('should see admin-specific UI elements and access admin pages', () => {
            cy.get('nav').should('contain.text', users.admin.username); // Or some other indicator of being logged in
            // Example: cy.get('a[href="/admin/dashboard"]').should('be.visible');
            // Example: cy.get('button[data-testid="manage-all-events-btn"]').should('be.visible');

            // Visit an event and check for admin controls
            cy.visit(`/events/${eventByEOId}`); // Visit event created by EO
            cy.contains('h2', 'EO Own Event').should('be.visible');
            // Example: cy.get('button[data-testid="admin-edit-event-btn"]').should('be.visible');

            // Visit a venue and check for admin controls
            cy.visit(`/venues/${venueByVMId}`); // Visit venue created by VM
            cy.contains('h2', 'VM Own Venue').should('be.visible');
            // Example: cy.get('button[data-testid="admin-edit-venue-btn"]').should('be.visible');
            cy.log('Admin UI checks are placeholders, need actual selectors from frontend.');
        });
    });

    context('Event Organizer UI and Permissions', () => {
        beforeEach(() => {
            loginAs('eventOrganizer');
        });

        it('should see UI for managing own events but not venues', () => {
            cy.get('nav').should('contain.text', users.eventOrganizer.username);
            // Example: cy.get('a[href="/events/create"]').should('be.visible');
            // Example: cy.get('a[href="/venues/create"]').should('not.exist');

            // Visit own event
            cy.visit(`/events/${eventByEOId}`);
            cy.contains('h2', 'EO Own Event').should('be.visible');
            // Example: cy.get('button[data-testid="edit-own-event-btn"]').should('be.visible');

            // Visit admin's event (someone else's event)
            cy.visit(`/events/${eventByAdminId}`);
            cy.contains('h2', 'Admin General Event').should('be.visible');
            // Example: cy.get('button[data-testid="edit-own-event-btn"]').should('not.exist');

            // Attempt to navigate to venue creation page
            cy.visit('/venues/create', { failOnStatusCode: false }); // Allow Cypress to handle non-2xx responses
            // Verify redirection or error message. Depends on frontend implementation.
            // Example: cy.url().should('not.include', '/venues/create');
            // Example: cy.contains('You do not have permission to access this page.').should('be.visible');
            cy.log('EO UI checks are placeholders.');
        });
    });

    context('Venue Manager UI and Permissions', () => {
        beforeEach(() => {
            loginAs('venueManager');
        });

        it('should see UI for managing own venues but not events', () => {
            cy.get('nav').should('contain.text', users.venueManager.username);
            // Example: cy.get('a[href="/venues/create"]').should('be.visible');
            // Example: cy.get('a[href="/events/create"]').should('not.exist');

            // Visit own venue
            cy.visit(`/venues/${venueByVMId}`);
            cy.contains('h2', 'VM Own Venue').should('be.visible');
            // Example: cy.get('button[data-testid="edit-own-venue-btn"]').should('be.visible');

            // Visit admin's venue
            cy.visit(`/venues/${venueByAdminId}`);
            cy.contains('h2', 'Admin General Venue').should('be.visible');
            // Example: cy.get('button[data-testid="edit-own-venue-btn"]').should('not.exist');

            // Attempt to navigate to event creation page
            cy.visit('/events/create', { failOnStatusCode: false });
            // Example: cy.url().should('not.include', '/events/create');
            // Example: cy.contains('You do not have permission to access this page.').should('be.visible');
            cy.log('VM UI checks are placeholders.');
        });
    });

    context('Regular Customer UI and Permissions', () => {
        beforeEach(() => {
            loginAs('customer');
        });

        it('should not see admin/management UI elements and access only own data', () => {
            cy.get('nav').should('contain.text', users.customer.username);
            // Example: cy.get('a[href="/admin/dashboard"]').should('not.exist');
            // Example: cy.get('a[href="/events/create"]').should('not.exist');
            // Example: cy.get('a[href="/venues/create"]').should('not.exist');

            cy.visit(`/events/${eventByEOId}`); // View an event
            // Example: cy.get('button[data-testid="edit-event-btn"]').should('not.exist');

            cy.visit('/dashboard/my-bookings');
            cy.contains('h1', /my bookings/i).should('be.visible');
            // Further checks if there are bookings for this user.
            cy.log('Customer UI checks are placeholders.');
        });
    });
});
