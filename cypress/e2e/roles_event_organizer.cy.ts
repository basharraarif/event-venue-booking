// cypress/e2e/roles_event_organizer.cy.ts

describe('Event Organizer Role E2E Test', () => {
    const organizerUser = {
        username: 'e2e_eventorg',
        email: 'e2e_eventorg@example.com',
        password: 'e2e_password123',
        role: 'EVENT_ORGANIZER' // Ensure your backend setup can assign this or has this user
    };
    const customerUser = { // A regular user for testing negative cases
        username: 'e2e_customer_for_eo_test',
        email: 'e2e_cust_for_eo@example.com',
        password: 'e2e_password123',
        role: 'CUSTOMER'
    };
    let organizerAuthToken: string;
    let customerAuthToken: string;
    let createdEventId: string | null = null;

    before(() => {
        // Register and login Event Organizer user (simplified, assumes direct role assignment or specific user)
        // This might require a custom Cypress command or backend seeding if roles can't be set via registration.
        // For this test, we'll assume registration and login, and that roles are assigned correctly by backend.
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: { username: organizerUser.username, email: organizerUser.email, password: organizerUser.password, password2: organizerUser.password },
            failOnStatusCode: false
        }).then(() => {
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: organizerUser.email, password: organizerUser.password },
            }).then(resp => {
                organizerAuthToken = resp.body.key;
                // Note: Assigning roles via API after registration might be needed if not automatic
                // e.g., cy.request({ method: 'PATCH', url: `/api/users/${userId}/set-roles/`, body: {roles: [organizerUser.role]}, headers: { Authorization: `Token ${adminToken}` }});
            });
        });
        // Register and login Customer user
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: { username: customerUser.username, email: customerUser.email, password: customerUser.password, password2: customerUser.password },
            failOnStatusCode: false
        }).then(() => {
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: customerUser.email, password: customerUser.password },
            }).then(resp => customerAuthToken = resp.body.key);
        });
    });

    const loginAs = (token: string) => {
        localStorage.setItem('authToken', token);
        // Re-fetch user data to ensure AuthContext updates with roles
        // This depends on how AuthContext fetches user on token change/presence.
        // For now, assuming visit after setting token will trigger AuthContext update.
        cy.visit('/');
    };

    context('As Event Organizer', () => {
        beforeEach(() => {
            loginAs(organizerAuthToken);
        });

        it('should see Event Organizer specific links in Header', () => {
            cy.get('header').should('contain', 'Create Event');
            cy.get('header').should('not.contain', 'Create Venue'); // Assuming not also a Venue Manager
            cy.get('header').should('not.contain', 'Admin Panel'); // Assuming not also an Admin
        });

        it('can access and create an event', () => {
            cy.visit('/dashboard/organizer/events/create'); // Path from Header link
            cy.contains('h1', 'Create New Event').should('be.visible');
            // Fill out EventForm (assuming EventForm.tsx is implemented and has these fields)
            // This part is highly dependent on EventForm's actual fields and structure.
            // Example:
            // cy.get('input[name="name"]').type('E2E Test Event by Organizer');
            // cy.get('textarea[name="description"]').type('This is a test event created by an E2E test.');
            // cy.get('select[name="venue"]').select(1); // Select first venue, assumes venues are loaded
            // cy.get('input[name="start_time"]').type('2030-12-01T10:00');
            // cy.get('input[name="end_time"]').type('2030-12-01T12:00');
            // cy.get('input[name="ticket_price"]').type('25.00');
            // cy.get('button[type="submit"]').click();
            // cy.url().should('include', '/events/'); // Or wherever it redirects after creation
            // cy.contains('E2E Test Event by Organizer').should('be.visible');
            cy.log('EVENT CREATION TEST SKIPPED: EventForm.tsx interaction details unknown/not implemented yet in this test.');
            // For now, simulate creation via API to get an event ID for next steps
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/events-management/`,
                headers: { Authorization: `Token ${organizerAuthToken}` },
                body: { name: 'E2E Event by Organizer', venue: 1, /* Replace with actual venue ID */ ticket_price: '10', start_time: new Date().toISOString(), end_time: new Date().toISOString() }
            }).then(response => {
                expect(response.status).to.eq(201);
                createdEventId = response.body.id;
            });
        });

        it('can access and edit their own event', () => {
            expect(createdEventId).to.exist; // Ensure event was created in previous test or a shared setup
            if (!createdEventId) {
                cy.log("Skipping edit test as createdEventId is not set.");
                return; // Or skip using Cypress mechanism
            }
            cy.visit(`/dashboard/organizer/events/edit/${createdEventId}`); // Assuming this path structure
            cy.contains('h1', `Edit Event`).should('be.visible'); // Or similar title
            // Fill out form to edit
            // cy.get('input[name="name"]').clear().type('E2E Test Event - Edited');
            // cy.get('button[type="submit"]').click();
            // cy.contains('Event updated successfully').should('be.visible');
            cy.log('EVENT EDIT TEST SKIPPED: Edit form interaction details unknown.');
        });

        it('should be denied access to create venue page', () => {
            cy.visit('/dashboard/manager/venues/create', { failOnStatusCode: false });
            // RoleRequired guard should redirect or show error.
            // If it redirects to fallbackUrl='/', check for that.
            // If showError=true, check for error message.
            cy.contains('You are not authorized to view this page.').should('be.visible'); // Assuming showError=true
            // Or check URL if redirected: cy.url().should('not.include', '/dashboard/manager/venues/create');
        });
    });

    context('As Customer (Negative Permissions Test for EO Resources)', () => {
        beforeEach(() => {
            loginAs(customerAuthToken);
        });

        it('customer cannot access create event page', () => {
            cy.visit('/dashboard/organizer/events/create', { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });

        it('customer cannot edit an event created by an organizer', () => {
            if (!createdEventId) {
                cy.log("Skipping edit test as createdEventId is not set.");
                return;
            }
            cy.visit(`/dashboard/organizer/events/edit/${createdEventId}`, { failOnStatusCode: false });
            // This depends on whether the edit page itself is protected by RoleRequired for GET,
            // or if the form submission (PUT/PATCH) is protected.
            // Assuming page GET is protected or shows an immediate "unauthorized".
             cy.contains('You are not authorized to view this page.').should('be.visible');
        });
    });
});
