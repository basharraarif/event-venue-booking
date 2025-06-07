describe('Venue Listing Page - Basic Display', () => {
  beforeEach(() => {
    // For basic display, we assume some venues might exist or none.
    // Intercepting the initial call helps stabilize tests.
    cy.intercept('GET', '/api/venues*page=1*').as('getInitialVenues');
    cy.visit('/venues');
    cy.wait('@getInitialVenues', { timeout: 10000 }); // Wait for initial load
  });

  it('should display the main page title "Venues"', () => {
    cy.get('h1').contains('Venues').should('be.visible'); // From VenueList.tsx
  });

  it('should display venue cards if venues exist, or a "no venues" message', () => {
    cy.get('body').then(($body) => {
      if ($body.find('[data-cy="venue-card"]').length > 0) {
        cy.log('Venue cards found');
        cy.get('[data-cy="venue-card"]').first().should('be.visible');
      } else if ($body.find('[data-cy="no-venues-message"]').length > 0) {
        cy.log('No venues message found');
        cy.get('[data-cy="no-venues-message"]').should('be.visible');
      } else if ($body.find('[data-cy="loading-venues-message"]').length > 0) {
        cy.log('Still loading, waiting a bit more.'); // Should have been caught by wait in beforeEach
        cy.get('[data-cy="loading-venues-message"]', { timeout: 10000 }).should('not.exist');
        // Re-check after potential extended loading
        if ($body.find('[data-cy="venue-card"]').length > 0) {
            cy.log('Venue cards found after extended wait');
        } else {
            cy.get('[data-cy="no-venues-message"]').should('be.visible');
        }
      }
      else {
        // This case might indicate an error page or unexpected state.
        cy.log('Neither venue cards nor "no venues" message found. Error page?');
        cy.get('[data-cy="error-venues-message"]').should('be.visible');
      }
    });
  });

  it('should display pagination controls if venues exist', () => {
    cy.get('body').then(($body) => {
      if ($body.find('[data-cy="venue-card"]').length > 0) {
        cy.get('[data-cy="pagination-page-display"]').should('be.visible');
        cy.get('[data-cy="pagination-prev-button"]').should('be.visible');
        cy.get('[data-cy="pagination-next-button"]').should('be.visible');
      } else {
        cy.log('No venues, so no pagination expected.');
      }
    });
  });

  it('should have "Create New Venue" link(s)', () => {
    // VenueList component has this link, and it might also be in a layout if this page is part of a larger app structure
    cy.get('a').contains('Create New Venue').should('be.visible');
  });
});

describe('Venue Listing - Filtering and Searching', () => {
  // Mocked data for consistent testing of filtering/searching
  const mockVenuesSeed = [
    { id: 1, name: 'Grand Plaza Hall', address: '123 Main St', capacity: 200, is_available: true, pricing_per_hour: '150.00', description: 'Opulent hall for grand events.', amenities: {wifi: true, stage: true} },
    { id: 2, name: 'Cozy Corner Room', address: '456 Oak Ave', capacity: 50, is_available: false, pricing_per_hour: '50.00', description: 'Perfect for small meetings.', amenities: {projector: true} },
    { id: 3, name: 'Tech Conference Center', address: '789 Pine Rd', capacity: 500, is_available: true, pricing_per_hour: '300.00', description: 'State-of-the-art facility.', amenities: {wifi: true, parking: true, catering: true} },
    { id: 4, name: 'Riverside Pavilion', address: '101 River Bend', capacity: 100, is_available: true, pricing_per_hour: '80.00', description: 'Scenic outdoor setting.', amenities: {outdoor_space: true} },
    { id: 5, name: 'Downtown Studio Loft', address: '55 Central Sq', capacity: 75, is_available: true, pricing_per_hour: '120.00', description: 'Chic urban space.', amenities: {wifi: true, kitchen: true} },
  ];

  beforeEach(() => {
    // Intercept the initial GET request for venues (page 1, no filters)
    cy.intercept('GET', '/api/venues*', (req) => {
        // This initial intercept will catch any call to /api/venues.
        // We can refine it based on query parameters if needed for specific initial states.
        // For now, assume it's the default load.
        if (!req.url.includes('?')) { // A very basic check for no query params
            req.reply({
                statusCode: 200,
                body: { results: mockVenuesSeed, count: mockVenuesSeed.length, next: null, previous: null },
            });
        }
        // Let other specific intercepts handle filtered requests
    }).as('getInitialVenues');

    cy.visit('/venues');
    cy.wait('@getInitialVenues', {timeout: 10000});
  });

  it('should filter venues by search term (name)', () => {
    const searchTerm = 'Grand Plaza';
    const expectedResult = mockVenuesSeed.filter(v => v.name.includes('Grand Plaza'));
    cy.intercept('GET', `/api/venues*search=${encodeURIComponent(searchTerm)}*`, {
      statusCode: 200,
      body: { results: expectedResult, count: expectedResult.length, next: null, previous: null },
    }).as('getVenuesBySearch');

    cy.get('[data-cy="search-input"]').clear().type(searchTerm);
    cy.wait('@getVenuesBySearch');

    cy.get('[data-cy="venue-card"]').should('have.length', expectedResult.length);
    if (expectedResult.length > 0) {
      cy.get('[data-cy="venue-card"]').first().find('[data-cy="venue-name"]').should('contain.text', 'Grand Plaza Hall');
    }
  });

  it('should filter venues by minimum capacity', () => {
    const minCapacity = 150;
    const expectedResult = mockVenuesSeed.filter(v => v.capacity >= minCapacity);
    cy.intercept('GET', `/api/venues*capacity__gte=${minCapacity}*`, {
      statusCode: 200,
      body: { results: expectedResult, count: expectedResult.length, next: null, previous: null },
    }).as('getVenuesByCapacity');

    cy.get('[data-cy="filter-capacity-input"]').clear().type(minCapacity.toString());
    cy.wait('@getVenuesByCapacity');

    cy.get('[data-cy="venue-card"]').should('have.length', expectedResult.length);
    cy.get('[data-cy="venue-card"]').each(($card) => {
      cy.wrap($card).find('[data-cy="venue-capacity"]').invoke('text').then(text => {
        const capacity = parseInt(text.replace('Capacity: ', ''), 10);
        expect(capacity).to.be.gte(minCapacity);
      });
    });
  });

  it('should filter venues by availability (Available)', () => {
    const expectedResult = mockVenuesSeed.filter(v => v.is_available);
    cy.intercept('GET', `/api/venues*is_available=true*`, {
      statusCode: 200,
      body: { results: expectedResult, count: expectedResult.length, next: null, previous: null },
    }).as('getVenuesByAvailability');

    cy.get('[data-cy="filter-availability-select"]').select('true'); // 'true' for Available
    cy.wait('@getVenuesByAvailability');

    cy.get('[data-cy="venue-card"]').should('have.length', expectedResult.length);
    cy.get('[data-cy="venue-card"]').each(($card) => {
      cy.wrap($card).find('[data-cy="venue-availability-status"]').should('contain.text', 'Available');
    });
  });

  it('should filter venues by price range (e.g., $70 to $160 per hour)', () => {
    const minPrice = 70;
    const maxPrice = 160;
    const expectedResult = mockVenuesSeed.filter(v => {
      const price = parseFloat(v.pricing_per_hour);
      return price >= minPrice && price <= maxPrice;
    });
    cy.intercept('GET', `/api/venues*pricing_per_hour__gte=${minPrice}*pricing_per_hour__lte=${maxPrice}*`, {
      statusCode: 200,
      body: { results: expectedResult, count: expectedResult.length, next: null, previous: null },
    }).as('getVenuesByPrice');

    cy.get('[data-cy="filter-min-price-input"]').clear().type(minPrice.toString());
    // Wait for debounce and API call if inputs trigger individually
    // For this test, assume combined effect or last action triggers the main call
    cy.get('[data-cy="filter-max-price-input"]').clear().type(maxPrice.toString());
    cy.wait('@getVenuesByPrice');

    cy.get('[data-cy="venue-card"]').should('have.length', expectedResult.length);
    cy.get('[data-cy="venue-card"]').each(($card) => {
      cy.wrap($card).find('[data-cy="venue-price-per-hour"]').invoke('text').then(text => {
        const price = parseFloat(text.replace('Price per hour: $', ''));
        expect(price).to.be.gte(minPrice);
        expect(price).to.be.lte(maxPrice);
      });
    });
  });

  it('should show "No venues match" for a search with no results', () => {
    const searchTerm = 'XYZUnfindableVenue123';
    cy.intercept('GET', `/api/venues*search=${encodeURIComponent(searchTerm)}*`, {
      statusCode: 200,
      body: { results: [], count: 0, next: null, previous: null },
    }).as('getNoResults');

    cy.get('[data-cy="search-input"]').clear().type(searchTerm);
    cy.wait('@getNoResults');

    cy.get('[data-cy="venue-card"]').should('not.exist');
    cy.get('[data-cy="no-venues-message"]').should('be.visible');
  });

  it('should paginate to the next page', () => {
    // For this test, we need to ensure the initial load mock allows pagination
    const initialResponse = {
        results: mockVenuesSeed.slice(0, 2), // Assume page size is 2 for this test
        count: mockVenuesSeed.length,
        next: '/api/venues?page=2', // Mock a next link
        previous: null,
    };
    const page2Response = {
        results: mockVenuesSeed.slice(2, 4),
        count: mockVenuesSeed.length,
        next: '/api/venues?page=3',
        previous: '/api/venues?page=1',
    };

    // Override the generic beforeEach intercept for this specific test's initial load
    cy.intercept('GET', '/api/venues*', initialResponse).as('getInitialPageForPagination');
    cy.visit('/venues');
    cy.wait('@getInitialPageForPagination');

    cy.get('[data-cy="venue-card"]').should('have.length', 2);
    cy.get('[data-cy="pagination-next-button"]').should('be.enabled').click();

    // Intercept the call for page 2
    cy.intercept('GET', '/api/venues*page=2*', page2Response).as('getPage2');
    cy.wait('@getPage2');

    cy.get('[data-cy="pagination-page-display"]').should('contain.text', 'Page 2');
    cy.get('[data-cy="venue-card"]').should('have.length', 2); // Assuming 2 items on page 2
    cy.get('[data-cy="venue-card"]').first().find('[data-cy="venue-name"]').should('contain.text', mockVenuesSeed[2].name);
    cy.get('[data-cy="pagination-prev-button"]').should('be.enabled');
  });

  // Test for clearing filters would require inputs to be cleared and a re-fetch.
  // Since there's no explicit "Clear Filters" button, this means manually clearing each input.
  // This can be complex to ensure it triggers a "show all" state without specific clear functionality.
  // A simpler test would be to apply a filter, then change it to something else or an empty value.
  it('should update results when a filter is cleared by user', () => {
    const searchTerm = 'Grand Plaza';
    const expectedResultSearch = mockVenuesSeed.filter(v => v.name.includes(searchTerm));
    cy.intercept('GET', `/api/venues*search=${encodeURIComponent(searchTerm)}*`, {
      body: { results: expectedResultSearch, count: expectedResultSearch.length },
    }).as('getSearch');

    cy.get('[data-cy="search-input"]').type(searchTerm);
    cy.wait('@getSearch');
    cy.get('[data-cy="venue-card"]').should('have.length', expectedResultSearch.length);

    // Now clear the search input
    // Intercept for when search is empty
    cy.intercept('GET', '/api/venues*', (req) => {
        if (!req.url.includes('search=') || req.url.includes('search=&') ) { // Simplistic check for empty search
             req.reply({ body: { results: mockVenuesSeed, count: mockVenuesSeed.length } });
        }
    }).as('getAfterClearSearch');

    cy.get('[data-cy="search-input"]').clear();
    cy.wait('@getAfterClearSearch');
    cy.get('[data-cy="venue-card"]').should('have.length', mockVenuesSeed.length);
  });

});
