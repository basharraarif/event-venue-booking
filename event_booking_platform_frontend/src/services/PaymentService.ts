import axiosInstance from './axiosInstance'; // Assuming you have an axios instance configured

export interface PaymentIntentPayload {
  booking_id: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_id: string; // UUID of the payment record in your backend
  error?: string; // Optional error message
}

const PaymentService = {
  createPaymentIntent: async (payload: PaymentIntentPayload): Promise<PaymentIntentResponse> => {
    try {
      const response = await axiosInstance.post<PaymentIntentResponse>('/payments/create-payment-intent/', payload);
      return response.data;
    } catch (error: any) {
      // Handle errors, perhaps transform them into a consistent error response
      console.error('Error creating payment intent:', error.response?.data || error.message);
      return {
        client_secret: '',
        payment_id: '',
        error: error.response?.data?.error || 'Failed to create payment intent.'
      };
    }
  },

  getPaymentDetails: async (paymentId: string): Promise<any> => { // Define a proper type for payment details
    try {
      const response = await axiosInstance.get(`/payments/${paymentId}/`);
      return response.data;
    } catch (error: any) {
      console.error('Error fetching payment details:', error.response?.data || error.message);
      throw error; // Re-throw or handle as appropriate
    }
  }
};

export default PaymentService;
