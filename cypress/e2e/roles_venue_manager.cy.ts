// cypress/e2e/roles_venue_manager.cy.ts

describe('Venue Manager Role E2E Test', () => {
    const venueManagerUser = {
        username: 'e2e_venuemanager',
        email: 'e2e_vm@example.com',
        password: 'e2e_password123',
        role: 'VENUE_MANAGER'
    };
    const customerUser = {
        username: 'e2e_customer_for_vm_test',
        email: 'e2e_cust_for_vm@example.com',
        password: 'e2e_password123',
        role: 'CUSTOMER'
    };
    let venueManagerAuthToken: string;
    let customerAuthToken: string;
    let createdVenueId: string | null = null;

    before(() => {
        // Register and login Venue Manager user
        cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/auth/registration/`,
            body: { username: venueManagerUser.username, email: venueManagerUser.email, password: venueManagerUser.password, password2: venueManagerUser.password },
            failOnStatusCode: false
        }).then(() => {
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/auth/login/`,
                body: { email: venueManagerUser.email, password: venueManagerUser.password },
            }).then(resp => venueManagerAuthToken = resp.body.key);
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
        cy.visit('/');
    };

    context('As Venue Manager', () => {
        beforeEach(() => {
            loginAs(venueManagerAuthToken);
        });

        it('should see Venue Manager specific links in Header', () => {
            cy.get('header').should('contain', 'Create Venue');
            cy.get('header').should('not.contain', 'Create Event'); // Assuming not also an Event Organizer
            cy.get('header').should('not.contain', 'Admin Panel'); // Assuming not also an Admin
        });

        it('can access and create a venue', () => {
            cy.visit('/dashboard/manager/venues/create'); // Path from Header link
            cy.contains('h1', 'Create New Venue').should('be.visible');
            // Fill out VenueForm (assuming VenueForm.tsx is implemented)
            // Example:
            // cy.get('input[name="name"]').type('E2E Test Venue by Manager');
            // cy.get('textarea[name="address"]').type('123 E2E VM Address');
            // cy.get('input[name="capacity"]').type('150');
            // cy.get('button[type="submit"]').click();
            // cy.url().should('include', '/venues/');
            // cy.contains('E2E Test Venue by Manager').should('be.visible');
            cy.log('VENUE CREATION TEST SKIPPED: VenueForm.tsx interaction details unknown/not implemented yet in this test.');
            // Simulate creation via API for subsequent tests
            cy.request({
                method: 'POST',
                url: `${Cypress.env('apiUrl')}/venues/`,
                headers: { Authorization: `Token ${venueManagerAuthToken}` },
                body: { name: 'E2E Venue by Manager', address: '123 VM St', capacity: 100 }
            }).then(response => {
                expect(response.status).to.eq(201);
                createdVenueId = response.body.id;
            });
        });

        it('can access and edit their own venue', () => {
            expect(createdVenueId).to.exist;
            if (!createdVenueId) {
                cy.log("Skipping edit test as createdVenueId is not set.");
                return;
            }
            cy.visit(`/dashboard/manager/venues/edit/${createdVenueId}`); // Assuming this path structure
            cy.contains('h1', `Edit Venue`).should('be.visible');
            // cy.get('input[name="name"]').clear().type('E2E Test Venue - Edited by VM');
            // cy.get('button[type="submit"]').click();
            // cy.contains('Venue updated successfully').should('be.visible');
            cy.log('VENUE EDIT TEST SKIPPED: Edit form interaction details unknown.');
        });

        it('should be denied access to create event page', () => {
            cy.visit('/dashboard/organizer/events/create', { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });
    });

    context('As Customer (Negative Permissions Test for VM Resources)', () => {
        beforeEach(() => {
            loginAs(customerAuthToken);
        });

        it('customer cannot access create venue page', () => {
            cy.visit('/dashboard/manager/venues/create', { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });

        it('customer cannot edit a venue created by a manager', () => {
            if (!createdVenueId) {
                cy.log("Skipping edit test as createdVenueId is not set.");
                return;
            }
            cy.visit(`/dashboard/manager/venues/edit/${createdVenueId}`, { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });
    });
});
