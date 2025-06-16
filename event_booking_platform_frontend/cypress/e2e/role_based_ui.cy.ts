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
                    cy.request({
                        method: 'GET',
                        url: `${Cypress.env('apiUrl')}/auth/user/`,
                        headers: { Authorization: `Token ${user.token}` }
                    }).then(userResp => {
                        user.id = userResp.body.id;
                        // Placeholder for actual role assignment via API if available in a real test setup
                        // For now, roles are assumed to be assigned based on user type during backend setup or via a separate mechanism.
                        // If backend allows role modification via API and this user (e.g. admin) has rights:
                        // cy.request({ method: 'PATCH', url: `${Cypress.env('apiUrl')}/users/${user.id}/assign-role/`, headers: { Authorization: `Token ${users.admin.token}` }, body: {role: role} });
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

            // Admin creates a general venue for other tests
            cy.request({
                method: 'POST', url: `${Cypress.env('apiUrl')}/venues/`,
                headers: { Authorization: `Token ${users.admin.token}` },
                body: { name: 'Admin General Venue', address: '789 Admin St', capacity: 200, owner: users.admin.id }
            }).then(venueResp => {
                venueByAdminId = venueResp.body.id;

                // Event Organizer creates their own event
                cy.request({
                    method: 'POST', url: `${Cypress.env('apiUrl')}/events-management/`,
                    headers: { Authorization: `Token ${users.eventOrganizer.token}` },
                    body: { name: 'EO Own Event', venue: venueByAdminId, ticket_price: '20.00', organizer: users.eventOrganizer.id,
                            start_time: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
                            end_time: new Date(Date.now() + 74 * 60 * 60 * 1000).toISOString() }
                }).then(resp => { eventByEOId = resp.body.id; });

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
    });

    const loginAs = (userKey: keyof typeof users) => {
        const user = users[userKey];
        localStorage.setItem('authToken', user.token);
        // localStorage.setItem('userRoles', JSON.stringify([userKey])); // Simplified role storage for frontend
        cy.visit('/');
        cy.window().its('appContext').invoke('login', { user: { id: user.id, username: user.username, email: user.email, roles: [userKey] }, token: user.token });
        cy.visit('/'); // Re-visit to ensure state is applied
    };

    context('Admin User UI and Permissions', () => {
        beforeEach(() => {
            loginAs('admin');
        });

        it('should see admin-specific UI elements and access admin pages', () => {
            cy.get('nav').should('contain.text', users.admin.username);
            cy.get('nav a[href="/dashboard/admin"]').should('be.visible'); // Generic admin dashboard link

            cy.visit(`/events/${eventByEOId}`); // Visit event created by EO
            cy.contains('h2', 'EO Own Event').should('be.visible');
            cy.contains('button', /edit event/i).should('be.visible'); // Admin can edit any event
            cy.contains('button', /delete event/i).should('be.visible');


            cy.visit(`/venues/${venueByVMId}`); // Visit venue created by VM
            cy.contains('h2', 'VM Own Venue').should('be.visible');
            cy.contains('button', /edit venue/i).should('be.visible'); // Admin can edit any venue
            cy.contains('button', /delete venue/i).should('be.visible');
        });
    });

    context('Event Organizer UI and Permissions', () => {
        beforeEach(() => {
            loginAs('eventOrganizer');
        });

        it('should see UI for managing own events but not venues', () => {
            cy.get('nav').should('contain.text', users.eventOrganizer.username);
            cy.get('nav a[href="/dashboard/organizer/events/new"]').should('be.visible'); // Link to create new event
            cy.get('nav a[href="/dashboard/manager/venues/new"]').should('not.exist'); // No link to create new venue

            // Visit own event
            cy.visit(`/events/${eventByEOId}`);
            cy.contains('h2', 'EO Own Event').should('be.visible');
            cy.contains('button', /edit event/i).should('be.visible');
            cy.contains('button', /delete event/i).should('be.visible');


            // Visit admin's event (someone else's event)
            cy.visit(`/events/${eventByAdminId}`);
            cy.contains('h2', 'Admin General Event').should('be.visible');
            cy.contains('button', /edit event/i).should('not.exist');
            cy.contains('button', /delete event/i).should('not.exist');


            // Attempt to navigate to venue creation page
            cy.visit('/dashboard/manager/venues/new', { failOnStatusCode: false });
            cy.url().should('not.include', '/dashboard/manager/venues/new');
            cy.contains(/access denied|please login/i).should('be.visible'); // Or other permission error message
        });
    });

    context('Venue Manager UI and Permissions', () => {
        beforeEach(() => {
            loginAs('venueManager');
        });

        it('should see UI for managing own venues but not events', () => {
            cy.get('nav').should('contain.text', users.venueManager.username);
            cy.get('nav a[href="/dashboard/manager/venues/new"]').should('be.visible'); // Link to create new venue
            cy.get('nav a[href="/dashboard/organizer/events/new"]').should('not.exist'); // No link to create new event

            // Visit own venue
            cy.visit(`/venues/${venueByVMId}`);
            cy.contains('h2', 'VM Own Venue').should('be.visible');
            cy.contains('button', /edit venue/i).should('be.visible');
            cy.contains('button', /delete venue/i).should('be.visible');


            // Visit admin's venue
            cy.visit(`/venues/${venueByAdminId}`);
            cy.contains('h2', 'Admin General Venue').should('be.visible');
            cy.contains('button', /edit venue/i).should('not.exist');
            cy.contains('button', /delete venue/i).should('not.exist');


            // Attempt to navigate to event creation page
            cy.visit('/dashboard/organizer/events/new', { failOnStatusCode: false });
            cy.url().should('not.include', '/dashboard/organizer/events/new');
            cy.contains(/access denied|please login/i).should('be.visible');
        });
    });

    context('Regular Customer UI and Permissions', () => {
        beforeEach(() => {
            loginAs('customer');
        });

        it('should not see admin/management UI elements and access only own data', () => {
            cy.get('nav').should('contain.text', users.customer.username);
            cy.get('nav a[href="/dashboard/admin"]').should('not.exist');
            cy.get('nav a[href="/dashboard/organizer/events/new"]').should('not.exist');
            cy.get('nav a[href="/dashboard/manager/venues/new"]').should('not.exist');
            cy.get('nav a[href="/dashboard/my-bookings"]').should('be.visible');

            cy.visit(`/events/${eventByEOId}`);
            cy.contains('h2', 'EO Own Event').should('be.visible');
            cy.contains('button', /edit event/i).should('not.exist'); // No edit button for events
            cy.contains('button', /delete event/i).should('not.exist');


            cy.visit(`/venues/${venueByVMId}`);
            cy.contains('h2', 'VM Own Venue').should('be.visible');
            cy.contains('button', /edit venue/i).should('not.exist'); // No edit button for venues
            cy.contains('button', /delete venue/i).should('not.exist');


            cy.visit('/dashboard/my-bookings');
            cy.contains('h1', /my bookings/i).should('be.visible');
            // Further checks if there are bookings for this user can be added here.
            // For now, just checking page access and visibility.
        });
    });
});
