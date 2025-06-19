const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_ADMIN = 'ADMIN';
const ROLE_CUSTOMER = 'CUSTOMER';

describe('Event Creation Page (/dashboard/organizer/events/create)', () => {
  const uniqueId = Date.now();
  const eventOrganizerUser = {
    email: `eo_${uniqueId}@example.com`,
    password: 'password123',
    username: `eo_user_${uniqueId}`,
  };
  const customerUser = {
    email: `cust_event_create_${uniqueId}@example.com`,
    password: 'password123',
    username: `cust_event_create_${uniqueId}`,
  };
  const adminUser = {
    // Admin user for creating venues needed by event form
    email: `admin_event_create_${uniqueId}@example.com`,
    password: 'password123',
    username: `admin_event_create_${uniqueId}`,
  };

  let eventOrganizerToken: string;
  let customerToken: string;
  let adminToken: string;
  let testVenueId: string;

  before(() => {
    // Create Admin User (to create a venue)
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: adminUser.username,
        email: adminUser.email,
        password: adminUser.password,
        password2: adminUser.password,
      },
      failOnStatusCode: false, // Allow failure if user already exists from previous partial run
    }).then((regResp) => {
      // Log in as admin to get token
      cy.request({
        method: 'POST',
        url: `${Cypress.env('apiUrl')}/auth/login/`,
        body: { email: adminUser.email, password: adminUser.password },
      }).then((loginResp) => {
        adminToken = loginResp.body.key;
        // Create a venue as admin (or ensure one exists)
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/venues/`,
          headers: { Authorization: `Token ${adminToken}` },
          body: {
            name: `Test Venue for Event Create ${uniqueId}`,
            address: '123 Test St',
            capacity: 100,
          },
        }).then((venueResp) => {
          testVenueId = venueResp.body.id;
          cy.wrap(testVenueId).as('testVenueId');
        });
      });
    });

    // Create Event Organizer user
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: eventOrganizerUser.username,
        email: eventOrganizerUser.email,
        password: eventOrganizerUser.password,
        password2: eventOrganizerUser.password,
      },
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: {
            email: eventOrganizerUser.email,
            password: eventOrganizerUser.password,
          },
        })
      )
      .then((loginResp) => {
        eventOrganizerToken = loginResp.body.key;
        cy.wrap(eventOrganizerToken).as('eventOrganizerToken');
        // Assume role assignment happens externally or by default for this test user
        cy.log(
          `Event Organizer token obtained. Role assignment might be needed: ${eventOrganizerUser.email}`
        );
      });

    // Create Customer user
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: customerUser.username,
        email: customerUser.email,
        password: customerUser.password,
        password2: customerUser.password,
      },
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: { email: customerUser.email, password: customerUser.password },
        })
      )
      .then((loginResp) => {
        customerToken = loginResp.body.key;
        cy.wrap(customerToken).as('customerToken');
      });
  });

  beforeEach(() => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    cy.visit('/dashboard/organizer/events/create');
  });

  it('redirects unauthenticated user to login', () => {
    cy.url().should('include', '/login');
    cy.contains('h1', 'Login').should('be.visible');
  });

  it('shows access denied for Customer user', function () {
    localStorage.setItem('authToken', this.customerToken);
    cy.visit('/dashboard/organizer/events/create');
    // The RoleRequired HOC on this page uses showError=true
    cy.contains(/access denied|you are not authorized/i).should('be.visible');
    cy.get('h1').contains('Create New Event').should('not.exist');
  });

  context('When logged in as Event Organizer', () => {
    beforeEach(function () {
      localStorage.setItem('authToken', this.eventOrganizerToken);
      cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
        statusCode: 200,
        body: {
          pk: 'eoUserId',
          id: 'eoUserId',
          username: eventOrganizerUser.username,
          email: eventOrganizerUser.email,
          roles: [{ name: ROLE_EVENT_ORGANIZER }],
        },
      }).as('getUserEO');
      // Mock calls for EventForm data if it makes them (e.g., categories, venues)
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/venues/?limit=1000&offset=0`,
        {
          statusCode: 200,
          body: {
            results: [
              { id: this.testVenueId, name: 'Test Venue for Event Create' },
            ],
          },
        }
      ).as('getVenuesForForm');
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/events-management/categories/`,
        { statusCode: 200, body: [{ id: 'cat1', name: 'Test Category' }] }
      ).as('getCategoriesForForm');

      cy.visit('/dashboard/organizer/events/create');
      cy.wait(['@getUserEO', '@getVenuesForForm', '@getCategoriesForForm']);
    });

    it('allows EVENT_ORGANIZER to see the "Create New Event" page and form', () => {
      cy.url().should('include', '/dashboard/organizer/events/create');
      cy.get('h1').contains('Create New Event').should('be.visible');
      // Assuming EventForm is complex and has its own unit tests,
      // here we just check if a key part of it is rendered.
      // If EventForm is a placeholder, this might need adjustment.
      // For now, let's assume EventForm renders some distinctive fields/button.
      cy.get('input[name="name"]').should('be.visible'); // From a potential EventForm
      cy.get('button[type="submit"]').should('be.visible');
    });

    it('allows EVENT_ORGANIZER to fill and submit the event form successfully', function () {
      const eventName = `E2E Test Event ${new Date().getTime()}`;
      cy.intercept(
        'POST',
        `${Cypress.env('apiUrl')}/events-management/events/`
      ).as('createEventApi');

      cy.get('input[name="name"]').type(eventName);
      cy.get('textarea[name="description"]').type(
        'An exciting E2E test event.'
      );
      cy.get('select[name="venue"]').select(this.testVenueId);
      cy.get('select[name="categories"]').select(['cat1']); // Assuming multi-select or some way to pick category

      const startTime = new Date(Date.now() + 3 * 24 * 60 * 60 * 1000); // 3 days from now
      const endTime = new Date(
        Date.now() + 3 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000
      ); // 2 hours after start
      cy.get('input[name="start_time"]').type(
        startTime.toISOString().substring(0, 16)
      );
      cy.get('input[name="end_time"]').type(
        endTime.toISOString().substring(0, 16)
      );

      cy.get('input[name="ticket_price"]').type('25.00');
      cy.get('input[name="max_capacity"]').type('100');

      cy.get('button[type="submit"]').click();

      cy.wait('@createEventApi').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201);
        expect(interception.request.body.name).to.eq(eventName);
        expect(interception.request.body.venue).to.eq(this.testVenueId);
      });

      cy.contains(/event created successfully/i).should('be.visible');
      // Check for redirect, e.g., to event detail page or dashboard
      // cy.url().should('include', '/dashboard');
    });
  });
});
