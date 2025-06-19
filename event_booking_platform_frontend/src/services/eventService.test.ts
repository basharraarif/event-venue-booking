import eventService, { GetEventsParams } from './eventService';
import axiosInstance from './axiosInstance';

jest.mock('./axiosInstance');
const mockedAxiosInstance = axiosInstance as jest.Mocked<typeof axiosInstance>;

describe('eventService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('getEvents', () => {
    it('should call GET /events-management/events/ with params and return data', async () => {
      const mockEvents = [{ id: 'e1', name: 'Event 1' }];
      const params: GetEventsParams = { name: 'Test Event' };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockEvents });

      const result = await eventService.getEvents(params);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(
        '/events-management/events/',
        { params }
      );
      expect(result).toEqual(mockEvents);
    });

    it('should call GET /events-management/events/ without params if none provided', async () => {
      const mockEvents = [{ id: 'e2', name: 'Event 2' }];
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockEvents });

      const result = await eventService.getEvents();

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(
        '/events-management/events/',
        { params: undefined }
      );
      expect(result).toEqual(mockEvents);
    });

    it('should throw error if API call fails for getEvents', async () => {
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Network Error'));
      await expect(eventService.getEvents()).rejects.toThrow('Network Error');
    });
  });

  describe('getEventById', () => {
    it('should call GET /events-management/events/{id}/ and return data', async () => {
      const eventId = 'e123';
      const mockEvent = { id: eventId, name: 'Specific Event' };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockEvent });

      const result = await eventService.getEventById(eventId);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(
        `/events-management/events/${eventId}/`
      );
      expect(result).toEqual(mockEvent);
    });

    it('should throw error if API call fails for getEventById', async () => {
      const eventId = 'e123';
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Not Found'));
      await expect(eventService.getEventById(eventId)).rejects.toThrow(
        'Not Found'
      );
    });
  });

  describe('getCategories', () => {
    it('should call GET /events-management/categories/ and return data', async () => {
      const mockCategories = [{ id: 'c1', name: 'Category 1' }];
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockCategories });

      const result = await eventService.getCategories();

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(
        '/events-management/categories/'
      );
      expect(result).toEqual(mockCategories);
    });

    it('should throw error if API call fails for getCategories', async () => {
      mockedAxiosInstance.get.mockRejectedValueOnce(
        new Error('Categories Fetch Error')
      );
      await expect(eventService.getCategories()).rejects.toThrow(
        'Categories Fetch Error'
      );
    });
  });
});
