// cypress/e2e/event_booking_flow.cy.ts

describe('Event Booking and Payment Flow E2E Test', () => {
  const userEmail = `e2e_user_${Date.now()}@example.com`; // Unique email
  const userPassword = 'e2e_password123';
  let testUserId: string;
  let authToken: string;

  // Aliases for event IDs
  const paidEventAlias = 'paidEventId';
  const freeEventAlias = 'freeEventId';

  before(() => {
    // Register user
    cy.request({
      method: 'POST',
      url: `${Cypress.env('apiUrl')}/auth/registration/`,
      body: {
        username: userEmail.split('@')[0],
        email: userEmail,
        password: userPassword,
        password2: userPassword,
      },
    }).then((regResp) => {
      expect(regResp.status).to.eq(201);
      // Login user
      cy.request({
        method: 'POST',
        url: `${Cypress.env('apiUrl')}/auth/login/`,
        body: { email: userEmail, password: userPassword },
      }).then((loginResp) => {
        expect(loginResp.status).to.eq(200);
        authToken = loginResp.body.key;
        cy.wrap(authToken).as('authToken');

        cy.request({
          method: 'GET',
          url: `${Cypress.env('apiUrl')}/auth/user/`,
          headers: { Authorization: `Token ${authToken}` },
        }).then((userResp) => {
          testUserId = userResp.body.id;
          cy.wrap(testUserId).as('testUserId');

          cy.request({
            method: 'POST',
            url: `${Cypress.env('apiUrl')}/venues/`,
            headers: { Authorization: `Token ${authToken}` },
            body: {
              name: 'E2E Test Venue',
              address: '123 E2E St',
              capacity: 100,
              owner: testUserId,
            }, // Assign owner
          }).then((venueResp) => {
            const venueId = venueResp.body.id;
            cy.request({
              method: 'POST',
              url: `${Cypress.env('apiUrl')}/events-management/`,
              headers: { Authorization: `Token ${authToken}` },
              body: {
                name: 'E2E Paid Event',
                venue: venueId,
                ticket_price: '10.00',
                start_time: new Date(
                  Date.now() + 24 * 60 * 60 * 1000
                ).toISOString(),
                end_time: new Date(
                  Date.now() + 26 * 60 * 60 * 1000
                ).toISOString(),
                description: 'A paid event for E2E testing',
                organizer: testUserId, // Assign organizer
              },
            }).then((eventResp) =>
              cy.wrap(eventResp.body.id).as(paidEventAlias)
            );

            cy.request({
              method: 'POST',
              url: `${Cypress.env('apiUrl')}/events-management/`,
              headers: { Authorization: `Token ${authToken}` },
              body: {
                name: 'E2E Free Event',
                venue: venueId,
                ticket_price: '0.00',
                start_time: new Date(
                  Date.now() + 48 * 60 * 60 * 1000
                ).toISOString(),
                end_time: new Date(
                  Date.now() + 50 * 60 * 60 * 1000
                ).toISOString(),
                description: 'A free event for E2E testing',
                organizer: testUserId, // Assign organizer
              },
            }).then((eventResp) =>
              cy.wrap(eventResp.body.id).as(freeEventAlias)
            );
          });
        });
      });
    });
  });

  beforeEach(() => {
    cy.get('@authToken').then((token) => {
      localStorage.setItem('authToken', token as unknown as string);
    });
    cy.intercept('GET', `${Cypress.env('apiUrl')}/auth/user/`).as('getUser');
    // Common intercept for payment intent creation for all paid tests
    cy.intercept(
      'POST',
      `${Cypress.env('apiUrl')}/payments/create-payment-intent/`,
      (req) => {
        req.reply({
          statusCode: 201,
          body: {
            client_secret: `cs_test_mock_secret_${Date.now()}`, // Unique client secret
            payment_id: `mockPaymentDbId_${Date.now()}`,
          },
        });
      }
    ).as('createPaymentIntent');
  });

  context('Paid Event Booking with Stripe Interaction', () => {
    // Function to type into Stripe's iframe input fields
    // Note: This assumes Stripe Elements are loaded and inputs are not in nested iframes.
    // This approach can be flaky if Stripe changes its internal DOM structure.
    const typeInStripeInput = (inputSelector: string, value: string) => {
      // Wait for the iframe to be available and ready
      cy.get('iframe[title="Secure payment input frame"]')
        .its('0.contentDocument.body')
        .should('not.be.empty')
        .then(cy.wrap)
        .find(inputSelector)
        .type(value, { delay: 50 }); // Add delay for typing stability
    };

    const completeStripeForm = () => {
      // Replace with actual selectors if Stripe changes its structure.
      // These are common placeholders. Stripe's Payment Element might combine these.
      // This test assumes separate card number, expiry, CVC, and postal code fields.
      // If using PaymentElement, it might be a single complex iframe.
      // For robust testing, target specific data-testid or aria-labels if available from Stripe.

      // This example assumes Stripe is using multiple iframes or inputs that are individually targetable.
      // A more modern Stripe Payment Element might have a single iframe that's harder to script.
      // If Stripe Elements uses a single complex iframe, a different strategy might be needed,
      // or this level of detail might be omitted in E2E in favor of mocking confirmCardPayment directly
      // without filling the form. The prompt asks to fill it, so we attempt.

      // This is a simplified example. Actual Stripe iframe selectors can be complex.
      // It's common for test environments to have simplified Stripe forms or test modes.
      // If the fields are not directly accessible, this part will fail and need adjustment
      // based on the frontend's Stripe Element configuration.

      // A common pattern is that Stripe elements are wrapped, and the iframe is a child.
      // Let's assume a common structure where each field is in its own iframe or accessible.
      // This is highly dependent on the specific Stripe integration (CardElement vs PaymentElement)

      // For PaymentElement, which is often a single iframe:
      cy.get('iframe[src*="stripe.com"]')
        .its('0.contentDocument.body')
        .should('not.be.empty')
        .then(cy.wrap)
        .find(
          'input[name="cardNumber"], input#Field-cardNumberInput, [data-elements-stable-field-name="cardNumber"]'
        ) // Common selectors
        .type('4242')
        .type('4242')
        .type('4242')
        .type('4242');

      cy.get('iframe[src*="stripe.com"]')
        .its('0.contentDocument.body')
        .should('not.be.empty')
        .then(cy.wrap)
        .find(
          'input[name="cardExpiry"], input#Field-cardExpiryInput, [data-elements-stable-field-name="cardExpiry"]'
        )
        .type('12/29'); // Future date

      cy.get('iframe[src*="stripe.com"]')
        .its('0.contentDocument.body')
        .should('not.be.empty')
        .then(cy.wrap)
        .find(
          'input[name="cardCvc"], input#Field-cardCvcInput, [data-elements-stable-field-name="cardCvc"]'
        )
        .type('123');

      cy.get('iframe[src*="stripe.com"]')
        .its('0.contentDocument.body')
        .should('not.be.empty')
        .then(cy.wrap)
        .find(
          'input[name="postalCode"], input#Field-postalCodeInput, [data-elements-stable-field-name="postalCode"]'
        )
        .type('90210');
      cy.log('Attempted to fill Stripe form inputs.');
    };

    it('successfully books and simulates a successful payment', function () {
      cy.visit(`/events/${this[paidEventAlias]}`);
      cy.contains('h2', 'E2E Paid Event').should('be.visible');
      cy.get('input[name="numberOfTickets"]').clear().type('1');

      cy.intercept('POST', `${Cypress.env('apiUrl')}/bookings/`, {
        statusCode: 201,
        body: {
          id: 'mockBookingSuccess123',
          status: 'pending_payment',
          event: this[paidEventAlias],
          number_of_tickets: 1,
          total_price: '10.00',
        },
      }).as('createBookingSuccess');

      cy.get('button')
        .contains(/book tickets/i)
        .click();
      cy.wait('@createBookingSuccess');
      cy.url().should('include', '/checkout/mockBookingSuccess123');
      cy.contains('h1', 'Checkout').should('be.visible');
      cy.wait('@createPaymentIntent'); // Ensure payment intent is created

      // Mock Stripe.js confirmCardPayment
      cy.window().then((win) => {
        if (win.stripe) {
          // Ensure stripe object is available
          cy.stub(win.stripe, 'confirmCardPayment')
            .resolves({
              paymentIntent: { id: 'pi_mock_success_e2e', status: 'succeeded' },
            })
            .as('confirmCardPaymentMock');
        } else {
          // Fallback or error if Stripe.js isn't loaded as expected
          throw new Error('Stripe.js not found on window.stripe');
        }
      });

      // Attempt to fill the Stripe form elements
      // This is the most fragile part of the test. If selectors are off, it will fail here.
      // Wait for elements to be potentially loaded.
      cy.wait(3000); // Give Stripe elements some time to load, not ideal, use specific element waits if possible
      completeStripeForm();

      cy.get('button[type="submit"]')
        .contains(/pay|confirm order/i)
        .click();
      cy.get('@confirmCardPaymentMock').should('have.been.called');

      // Verify redirection to success page (or success UI update)
      // The frontend should redirect after confirmCardPayment resolves successfully.
      // Example: /payment-status?booking_id=mockBookingSuccess123&status=success
      cy.url().should('include', '/payment-status', { timeout: 10000 });
      cy.url().should('include', 'booking_id=mockBookingSuccess123');
      cy.url().should('include', 'status=success'); // Assuming app sets this query param on success
      cy.contains('h1', /payment successful/i, { timeout: 10000 }).should(
        'be.visible'
      );
      cy.contains('Your booking is confirmed.', { timeout: 10000 }).should(
        'be.visible'
      );

      // Optional: API check for booking status
      cy.get('@authToken').then((token) => {
        cy.request({
          method: 'GET',
          url: `${Cypress.env('apiUrl')}/bookings/mockBookingSuccess123/`,
          headers: { Authorization: `Token ${token as unknown as string}` },
        }).then((bookingDetailsResp) => {
          // Note: The frontend mock of confirmCardPayment doesn't trigger backend webhook in E2E.
          // So, backend booking status might not be 'confirmed' unless the success page call triggers it.
          // For a pure frontend E2E after mocking stripe-js, this check might be out of scope
          // or require another mocked interaction if the success page updates the backend.
          // If the success page calls a backend endpoint to finalize/verify, that should be intercepted too.
          // For now, we assume the frontend shows success. The previous test checked backend update via simulated webhook.
          cy.log(
            'Frontend shows success. Backend status depends on actual webhook or further frontend calls.'
          );
        });
      });
    });

    it('handles a simulated failed payment', function () {
      cy.visit(`/events/${this[paidEventAlias]}`); // Start fresh
      cy.contains('h2', 'E2E Paid Event').should('be.visible');
      cy.get('input[name="numberOfTickets"]').clear().type('1');

      cy.intercept('POST', `${Cypress.env('apiUrl')}/bookings/`, {
        statusCode: 201,
        body: {
          id: 'mockBookingFail123',
          status: 'pending_payment',
          event: this[paidEventAlias],
          number_of_tickets: 1,
          total_price: '10.00',
        },
      }).as('createBookingFail');

      cy.get('button')
        .contains(/book tickets/i)
        .click();
      cy.wait('@createBookingFail');
      cy.url().should('include', '/checkout/mockBookingFail123');
      cy.contains('h1', 'Checkout').should('be.visible');
      cy.wait('@createPaymentIntent');

      // Mock Stripe.js confirmCardPayment to simulate a payment failure
      cy.window().then((win) => {
        if (win.stripe) {
          cy.stub(win.stripe, 'confirmCardPayment')
            .resolves({
              error: { message: 'Your card was declined by the bank.' },
            })
            .as('confirmCardPaymentMockFail');
        } else {
          throw new Error(
            'Stripe.js not found on window.stripe for failure mock'
          );
        }
      });

      cy.wait(3000); // Wait for Stripe elements
      completeStripeForm(); // Fill the form

      cy.get('button[type="submit"]')
        .contains(/pay|confirm order/i)
        .click();
      cy.get('@confirmCardPaymentMockFail').should('have.been.called');

      // Verify error message is shown on the checkout page
      cy.contains('Your card was declined by the bank.', {
        timeout: 10000,
      }).should('be.visible');
      // Verify user is still on the checkout page
      cy.url().should('include', '/checkout/mockBookingFail123');
      // Verify form might be re-enabled or a "try again" option is available
      cy.get('button[type="submit"]')
        .contains(/pay|confirm order/i)
        .should('not.be.disabled');
    });
  });

  it('successfully books a free event', function () {
    // Copied from original, seems okay
    cy.visit(`/events/${this[freeEventAlias]}`);
    cy.contains('h2', 'E2E Free Event').should('be.visible');
    cy.get('input[name="numberOfTickets"]').clear().type('1');
    cy.intercept('POST', `${Cypress.env('apiUrl')}/bookings/`, {
      statusCode: 201,
      body: {
        id: 'mockBookingFree123',
        status: 'confirmed',
        event: this[freeEventAlias],
        number_of_tickets: 1,
        total_price: '0.00',
      },
    }).as('createFreeBooking');
    const alertStub = cy.stub();
    cy.on('window:alert', alertStub);
    cy.get('button')
      .contains(/book tickets/i)
      .click();
    cy.wait('@createFreeBooking');
    cy.wrap(alertStub).should(
      'have.been.calledOnceWith',
      'Booking successful! This event requires no payment and is confirmed.'
    );
    cy.url().should('include', '/dashboard/my-bookings');
    cy.contains('h1', /my bookings/i).should('be.visible');
  });
});
