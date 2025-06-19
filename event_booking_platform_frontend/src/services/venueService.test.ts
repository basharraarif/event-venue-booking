import {
  getVenues,
  getVenueById,
  createVenue,
  updateVenue,
  deleteVenue,
  Venue,
} from './venueService';
import apiClient from './venueService'; // Import the named export

// Mock the apiClient (axios instance)
jest.mock('./venueService', () => ({
  __esModule: true, // this property makes it work for ESM modules
  ...jest.requireActual('./venueService'), // import and retain default exports
  default: {
    // Mock the default export (apiClient)
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  },
}));

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('Venue Service', () => {
  afterEach(() => {
    jest.clearAllMocks(); // Clear mocks after each test
  });

  // Test for getVenues
  describe('getVenues', () => {
    it('should fetch venues successfully', async () => {
      const mockVenueData = {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 1,
            name: 'Test Venue',
            address: '123 Test St',
            capacity: 100,
            amenities: [],
            pricing_per_hour: '10.00',
            pricing_per_day: '100.00',
            is_available: true,
            created_at: '2023-01-01T00:00:00Z',
            updated_at: '2023-01-01T00:00:00Z',
          },
        ],
      };
      mockApiClient.get.mockResolvedValue({ data: mockVenueData });

      const params = { page: 1 };
      const result = await getVenues(params);

      expect(mockApiClient.get).toHaveBeenCalledWith('/venues/', { params });
      expect(result).toEqual(mockVenueData);
    });

    it('should handle error when fetching venues', async () => {
      const errorMessage = 'Network Error';
      mockApiClient.get.mockRejectedValue(new Error(errorMessage));

      await expect(getVenues()).rejects.toThrow(errorMessage);
      expect(mockApiClient.get).toHaveBeenCalledWith('/venues/', {
        params: undefined,
      });
    });
  });

  // Test for getVenueById
  describe('getVenueById', () => {
    it('should fetch a single venue successfully', async () => {
      const mockVenue: Venue = {
        id: 1,
        name: 'Test Venue',
        address: '123 Test St',
        capacity: 100,
        amenities: [],
        pricing_per_hour: '10.00',
        pricing_per_day: '100.00',
        is_available: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z',
      };
      mockApiClient.get.mockResolvedValue({ data: mockVenue });

      const venueId = '1';
      const result = await getVenueById(venueId);

      expect(mockApiClient.get).toHaveBeenCalledWith(`/venues/${venueId}/`);
      expect(result).toEqual(mockVenue);
    });

    it('should handle error when fetching a single venue', async () => {
      const errorMessage = 'Venue not found';
      mockApiClient.get.mockRejectedValue(new Error(errorMessage));

      const venueId = '1';
      await expect(getVenueById(venueId)).rejects.toThrow(errorMessage);
      expect(mockApiClient.get).toHaveBeenCalledWith(`/venues/${venueId}/`);
    });
  });

  // Test for createVenue
  describe('createVenue', () => {
    it('should create a venue successfully', async () => {
      const venueData = {
        name: 'New Venue',
        address: '456 New St',
        capacity: 50,
        amenities: ['wifi'],
        pricing_per_hour: '15.00',
        pricing_per_day: '120.00',
        is_available: false,
      };
      const mockCreatedVenue: Venue = {
        id: 2,
        ...venueData,
        created_at: '2023-01-02T00:00:00Z',
        updated_at: '2023-01-02T00:00:00Z',
      };
      mockApiClient.post.mockResolvedValue({ data: mockCreatedVenue });

      const result = await createVenue(venueData);

      expect(mockApiClient.post).toHaveBeenCalledWith('/venues/', venueData);
      expect(result).toEqual(mockCreatedVenue);
    });

    it('should handle error when creating a venue', async () => {
      const venueData = {
        name: 'New Venue',
        address: '456 New St',
        capacity: 50,
        amenities: [],
        pricing_per_hour: '15.00',
        pricing_per_day: '120.00',
        is_available: false,
      };
      const errorMessage = 'Creation failed';
      mockApiClient.post.mockRejectedValue(new Error(errorMessage));

      await expect(createVenue(venueData)).rejects.toThrow(errorMessage);
      expect(mockApiClient.post).toHaveBeenCalledWith('/venues/', venueData);
    });
  });

  // Test for updateVenue
  describe('updateVenue', () => {
    it('should update a venue successfully', async () => {
      const venueId = '1';
      const venueUpdateData = { name: 'Updated Venue Name', capacity: 120 };
      const mockUpdatedVenue: Venue = {
        id: 1,
        name: 'Updated Venue Name',
        address: '123 Test St',
        capacity: 120,
        amenities: [],
        pricing_per_hour: '10.00',
        pricing_per_day: '100.00',
        is_available: true,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-03T00:00:00Z',
      };
      mockApiClient.put.mockResolvedValue({ data: mockUpdatedVenue });

      const result = await updateVenue(venueId, venueUpdateData);

      expect(mockApiClient.put).toHaveBeenCalledWith(
        `/venues/${venueId}/`,
        venueUpdateData
      );
      expect(result).toEqual(mockUpdatedVenue);
    });

    it('should handle error when updating a venue', async () => {
      const venueId = '1';
      const venueUpdateData = { name: 'Updated Venue Name' };
      const errorMessage = 'Update failed';
      mockApiClient.put.mockRejectedValue(new Error(errorMessage));

      await expect(updateVenue(venueId, venueUpdateData)).rejects.toThrow(
        errorMessage
      );
      expect(mockApiClient.put).toHaveBeenCalledWith(
        `/venues/${venueId}/`,
        venueUpdateData
      );
    });
  });

  // Test for deleteVenue
  describe('deleteVenue', () => {
    it('should delete a venue successfully', async () => {
      const venueId = '1';
      mockApiClient.delete.mockResolvedValue({}); // No data expected on successful delete

      await deleteVenue(venueId);

      expect(mockApiClient.delete).toHaveBeenCalledWith(`/venues/${venueId}/`);
    });

    it('should handle error when deleting a venue', async () => {
      const venueId = '1';
      const errorMessage = 'Deletion failed';
      mockApiClient.delete.mockRejectedValue(new Error(errorMessage));

      await expect(deleteVenue(venueId)).rejects.toThrow(errorMessage);
      expect(mockApiClient.delete).toHaveBeenCalledWith(`/venues/${venueId}/`);
    });
  });

  // Note: getVenuesByOwner is not in the provided venueService.ts
  // If it were, tests would be similar to getVenues, likely with an ownerId param.
});
