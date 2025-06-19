const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_CUSTOMER = 'CUSTOMER';

describe('Venue Creation Page (/venues/new)', () => {
  const venueManagerUser = {
    email: `vm_${Date.now()}@example.com`,
    password: 'password123',
    username: `vm_user_${Date.now()}`,
  };
  const customerUser = {
    email: `cust_${Date.now()}@example.com`,
    password: 'password123',
    username: `cust_user_${Date.now()}`,
  };

  let venueManagerToken: string;
  let customerToken: string;

  before(() => {
    // Create Venue Manager user
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: venueManagerUser.username,
        email: venueManagerUser.email,
        password: venueManagerUser.password,
        password2: venueManagerUser.password,
      },
    }).then((regResp) => {
      expect(regResp.status).to.eq(201);
      // Log in as Venue Manager to get token and assign role (assuming admin powers or specific endpoint for role assign)
      cy.request({
        method: 'POST',
        url: `${Cypress.env('apiUrl')}/auth/login/`,
        body: {
          email: venueManagerUser.email,
          password: venueManagerUser.password,
        },
      }).then((loginResp) => {
        venueManagerToken = loginResp.body.key;
        cy.wrap(venueManagerToken).as('venueManagerToken');
        // Assign VENUE_MANAGER role - This step is tricky without an admin user or specific endpoint.
        // For now, we assume this user, once created, *is* a venue manager or can be made one easily.
        // This might need a custom backend command or seeding if role assignment is complex.
        // As a placeholder, we'll log it. If tests fail on role, this needs to be addressed.
        cy.log(
          `Venue Manager token obtained. Manual role assignment might be needed if not default: ${venueManagerUser.email}`
        );
      });
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
    }).then((regResp) => {
      expect(regResp.status).to.eq(201);
      cy.request({
        method: 'POST',
        url: `${Cypress.env('apiUrl')}/auth/login/`,
        body: { email: customerUser.email, password: customerUser.password },
      }).then((loginResp) => {
        customerToken = loginResp.body.key;
        cy.wrap(customerToken).as('customerToken');
      });
    });
  });

  beforeEach(() => {
    localStorage.removeItem('authToken'); // Clear token before each test
    localStorage.removeItem('authUser');
    cy.visit('/venues/new'); // Navigate to the page
  });

  it('redirects unauthenticated user to login', () => {
    cy.url().should('include', '/login'); // Or a fallback if RoleRequired redirects elsewhere first
    cy.contains('h1', 'Login').should('be.visible');
  });

  it('shows access denied or redirects customer user (not VENUE_MANAGER)', function () {
    localStorage.setItem('authToken', this.customerToken);
    // Re-visit because beforeEach clears it, and RoleRequired checks on mount
    cy.visit('/venues/new');

    // RoleRequired uses showError=true for this page, so it should display an error message
    cy.contains(/access denied|you are not authorized/i).should('be.visible');
    cy.get('h1').contains('Add New Venue').should('not.exist');
  });

  context('When logged in as Venue Manager', () => {
    beforeEach(function () {
      // Use function() to access alias context
      localStorage.setItem('authToken', this.venueManagerToken);
      // Mock a successful user fetch for AuthContext that includes the role
      cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
        statusCode: 200,
        body: {
          pk: 1,
          id: 1,
          username: venueManagerUser.username,
          email: venueManagerUser.email,
          roles: [{ name: ROLE_VENUE_MANAGER }], // Ensure roles are objects if AuthContext processes them
        },
      }).as('getUserVenueManager');
      cy.visit('/venues/new');
      cy.wait('@getUserVenueManager'); // Wait for user context to be potentially set
    });

    it('allows VENUE_MANAGER to see the "Add New Venue" page and form', () => {
      cy.url().should('include', '/venues/new');
      cy.get('h1').contains('Add New Venue').should('be.visible');
      cy.get('form').should('be.visible');
      cy.get('input[name="name"]').should('be.visible');
      cy.get('button[type="submit"]')
        .contains('Create Venue')
        .should('be.visible');
    });

    it('allows VENUE_MANAGER to fill and submit the venue form successfully', () => {
      const venueName = `E2E Test Venue ${new Date().getTime()}`;
      cy.intercept('POST', `${Cypress.env('apiUrl')}/venues/`).as(
        'createVenueApi'
      );

      cy.get('input[name="name"]').type(venueName);
      cy.get('textarea[name="address"]').type('123 E2E Test Street, Test City');
      cy.get('input[name="capacity"]').type('120');
      cy.get('input[name="amenities"]').type('WiFi, Projector, Parking'); // Assuming amenities is a text input for comma-separated
      cy.get('input[name="pricing_per_hour"]').type('75.50');
      cy.get('input[name="pricing_per_day"]').type('500.00');
      // is_available might be a checkbox or default to true
      // cy.get('input[name="is_available"]').check();

      cy.get('button[type="submit"]').contains('Create Venue').click();

      cy.wait('@createVenueApi').then((interception) => {
        expect(interception.response?.statusCode).to.eq(201);
        expect(interception.request.body.name).to.eq(venueName);
        expect(interception.request.body.capacity).to.eq(120); // Number, not string
      });

      cy.contains(`Venue "${venueName}" created successfully!`).should(
        'be.visible'
      );
      cy.url().should('include', '/venues'); // Check for redirect to venues list
    });

    it('shows an error message if form submission fails', () => {
      cy.intercept('POST', `${Cypress.env('apiUrl')}/venues/`, {
        statusCode: 400,
        body: { name: ['Venue with this name already exists.'] }, // Example error
      }).as('createVenueApiFail');

      cy.get('input[name="name"]').type('Duplicate Test Venue');
      cy.get('textarea[name="address"]').type('Error Address');
      cy.get('input[name="capacity"]').type('50');

      cy.get('button[type="submit"]').contains('Create Venue').click();
      cy.wait('@createVenueApiFail');

      cy.contains(/failed to create venue/i).should('be.visible');
      // Check for specific field error if available
      // cy.contains(/venue with this name already exists/i).should('be.visible');
    });
  });
});
