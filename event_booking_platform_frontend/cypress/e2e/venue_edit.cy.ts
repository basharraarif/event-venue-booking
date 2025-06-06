describe('Venue Edit Page Access', () => {
  const venueId = '1'; // Example venue ID
  const editUrl = `/venues/${venueId}/edit`;
  const loginUrl = '/login'; // Assuming this is your login page URL

  const mockVenueData = {
    id: venueId,
    name: 'Test Venue for Edit',
    address: '123 Edit St',
    description: 'A lovely venue for editing purposes.',
    capacity: 100,
    amenities: ['WiFi', 'Projector'],
    pricing_per_hour: '120.00',
    pricing_per_day: '800.00',
    is_available: true,
    // created_at and updated_at are usually handled by backend
  };

  it('should redirect unauthenticated users to the login page', () => {
    cy.visit(editUrl);
    cy.url().should('include', loginUrl);
    // Assuming your login page has a distinctive element, e.g., a heading
    cy.get('h1').contains('Login to Your Account').should('be.visible');
  });

  it('should allow authenticated users to access the edit page and see pre-filled form', () => {
    // Simulate login by setting auth token in localStorage
    // This token name ('authToken') must match what your AuthContext/withAuth HOC expects
    localStorage.setItem('authToken', 'fake-e2e-auth-token');

    // Mock the API call for fetching venue details for the form
    cy.intercept('GET', `/api/venues/${venueId}/`, {
      statusCode: 200,
      body: mockVenueData, // Ensure this matches the structure expected by VenueForm's initialData
    }).as('getVenueDetails');

    cy.visit(editUrl);

    // Wait for the API call to fetch venue details
    cy.wait('@getVenueDetails');

    // Check that the URL is the edit page URL
    cy.url().should('include', editUrl);

    // Check for a distinctive element on the edit page, e.g., the page title
    // The title is dynamic: "Edit Venue: {venue.name}"
    cy.get('h1').contains(`Edit Venue: ${mockVenueData.name}`).should('be.visible');

    // Check if form fields are pre-filled with mock data
    cy.get('input[name="name"]').should('have.value', mockVenueData.name);
    cy.get('input[name="address"]').should('have.value', mockVenueData.address);
    cy.get('textarea[name="description"]').should('have.value', mockVenueData.description);
    cy.get('input[name="capacity"]').should('have.value', mockVenueData.capacity.toString());
    cy.get('input[name="pricing_per_hour"]').should('have.value', mockVenueData.pricing_per_hour);
    // For amenities, it might be more complex (e.g., multi-select or tags)
    // For simplicity, we'll assume amenities are handled if the other fields are correct.
    // Depending on how is_available is rendered (checkbox, select), adjust the check:
    // Example for a checkbox:
    // if (mockVenueData.is_available) {
    //   cy.get('input[name="is_available"]').should('be.checked');
    // } else {
    //   cy.get('input[name="is_available"]').should('not.be.checked');
    // }
    // For this example, we'll assume the form is correctly loading if name/address/etc. are there.

    cy.get('button[type="submit"]').contains('Update Venue').should('be.visible');
  });

  afterEach(() => {
    // Clear localStorage after each test to ensure a clean slate for the next test
    localStorage.removeItem('authToken');
  });
});
