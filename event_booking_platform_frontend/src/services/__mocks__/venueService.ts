// src/services/__mocks__/venueService.ts

// Mock implementation for getVenues
export const getVenues = jest.fn(() => Promise.resolve({ results: [], count: 0, next: null, previous: null }));

// Mock implementation for getVenueById
export const getVenueById = jest.fn((id: string) => {
  if (id === "1" || parseInt(id, 10) === 1) { // Allow string or number for ID in mock
    return Promise.resolve({
      id: 1,
      name: 'Mocked Venue Detail',
      address: '123 Mock St',
      capacity: 150,
      amenities: ['wifi', 'projector'],
      pricing_per_hour: '100.00',
      pricing_per_day: '700.00',
      is_available: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }
  return Promise.reject(new Error('Venue not found'));
});

// Mock implementation for createVenue
export const createVenue = jest.fn((venueData) => {
  return Promise.resolve({
    id: Date.now(), // Generate a mock ID
    ...venueData,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });
});

// Mock implementation for updateVenue
export const updateVenue = jest.fn((id, venueData) => {
  return Promise.resolve({
    id: parseInt(id, 10),
    ...venueData,
    name: venueData.name || 'Updated Mocked Venue', // Ensure name is present
    address: venueData.address || 'Updated Mock Address',
    capacity: venueData.capacity || 100,
    created_at: new Date().toISOString(), // Should not actually change
    updated_at: new Date().toISOString(),
  });
});

// Mock implementation for deleteVenue
export const deleteVenue = jest.fn(() => Promise.resolve());

// You might want to export the mock apiClient if tests need to inspect its usage,
// but typically mocking service functions is enough.
// export const apiClient = {
//   get: jest.fn(),
//   post: jest.fn(),
//   put: jest.fn(),
//   patch: jest.fn(),
//   delete: jest.fn(),
// };
