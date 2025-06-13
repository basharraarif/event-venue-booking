// cypress/e2e/roles_customer.cy.ts

describe('Customer Role E2E Test', () => {
    const customerUser = {
        username: 'e2e_customer_role_test',
        email: 'e2e_customer_rt@example.com',
        password: 'e2e_password123',
        role: 'CUSTOMER' // Ensure backend assigns this or test user has it
    };
    let customerAuthToken: string;

    before(() => {
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

    const loginAsCustomer = () => {
        localStorage.setItem('authToken', customerAuthToken);
        cy.visit('/');
    };

    context('As Customer', () => {
        beforeEach(() => {
            loginAsCustomer();
        });

        it('should not see admin, event organizer, or venue manager specific links in Header', () => {
            cy.get('header').should('not.contain', 'Create Event');
            cy.get('header').should('not.contain', 'Create Venue');
            cy.get('header').should('not.contain', 'Admin Panel');
            // Should see generic links like "Events", "Venues", "Dashboard", "Logout"
            cy.get('header').should('contain', 'Events');
            cy.get('header').should('contain', 'Venues');
            cy.get('header').should('contain', 'Dashboard'); // Generic dashboard link
            cy.get('header').should('contain', 'Logout');
        });

        it('should be denied access to event creation page', () => {
            cy.visit('/dashboard/organizer/events/create', { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });

        it('should be denied access to venue creation page', () => {
            cy.visit('/dashboard/manager/venues/create', { failOnStatusCode: false });
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });

        it('can access their own dashboard and bookings list (generic dashboard)', () => {
            cy.visit('/dashboard');
            cy.contains('h1', 'My Dashboard').should('be.visible'); // Assuming a generic dashboard page title
            // Could add further checks if there's a "My Bookings" section or link here
            cy.visit('/dashboard/bookings'); // Assuming this is the URL for listing own bookings
            cy.contains('h1', 'My Bookings').should('be.visible');
        });

        // Add a test for attempting to access a protected admin page if one exists
        it('should be denied access to a generic admin page', () => {
            cy.visit('/admin/dashboard', { failOnStatusCode: false }); // Example admin path
            cy.contains('You are not authorized to view this page.').should('be.visible');
        });
    });
});
