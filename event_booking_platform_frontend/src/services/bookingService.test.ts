import bookingService, { CreateBookingPayload, GetBookingsParams } from './bookingService';
import axiosInstance from './axiosInstance';

jest.mock('./axiosInstance');
const mockedAxiosInstance = axiosInstance as jest.Mocked<typeof axiosInstance>;

describe('bookingService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('getMyBookings', () => {
    it('should call GET /bookings/ with optional params and return data', async () => {
      const mockBookings = [{ id: 'b1', event: 'e1', number_of_tickets: 2 }];
      const params: GetBookingsParams = { status: 'confirmed' };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockBookings });

      const result = await bookingService.getMyBookings(params);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith('/bookings/', { params });
      expect(result).toEqual(mockBookings);
    });

    it('should call GET /bookings/ without params if none provided', async () => {
        const mockBookings = [{ id: 'b2', event: 'e2', number_of_tickets: 1 }];
        mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockBookings });

        const result = await bookingService.getMyBookings();

        expect(mockedAxiosInstance.get).toHaveBeenCalledWith('/bookings/', { params: undefined });
        expect(result).toEqual(mockBookings);
      });


    it('should throw error if API call fails for getMyBookings', async () => {
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Network Error'));
      await expect(bookingService.getMyBookings()).rejects.toThrow('Network Error');
    });
  });

  describe('getBookingById', () => {
    it('should call GET /bookings/{id}/ and return data', async () => {
      const bookingId = 'b123';
      const mockBooking = { id: bookingId, event: 'e1', number_of_tickets: 1 };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockBooking });

      const result = await bookingService.getBookingById(bookingId);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/bookings/${bookingId}/`);
      expect(result).toEqual(mockBooking);
    });

    it('should throw error if API call fails for getBookingById', async () => {
      const bookingId = 'b123';
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Not Found'));
      await expect(bookingService.getBookingById(bookingId)).rejects.toThrow('Not Found');
    });
  });

  describe('createBooking', () => {
    it('should call POST /bookings/ with payload and return data', async () => {
      const payload: CreateBookingPayload = { event: 'e1', number_of_tickets: 2 };
      const mockCreatedBooking = { id: 'bNew', ...payload, status: 'pending', total_price: '20.00' };
      mockedAxiosInstance.post.mockResolvedValueOnce({ data: mockCreatedBooking });

      const result = await bookingService.createBooking(payload);

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/bookings/', payload);
      expect(result).toEqual(mockCreatedBooking);
    });

    it('should throw error if API call fails for createBooking', async () => {
      const payload: CreateBookingPayload = { event: 'e1', number_of_tickets: 2 };
      mockedAxiosInstance.post.mockRejectedValueOnce(new Error('Create Failed'));
      await expect(bookingService.createBooking(payload)).rejects.toThrow('Create Failed');
    });
  });

  describe('cancelBooking', () => {
    it('should call PATCH /bookings/{id}/ with status cancelled and return data', async () => {
      const bookingId = 'bCancel';
      const mockCancelledBooking = { id: bookingId, status: 'cancelled' };
      mockedAxiosInstance.patch.mockResolvedValueOnce({ data: mockCancelledBooking });

      const result = await bookingService.cancelBooking(bookingId);

      expect(mockedAxiosInstance.patch).toHaveBeenCalledWith(`/bookings/${bookingId}/`, { status: 'cancelled' });
      expect(result).toEqual(mockCancelledBooking);
    });

    it('should throw error if API call fails for cancelBooking', async () => {
      const bookingId = 'bCancelFail';
      mockedAxiosInstance.patch.mockRejectedValueOnce(new Error('Cancel Failed'));
      await expect(bookingService.cancelBooking(bookingId)).rejects.toThrow('Cancel Failed');
    });
  });
});
