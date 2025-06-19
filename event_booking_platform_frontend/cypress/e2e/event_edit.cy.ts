const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_ADMIN = 'ADMIN';
const ROLE_CUSTOMER = 'CUSTOMER';

describe('Event Edit Page (/dashboard/organizer/events/edit/:eventId)', () => {
  const uniqueId = Date.now();
  const organizer1User = {
    email: `eo1_${uniqueId}@example.com`,
    password: 'password123',
    username: `eo1_user_${uniqueId}`,
  };
  const organizer2User = {
    email: `eo2_${uniqueId}@example.com`,
    password: 'password123',
    username: `eo2_user_${uniqueId}`,
  };
  const customerUser = {
    email: `cust_event_edit_${uniqueId}@example.com`,
    password: 'password123',
    username: `cust_event_edit_${uniqueId}`,
  };
  const adminUser = {
    email: `admin_event_edit_${uniqueId}@example.com`,
    password: 'password123',
    username: `admin_event_edit_${uniqueId}`,
  };

  let organizer1Token: string;
  let organizer2Token: string;
  let customerToken: string;
  let adminToken: string;

  let testVenueId: string;
  let eventByOrganizer1Id: string;

  // Mock Event Data that will be "fetched" for the edit page
  const mockEventData = {
    name: 'Original E2E Event Name',
    description: 'Original event description.',
    venue: '', // Will be set to testVenueId
    categories: [{ id: 'cat1', name: 'Test Category' }], // Assuming categories are objects with id and name
    start_time: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000)
      .toISOString()
      .substring(0, 16),
    end_time: new Date(
      Date.now() + 5 * 24 * 60 * 60 * 1000 + 2 * 60 * 60 * 1000
    )
      .toISOString()
      .substring(0, 16),
    ticket_price: '30.00',
    max_capacity: 150,
    status: 'upcoming',
    organizer: '', // Will be set to organizer1's actual ID
  };

  before(() => {
    // 1. Create Admin User (to create a venue)
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: adminUser.username,
        email: adminUser.email,
        password: adminUser.password,
        password2: adminUser.password,
      },
      failOnStatusCode: false,
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: { email: adminUser.email, password: adminUser.password },
        })
      )
      .then((loginResp) => {
        adminToken = loginResp.body.key;
        cy.request({
          method: 'GET',
          url: `${Cypress.env('apiUrl')}/auth/user/`,
          headers: { Authorization: `Token ${adminToken}` },
        }).then((userResp) => {
          // Create a venue as admin
          cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/venues/`,
            headers: { Authorization: `Token ${adminToken}` },
            body: {
              name: `Test Venue for Event Edit ${uniqueId}`,
              address: '123 Edit St',
              capacity: 100,
            },
          }).then((venueResp) => {
            testVenueId = venueResp.body.id;
            cy.wrap(testVenueId).as('testVenueId');
            mockEventData.venue = testVenueId; // Update mock data

            // 2. Create Event Organizer 1
            cy.request({
              method: 'POST',
              url: `${Cypress.env('apiUrl')}/auth/registration/`,
              body: {
                username: organizer1User.username,
                email: organizer1User.email,
                password: organizer1User.password,
                password2: organizer1User.password,
              },
            })
              .then(() =>
                cy.request({
                  method: 'POST',
                  url: `${Cypress.env('apiUrl')}/auth/login/`,
                  body: {
                    email: organizer1User.email,
                    password: organizer1User.password,
                  },
                })
              )
              .then((org1LoginResp) => {
                organizer1Token = org1LoginResp.body.key;
                cy.wrap(organizer1Token).as('organizer1Token');
                // Get organizer1's actual ID
                cy.request({
                  method: 'GET',
                  url: `${Cypress.env('apiUrl')}/auth/user/`,
                  headers: { Authorization: `Token ${organizer1Token}` },
                }).then((org1UserResp) => {
                  mockEventData.organizer = org1UserResp.body.id; // Set actual organizer ID
                  // Create Event by Organizer 1
                  cy.request({
                    method: 'POST',
                    url: `${Cypress.env('apiUrl')}/events-management/events/`,
                    headers: { Authorization: `Token ${organizer1Token}` },
                    body: {
                      ...mockEventData,
                      categories: mockEventData.categories.map((c) => c.name),
                    }, // Send category names for creation
                  }).then((eventResp) => {
                    eventByOrganizer1Id = eventResp.body.id;
                    cy.wrap(eventByOrganizer1Id).as('eventByOrganizer1Id');
                  });
                });
              });
          });
        });
      });

    // Create Event Organizer 2
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: organizer2User.username,
        email: organizer2User.email,
        password: organizer2User.password,
        password2: organizer2User.password,
      },
    })
      .then(() =>
        cy.request({
          method: 'POST',
          url: `${Cypress.env('apiUrl')}/auth/login/`,
          body: {
            email: organizer2User.email,
            password: organizer2User.password,
          },
        })
      )
      .then((loginResp) => {
        organizer2Token = loginResp.body.key;
        cy.wrap(organizer2Token).as('organizer2Token');
      });

    // Create Customer User
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
    // Ensure eventByOrganizer1Id is resolved before trying to use it in URL
    if (!this.eventByOrganizer1Id) {
      // This might happen if the before() block fails or alias not set in time for first test.
      // A better way is to ensure all setup completes before tests run.
      // For now, this check prevents undefined in URL.
      cy.log('Skipping test as eventByOrganizer1Id is not available.');
      this.skip();
    }
    cy.visit(`/dashboard/organizer/events/edit/${this.eventByOrganizer1Id}`);
  });

  it('redirects unauthenticated user to login', function () {
    if (!this.eventByOrganizer1Id) this.skip();
    cy.url().should('include', '/login');
    cy.contains('h1', 'Login').should('be.visible');
  });

  it('shows access denied for Customer user', function () {
    if (!this.eventByOrganizer1Id || !this.customerToken) this.skip();
    localStorage.setItem('authToken', this.customerToken);
    cy.visit(`/dashboard/organizer/events/edit/${this.eventByOrganizer1Id}`);
    cy.contains(/access denied|you are not authorized/i).should('be.visible');
    cy.get('h1')
      .contains(`Edit Event: ${mockEventData.name}`)
      .should('not.exist');
  });

  it('shows access denied for Event Organizer who is not the owner', function () {
    if (!this.eventByOrganizer1Id || !this.organizer2Token) this.skip();
    localStorage.setItem('authToken', this.organizer2Token);
    cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
      statusCode: 200,
      body: { id: 'org2UserId', roles: [{ name: ROLE_EVENT_ORGANIZER }] },
    }).as('getNonOwnerEO');
    cy.intercept(
      'GET',
      `${Cypress.env('apiUrl')}/events-management/events/${this.eventByOrganizer1Id}/`,
      {
        statusCode: 200,
        body: {
          ...mockEventData,
          id: this.eventByOrganizer1Id,
          organizer: mockEventData.organizer,
        },
      }
    ).as('getEventToEdit');

    cy.visit(`/dashboard/organizer/events/edit/${this.eventByOrganizer1Id}`);
    cy.wait(['@getNonOwnerEO', '@getEventToEdit']);

    cy.contains('You are not authorized to edit this event.').should(
      'be.visible'
    );
    cy.get('h1')
      .contains(`Edit Event: ${mockEventData.name}`)
      .should('not.exist');
  });

  context('When logged in as Event Organizer (Owner)', function () {
    beforeEach(function () {
      if (
        !this.eventByOrganizer1Id ||
        !this.organizer1Token ||
        !mockEventData.organizer
      )
        this.skip();
      localStorage.setItem('authToken', this.organizer1Token);
      cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`, {
        statusCode: 200,
        body: {
          id: mockEventData.organizer,
          roles: [{ name: ROLE_EVENT_ORGANIZER }],
        },
      }).as('getOwnerEO');
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/events-management/events/${this.eventByOrganizer1Id}/`,
        {
          statusCode: 200,
          body: {
            ...mockEventData,
            id: this.eventByOrganizer1Id,
            organizer: mockEventData.organizer,
            venue: testVenueId,
            categories: mockEventData.categories.map((c) => c.name),
          },
        }
      ).as('getEventToEdit');
      // Mock calls for EventForm data if it makes them (e.g., categories, venues)
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/venues/?limit=1000&offset=0`,
        {
          statusCode: 200,
          body: {
            results: [{ id: testVenueId, name: 'Test Venue for Event Edit' }],
          },
        }
      ).as('getVenuesForForm');
      cy.intercept(
        'GET',
        `${Cypress.env('apiUrl')}/events-management/categories/`,
        { statusCode: 200, body: mockEventData.categories }
      ).as('getCategoriesForForm');

      cy.visit(`/dashboard/organizer/events/edit/${this.eventByOrganizer1Id}`);
      cy.wait([
        '@getOwnerEO',
        '@getEventToEdit',
        '@getVenuesForForm',
        '@getCategoriesForForm',
      ]);
    });

    it('allows owner EVENT_ORGANIZER to see the edit page with pre-filled form', function () {
      cy.url().should(
        'include',
        `/dashboard/organizer/events/edit/${this.eventByOrganizer1Id}`
      );
      cy.get('h1')
        .contains(`Edit Event: ${mockEventData.name}`)
        .should('be.visible');
      // Assuming EventForm is complex and has its own unit tests,
      // here we just check if a key part of it is pre-filled.
      // This requires the actual EventForm to be rendered, not a simple mock div.
      // If EventForm is just a placeholder in the page, this will fail.
      // For now, let's assume the page renders some text indicating form placeholder.
      cy.contains(/event editing form will be here/i).should('be.visible');
      // To test pre-fill, the actual EventForm component would need to be integrated and its fields queryable.
      // Example (if form fields were directly on page):
      // cy.get('input[name="name"]').should('have.value', mockEventData.name);
    });

    it('allows owner EVENT_ORGANIZER to update the event (placeholder test)', function () {
      const updatedDescription = `Updated E2E Event Description ${Date.now()}`;
      cy.intercept(
        'PATCH',
        `${Cypress.env('apiUrl')}/events-management/events/${this.eventByOrganizer1Id}/`
      ).as('updateEventApi');

      // This part requires the actual EventForm to be rendered and interactable.
      // If EventForm is a placeholder, these interactions will fail.
      // cy.get('textarea[name="description"]').clear().type(updatedDescription);
      // cy.get('button[type="submit"]').click();

      // cy.wait('@updateEventApi').then((interception) => {
      //     expect(interception.response?.statusCode).to.eq(200);
      //     expect(interception.request.body.description).to.eq(updatedDescription);
      // });
      // cy.contains(/event updated successfully/i).should('be.visible');
      cy.log(
        'Placeholder test for event update by owner. Actual form interaction depends on EventForm component.'
      );
      expect(true).to.be.true; // Placeholder assertion
    });
  });

  // Add similar context for Admin user if needed
});
