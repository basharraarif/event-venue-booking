import PaymentService from './PaymentService';
import axiosInstance from './axiosInstance'; // Mock this

jest.mock('./axiosInstance'); // Automatically mocks all exports

const mockedAxiosInstance = axiosInstance as jest.Mocked<typeof axiosInstance>;

describe('PaymentService', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('createPaymentIntent', () => {
    it('should call the correct endpoint and return data on success', async () => {
      const mockPayload = { booking_id: 'test-booking-id' };
      const mockResponse = { client_secret: 'cs_test', payment_id: 'pi_test' };

      mockedAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await PaymentService.createPaymentIntent(mockPayload);

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/payments/create-payment-intent/', mockPayload);
      expect(result).toEqual(mockResponse);
    });

    it('should return an error object on failure', async () => {
      const mockPayload = { booking_id: 'test-booking-id' };
      const mockError = { response: { data: { error: 'Backend error' } } };

      mockedAxiosInstance.post.mockRejectedValueOnce(mockError);

      const result = await PaymentService.createPaymentIntent(mockPayload);

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/payments/create-payment-intent/', mockPayload);
      expect(result).toEqual(expect.objectContaining({
        error: 'Backend error'
      }));
    });
  });

  describe('getPaymentDetails', () => {
    it('should call the correct endpoint and return data on success', async () => {
        const paymentId = 'test-payment-id';
        const mockPaymentData = { id: paymentId, status: 'succeeded', amount: 1000 };
        mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockPaymentData });

        const result = await PaymentService.getPaymentDetails(paymentId);

        expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/payments/${paymentId}/`);
        expect(result).toEqual(mockPaymentData);
    });

    it('should throw error on failure', async () => {
        const paymentId = 'test-payment-id';
        const mockError = new Error('Network Error');
        mockedAxiosInstance.get.mockRejectedValueOnce(mockError);

        await expect(PaymentService.getPaymentDetails(paymentId)).rejects.toThrow('Network Error');
        expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/payments/${paymentId}/`);
    });
  });
});
