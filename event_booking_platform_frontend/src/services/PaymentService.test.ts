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
        const mockPaymentData = { id: paymentId, status: 'succeeded', amount: "100.00", currency: "USD" }; // More complete mock
        mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockPaymentData });

        const result = await PaymentService.getPaymentDetails(paymentId);

        expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/payments/view/${paymentId}/`); // Updated URL
        expect(result).toEqual(mockPaymentData);
    });

    it('should throw error on failure for getPaymentDetails', async () => {
        const paymentId = 'test-payment-id';
        const mockError = new Error('Network Error');
        mockedAxiosInstance.get.mockRejectedValueOnce(mockError);

        await expect(PaymentService.getPaymentDetails(paymentId)).rejects.toThrow('Network Error');
        expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/payments/view/${paymentId}/`); // Updated URL
    });
  });

  describe('getBookingDetails', () => {
    it('should call the correct endpoint and return data on success', async () => {
      const bookingId = 'test-booking-id';
      const mockBookingData = {
        id: bookingId,
        event_details: { name: 'Test Event', ticket_price: '10.00' },
        number_of_tickets: 2,
        total_price: '20.00',
        status: 'pending_payment'
      };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockBookingData });

      const result = await PaymentService.getBookingDetails(bookingId);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/bookings/${bookingId}/`);
      expect(result).toEqual(mockBookingData);
    });

    it('should throw error on failure for getBookingDetails', async () => {
      const bookingId = 'test-booking-id';
      const mockError = new Error('Fetch Booking Error');
      mockedAxiosInstance.get.mockRejectedValueOnce(mockError);

      await expect(PaymentService.getBookingDetails(bookingId)).rejects.toThrow('Fetch Booking Error');
      expect(mockedAxiosInstance.get).toHaveBeenCalledWith(`/bookings/${bookingId}/`);
    });
  });

  describe('confirmCardPayment', () => {
    const mockStripe = {
      confirmCardPayment: jest.fn(),
    };
    const mockCardElement = {}; // Dummy object for card element
    const clientSecret = 'cs_test_secret';
    const billingDetails = { name: 'Test User', email: 'test@example.com' };

    beforeEach(() => {
      mockStripe.confirmCardPayment.mockClear();
    });

    it('should call stripe.confirmCardPayment with correct parameters and resolve on success', async () => {
      const mockPaymentIntent = { id: 'pi_test', status: 'succeeded' };
      mockStripe.confirmCardPayment.mockResolvedValueOnce({ paymentIntent: mockPaymentIntent });

      const result = await PaymentService.confirmCardPayment(
        mockStripe,
        clientSecret,
        mockCardElement,
        billingDetails
      );

      expect(mockStripe.confirmCardPayment).toHaveBeenCalledWith(clientSecret, {
        payment_method: {
          card: mockCardElement,
          billing_details: billingDetails,
        },
      });
      expect(result).toEqual({ paymentIntent: mockPaymentIntent });
    });

    it('should reject with an error if stripe.confirmCardPayment returns an error', async () => {
      const mockError = { message: 'Stripe card confirmation failed' };
      mockStripe.confirmCardPayment.mockResolvedValueOnce({ error: mockError }); // Stripe API returns error in a resolved promise with an error key

      await expect(
        PaymentService.confirmCardPayment(mockStripe, clientSecret, mockCardElement, billingDetails)
      ).rejects.toEqual(mockError);

      expect(mockStripe.confirmCardPayment).toHaveBeenCalledWith(clientSecret, {
        payment_method: {
          card: mockCardElement,
          billing_details: billingDetails,
        },
      });
    });

    it('should reject if stripe instance is not provided', async () => {
      await expect(
        PaymentService.confirmCardPayment(null, clientSecret, mockCardElement, billingDetails)
      ).rejects.toEqual('Stripe.js or CardElement not initialized.');
    });

    it('should reject if cardElement is not provided', async () => {
      await expect(
        PaymentService.confirmCardPayment(mockStripe, clientSecret, null, billingDetails)
      ).rejects.toEqual('Stripe.js or CardElement not initialized.');
    });

    it('should reject with an error if stripe.confirmCardPayment throws an exception', async () => {
      const mockException = new Error('Unexpected Stripe error');
      mockStripe.confirmCardPayment.mockRejectedValueOnce(mockException);

      await expect(
        PaymentService.confirmCardPayment(mockStripe, clientSecret, mockCardElement, billingDetails)
      ).rejects.toEqual(mockException);
    });
  });
});
