const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_CUSTOMER = 'CUSTOMER';
const ROLE_ADMIN = 'ADMIN'; // For creating initial venue if needed

describe('Venue Edit Page (/venues/:id/edit)', () => {
  const uniqueId = Date.now();
  const venueManagerOwner = {
    email: `vm_owner_${uniqueId}@example.com`,
    password: 'password123',
    username: `vm_owner_${uniqueId}`,
  };
  const venueManagerNonOwner = {
    email: `vm_nonowner_${uniqueId}@example.com`,
    password: 'password123',
    username: `vm_nonowner_${uniqueId}`,
  };
  const customerUser = {
    email: `cust_edit_${uniqueId}@example.com`,
    password: 'password123',
    username: `cust_edit_${uniqueId}`,
  };

  let venueManagerOwnerToken: string;
  let venueManagerNonOwnerToken: string;
  let customerToken: string;
  let ownedVenueId: string;

  const mockVenueData = {
    name: 'Original E2E Venue Name',
    address: '123 Original St',
    capacity: 100,
    amenities: ['WiFi', 'Parking'],
    pricing_per_hour: '50.00',
    owner: { id: null }, // Placeholder, will be set to venueManagerOwner.id
  };

  before(() => {
    // Create users
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: venueManagerOwner.username,
        email: venueManagerOwner.email,
        password: venueManagerOwner.password,
        password2: venueManagerOwner.password,
      },
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: {
            email: venueManagerOwner.email,
            password: venueManagerOwner.password,
          },
        })
      )
      .then((loginResp) => {
        venueManagerOwnerToken = loginResp.body.key;
        cy.wrap(venueManagerOwnerToken).as('venueManagerOwnerToken');
        // Set the owner ID for mockVenueData
        // This requires knowing the user ID. Assume login response or a /auth/user call gives it.
        // For simplicity, we'll assume the test environment can link this user to the VENUE_MANAGER role.
        // And that their ID will be used for `mockVenueData.owner.id`.
        // This part is crucial: the user created here MUST have VENUE_MANAGER role in backend for tests to pass.
        // Also, their actual user ID from DB is needed for ownership check.
        // For now, we'll use a placeholder ID and assume test setup handles role assignment.
        // A better way is to fetch user after login to get their actual ID.
        cy.request({
          method: 'GET',
          url: `${Cypress.env('apiUrl')}/auth/user/`,
          headers: { Authorization: `Token ${venueManagerOwnerToken}` },
        }).then((userResp) => {
          mockVenueData.owner.id = userResp.body.id; // Set the actual owner ID
          // Create a venue owned by venueManagerOwner
          cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/venues/`,
            headers: { Authorization: `Token ${venueManagerOwnerToken}` },
            body: {
              name: mockVenueData.name,
              address: mockVenueData.address,
              capacity: mockVenueData.capacity,
              amenities: mockVenueData.amenities,
              pricing_per_hour: mockVenueData.pricing_per_hour,
            },
          }).then((venueResp) => {
            ownedVenueId = venueResp.body.id;
            cy.wrap(ownedVenueId).as('ownedVenueId');
          });
        });
      });

    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: venueManagerNonOwner.username,
        email: venueManagerNonOwner.email,
        password: venueManagerNonOwner.password,
        password2: venueManagerNonOwner.password,
      },
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: {
            email: venueManagerNonOwner.email,
            password: venueManagerNonOwner.password,
          },
        })
      )
      .then((loginResp) => {
        venueManagerNonOwnerToken = loginResp.body.key;
        cy.wrap(venueManagerNonOwnerToken).as('venueManagerNonOwnerToken');
        // Assume this user also gets VENUE_MANAGER role in test setup.
      });

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

  beforeEach(function () {
    // Use function() to access alias context
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    // Intercept common API calls
    cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`).as('getUser');
    // Intercept GET for the specific venue, using alias for ownedVenueId
    if (this.ownedVenueId) {
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/venues/${this.ownedVenueId}/`,
        {
          statusCode: 200,
          body: {
            ...mockVenueData,
            id: this.ownedVenueId,
            owner: mockVenueData.owner.id,
          }, // Return owner ID
        }
      ).as('getVenueDetails');
    }
  });

  it('redirects unauthenticated user to login', function () {
    if (!this.ownedVenueId) this.skip(); // Skip if venue setup failed
    cy.visit(`/venues/${this.ownedVenueId}/edit`);
    cy.url().should('include', '/login');
    cy.contains('h1', 'Login').should('be.visible');
  });

  it('shows access denied for Customer user', function () {
    if (!this.ownedVenueId || !this.customerToken) this.skip();
    localStorage.setItem('authToken', this.customerToken);
    cy.visit(`/venues/${this.ownedVenueId}/edit`);
    cy.contains(/access denied|you are not authorized/i).should('be.visible');
    cy.get('h1')
      .contains(`Edit Venue: ${mockVenueData.name}`)
      .should('not.exist');
  });

  it('shows access denied for Venue Manager who is not the owner', function () {
    if (!this.ownedVenueId || !this.venueManagerNonOwnerToken) this.skip();
    localStorage.setItem('authToken', this.venueManagerNonOwnerToken);
    // Mock user call for non-owner VM
    cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
      body: { id: 'nonOwnerId', roles: [{ name: ROLE_VENUE_MANAGER }] },
    }).as('getNonOwnerUser');

    cy.visit(`/venues/${this.ownedVenueId}/edit`);
    cy.wait('@getNonOwnerUser');
    cy.wait('@getVenueDetails'); // Ensure venue details are loaded to check ownership

    cy.contains('You are not authorized to edit this venue.').should(
      'be.visible'
    );
    cy.get('h1')
      .contains(`Edit Venue: ${mockVenueData.name}`)
      .should('not.exist');
  });

  context('When logged in as Venue Manager (Owner)', function () {
    beforeEach(function () {
      if (!this.ownedVenueId || !this.venueManagerOwnerToken) this.skip();
      localStorage.setItem('authToken', this.venueManagerOwnerToken);
      // Mock user call for owner VM
      cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
        body: {
          id: mockVenueData.owner.id,
          roles: [{ name: ROLE_VENUE_MANAGER }],
        },
      }).as('getOwnerUser');
      cy.visit(`/venues/${this.ownedVenueId}/edit`);
      cy.wait('@getOwnerUser');
      cy.wait('@getVenueDetails');
    });

    it('allows owner VENUE_MANAGER to see the edit page with pre-filled form', function () {
      cy.url().should('include', `/venues/${this.ownedVenueId}/edit`);
      cy.get('h1')
        .contains(`Edit Venue: ${mockVenueData.name}`)
        .should('be.visible');
      cy.get('input[name="name"]').should('have.value', mockVenueData.name);
      cy.get('textarea[name="address"]').should(
        'have.value',
        mockVenueData.address
      );
      cy.get('input[name="capacity"]').should(
        'have.value',
        mockVenueData.capacity.toString()
      );
      cy.get('button[type="submit"]')
        .contains('Update Venue')
        .should('be.visible');
    });

    it('allows owner VENUE_MANAGER to update the venue', function () {
      const updatedName = `Updated E2E Venue ${Date.now()}`;
      cy.intercept(
        'PATCH',
        `${Cypress.env('apiUrl')}/venues/${this.ownedVenueId}/`
      ).as('updateVenueApi');

      cy.get('input[name="name"]').clear().type(updatedName);
      cy.get('input[name="capacity"]').clear().type('150');

      cy.get('button[type="submit"]').contains('Update Venue').click();

      cy.wait('@updateVenueApi').then((interception) => {
        expect(interception.response?.statusCode).to.oneOf([200, 204]); // PUT is 200, PATCH can be 200
        expect(interception.request.body.name).to.eq(updatedName);
        expect(interception.request.body.capacity).to.eq(150);
      });
      cy.contains(`Venue "${updatedName}" updated successfully!`).should(
        'be.visible'
      );
      cy.url().should('include', '/venues'); // Check redirect after success
    });
  });
});
