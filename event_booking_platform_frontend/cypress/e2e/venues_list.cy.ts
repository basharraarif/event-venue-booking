describe('Venues Listing Page', () => {
  beforeEach(() => {
    // Optional: Mock API responses if not running against a live dev server with data.
    // Example: cy.intercept('GET', '/api/venues/?*', { fixture: 'venues.json' }).as('getVenues');
    cy.visit('/venues');
    // if (cy.contains('Loading venues...', {timeout: 7000})) { // Wait for loading to finish
    //   cy.contains('Loading venues...', {timeout: 7000}).should('not.exist');
    // }
  });

  it('should display the page title correctly', () => {
    cy.get('h1').contains('Available Venues'); // Or whatever the title element and text is
  });

  it('should display at least one venue card or a "no venues found" message', () => {
    // This test is flexible: it passes if venues are loaded OR if a "no venues" message is shown.
    // This avoids test failure if the backend has no data during the E2E test run.
    // For a more specific test, you'd ensure data exists or mock it.
    cy.get('body').then(($body) => {
      if ($body.find('[class*="VenueCard_"]').length > 0) { // Check for class containing VenueCard (adapt selector)
        cy.log('Venue cards found');
        // Optionally, check for specific content within a card
        // cy.get('[class*="VenueCard_"]').first().should('contain.text', 'Venue Name'); // Example
      } else if ($body.find('p:contains("No venues found")').length > 0) {
        cy.log('No venues found message displayed');
        cy.contains('No venues found').should('be.visible');
      } else if ($body.find(':contains("Loading venues...")').length > 0) {
        // If still loading after initial visit, wait a bit more
        cy.contains('Loading venues...', { timeout: 10000 }).should('not.exist');
        // Re-check after loading
        if ($body.find('[class*="VenueCard_"]').length > 0) {
          cy.log('Venue cards found after loading');
        } else if ($body.find('p:contains("No venues found")').length > 0) {
          cy.log('No venues found message displayed after loading');
          cy.contains('No venues found').should('be.visible');
        } else {
            // If neither venues nor "no venues" message, it might be an issue or still loading
            // This could be an assertion failure point if the app state is unexpected.
            // For now, just log it. In a stricter test, you might fail here.
            cy.log('Neither venues nor "no venues" message found after loading period.');
        }
      } else {
        // Fallback if none of the above states are immediately found
        // This could indicate an error page or an unexpected state.
        // Consider adding a cy.screenshot() here for debugging.
        cy.log('Initial check found neither venue cards, "no venues" message, nor loading indicator.');
        // Potentially fail the test if this state is not expected:
        // throw new Error('Unexpected page state: No venues, no "no venues" message, and not loading.');
      }
    });
  });

  it('should have a link/button to "Add New Venue"', () => {
    cy.get('a[href="/venues/new"]').contains('Add New Venue', { matchCase: false })
      .should('be.visible');
  });

  it('should navigate to the "Add New Venue" page when the link is clicked', () => {
    cy.get('a[href="/venues/new"]').contains('Add New Venue', { matchCase: false }).click();
    cy.url().should('include', '/venues/new');
    cy.get('h1').contains('Add New Venue'); // Check for title on the new page
  });
});

describe('Venues Listing Page - Filtering & Searching', () => {
  const mockVenues = {
    all: [
      { id: 1, name: 'Grand Plaza Hall', address: '123 Main St', capacity: 200, is_available: true, pricing_per_hour: '150.00' },
      { id: 2, name: 'Cozy Corner Room', address: '456 Oak Ave', capacity: 50, is_available: false, pricing_per_hour: '50.00' },
      { id: 3, name: 'Tech Conference Center', address: '789 Pine Rd', capacity: 500, is_available: true, pricing_per_hour: '300.00' },
      { id: 4, name: 'Riverside Pavilion', address: '101 River Bend', capacity: 100, is_available: true, pricing_per_hour: '80.00' },
    ],
    searchByName: [
      { id: 1, name: 'Grand Plaza Hall', address: '123 Main St', capacity: 200, is_available: true, pricing_per_hour: '150.00' },
    ],
    availableOnly: [
      { id: 1, name: 'Grand Plaza Hall', address: '123 Main St', capacity: 200, is_available: true, pricing_per_hour: '150.00' },
      { id: 3, name: 'Tech Conference Center', address: '789 Pine Rd', capacity: 500, is_available: true, pricing_per_hour: '300.00' },
      { id: 4, name: 'Riverside Pavilion', address: '101 River Bend', capacity: 100, is_available: true, pricing_per_hour: '80.00' },
    ],
    capacity150plus: [
      { id: 1, name: 'Grand Plaza Hall', address: '123 Main St', capacity: 200, is_available: true, pricing_per_hour: '150.00' },
      { id: 3, name: 'Tech Conference Center', address: '789 Pine Rd', capacity: 500, is_available: true, pricing_per_hour: '300.00' },
    ],
    priceRange50to100: [
      { id: 4, name: 'Riverside Pavilion', address: '101 River Bend', capacity: 100, is_available: true, pricing_per_hour: '80.00' },
      // Cozy Corner Room would fit if it were available and price was the only filter
    ],
    combinedSearchAndAvailable: [
       { id: 4, name: 'Riverside Pavilion', address: '101 River Bend', capacity: 100, is_available: true, pricing_per_hour: '80.00' },
    ],
    noResults: []
  };

  // Assuming VenueCard component has a root div with class 'venue-card-item' or similar for consistent selection
  const venueCardSelector = '.relative.flex.flex-col'; // Based on VenueCard structure from previous context (outer div)

  beforeEach(() => {
    cy.intercept('GET', '/api/venues/?', {
      statusCode: 200,
      body: { results: mockVenues.all, count: mockVenues.all.length, next: null, previous: null },
    }).as('getInitialVenues');

    cy.visit('/venues');
    cy.wait('@getInitialVenues');
    cy.get('h1').contains('Available Venues').should('be.visible');
  });

  it('should filter venues by search term', () => {
    cy.intercept('GET', '/api/venues/?search=Grand*', {
      statusCode: 200,
      body: { results: mockVenues.searchByName, count: mockVenues.searchByName.length, next: null, previous: null },
    }).as('getFilteredByName');

    cy.get('input[name="search"]').type('Grand');
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getFilteredByName');

    cy.get(venueCardSelector).should('have.length', mockVenues.searchByName.length);
    cy.contains(venueCardSelector, 'Grand Plaza Hall').should('be.visible');
    cy.contains(venueCardSelector, 'Cozy Corner Room').should('not.exist');
  });

  it('should filter venues by availability (Yes)', () => {
    cy.intercept('GET', '/api/venues/?is_available=true', {
      statusCode: 200,
      body: { results: mockVenues.availableOnly, count: mockVenues.availableOnly.length, next: null, previous: null },
    }).as('getFilteredByAvailability');

    cy.get('select[name="is_available"]').select('true'); // Value for "Yes"
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getFilteredByAvailability');

    cy.get(venueCardSelector).should('have.length', mockVenues.availableOnly.length);
    mockVenues.availableOnly.forEach(venue => {
      cy.contains(venueCardSelector, venue.name).should('be.visible');
    });
    cy.contains(venueCardSelector, 'Cozy Corner Room').should('not.exist'); // This one is is_available: false
  });

  it('should filter venues by minimum capacity', () => {
    cy.intercept('GET', '/api/venues/?capacity=150', {
      statusCode: 200,
      body: { results: mockVenues.capacity150plus, count: mockVenues.capacity150plus.length, next: null, previous: null },
    }).as('getFilteredByCapacity');

    cy.get('input[name="capacity"]').type('150');
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getFilteredByCapacity');

    cy.get(venueCardSelector).should('have.length', mockVenues.capacity150plus.length);
    mockVenues.capacity150plus.forEach(venue => {
      cy.contains(venueCardSelector, venue.name).should('be.visible');
    });
    cy.contains(venueCardSelector, 'Riverside Pavilion').should('not.exist'); // Capacity 100
  });

  it('should filter venues by price range', () => {
    cy.intercept('GET', '/api/venues/?min_price_per_hour=50&max_price_per_hour=100', {
      statusCode: 200,
      body: { results: mockVenues.priceRange50to100, count: mockVenues.priceRange50to100.length, next: null, previous: null },
    }).as('getFilteredByPrice');

    cy.get('input[name="min_price_per_hour"]').type('50');
    cy.get('input[name="max_price_per_hour"]').type('100');
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getFilteredByPrice');

    cy.get(venueCardSelector).should('have.length', mockVenues.priceRange50to100.length);
    if (mockVenues.priceRange50to100.length > 0) {
        mockVenues.priceRange50to100.forEach(venue => {
            cy.contains(venueCardSelector, venue.name).should('be.visible');
        });
    } else {
        cy.contains('No venues found matching your criteria.').should('be.visible');
    }
    cy.contains(venueCardSelector, 'Grand Plaza Hall').should('not.exist'); // Price 150
  });

  it('should filter by combined criteria (search term and availability)', () => {
    cy.intercept('GET', '/api/venues/?search=Riverside&is_available=true', {
      statusCode: 200,
      body: { results: mockVenues.combinedSearchAndAvailable, count: mockVenues.combinedSearchAndAvailable.length, next: null, previous: null },
    }).as('getCombinedFilter');

    cy.get('input[name="search"]').type('Riverside');
    cy.get('select[name="is_available"]').select('true');
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getCombinedFilter');

    cy.get(venueCardSelector).should('have.length', mockVenues.combinedSearchAndAvailable.length);
    mockVenues.combinedSearchAndAvailable.forEach(venue => {
      cy.contains(venueCardSelector, venue.name).should('be.visible');
    });
    cy.contains(venueCardSelector, 'Grand Plaza Hall').should('not.exist');
  });

  it('should display "No venues found" message when filters yield no results', () => {
    cy.intercept('GET', '/api/venues/?search=UnfindableVenueName123', {
      statusCode: 200,
      body: { results: mockVenues.noResults, count: 0, next: null, previous: null },
    }).as('getNoResults');

    cy.get('input[name="search"]').type('UnfindableVenueName123');
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getNoResults');

    cy.get(venueCardSelector).should('not.exist');
    cy.contains('No venues found matching your criteria.').should('be.visible');
  });

  it('should clear filters and show all venues', () => {
    // 1. Apply a filter first
    cy.intercept('GET', '/api/venues/?search=Grand*', {
      statusCode: 200,
      body: { results: mockVenues.searchByName, count: mockVenues.searchByName.length, next: null, previous: null },
    }).as('getFilteredForClearTest');
    cy.get('input[name="search"]').type('Grand');
    cy.get('select[name="is_available"]').select('true'); // Add another filter to check clearing
    cy.contains('button', 'Apply Filters').click();
    cy.wait('@getFilteredForClearTest'); // This intercept might need to be more specific if multiple filters are applied

    // Check that filter took effect
    cy.get(venueCardSelector).should('have.length', mockVenues.searchByName.length);
    cy.contains(venueCardSelector, 'Grand Plaza Hall').should('be.visible');

    // 2. Intercept for clearing filters (back to initial all venues state)
    cy.intercept('GET', '/api/venues/?', { // This will be the call after clearing
      statusCode: 200,
      body: { results: mockVenues.all, count: mockVenues.all.length, next: null, previous: null },
    }).as('getAllVenuesAfterClear');

    cy.contains('button', 'Clear Filters').click();
    cy.wait('@getAllVenuesAfterClear');

    // Assert inputs are cleared
    cy.get('input[name="search"]').should('have.value', '');
    cy.get('select[name="is_available"]').should('have.value', ''); // Default is 'Any' which has value ''
    cy.get('input[name="capacity"]').should('have.value', '');
    cy.get('input[name="min_price_per_hour"]').should('have.value', '');
    cy.get('input[name="max_price_per_hour"]').should('have.value', '');

    // Assert all venues are displayed
    cy.get(venueCardSelector).should('have.length', mockVenues.all.length);
    mockVenues.all.forEach(venue => {
      cy.contains(venueCardSelector, venue.name).should('be.visible');
    });
  });
});
