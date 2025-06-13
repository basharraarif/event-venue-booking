import axiosInstance from './axiosInstance'; // Assuming you have an axios instance configured

export interface PaymentIntentPayload {
  booking_id: string;
}

export interface PaymentIntentResponse {
  client_secret: string;
  payment_id: string; // UUID of the payment record in your backend
  error?: string; // Optional error message
}

// Define simplified interfaces for Payment and Booking details
// In a real app, these might be more detailed and live in a dedicated types file.
export interface Payment {
  id: string;
  booking_id: string;
  amount: string; // Typically string from backend DecimalFields
  currency: string;
  status: 'pending' | 'succeeded' | 'failed' | 'requires_action' | 'processing'; // Align with backend and Stripe statuses
  stripe_payment_intent_id: string;
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  event: string; // Assuming event ID, or could be a nested EventDetails object
  event_details?: { // Optional: if your serializer nests this
    name: string;
    ticket_price: string;
  };
  user: string; // User ID
  number_of_tickets: number;
  total_price: string;
  price_per_ticket_at_booking?: string; // Optional, but good for display
  booking_time: string;
  status: string; // e.g., 'pending_payment', 'confirmed', 'cancelled'
  payment_status: string; // e.g., 'pending', 'paid', 'failed', 'not_required'
  // any other fields needed by the frontend
}


const PaymentService = {
  createPaymentIntent: async (payload: PaymentIntentPayload): Promise<PaymentIntentResponse> => {
    try {
      const response = await axiosInstance.post<PaymentIntentResponse>('/payments/create-payment-intent/', payload);
      return response.data;
    } catch (error: any) {
      console.error('Error creating payment intent:', error.response?.data || error.message);
      return {
        client_secret: '',
        payment_id: '',
        error: error.response?.data?.detail || error.response?.data?.error || 'Failed to create payment intent.'
      };
    }
  },

  getPaymentDetails: async (paymentId: string): Promise<Payment> => {
    try {
      // The backend URL for PaymentViewSet (ReadOnly) is likely /api/payments/view/{payment_id}/
      // Adjust if your PaymentViewSet is registered differently.
      // Based on previous backend setup, it was registered under /api/payments/view/
      const response = await axiosInstance.get<Payment>(`/payments/view/${paymentId}/`);
      return response.data;
    } catch (error: any) {
      console.error('Error fetching payment details:', error.response?.data || error.message);
      // Consider how you want to propagate errors. Throwing allows components to catch.
      // Or return an object with an error field. For now, re-throwing.
      throw error;
    }
  },

  // As per task, adding getBookingDetails here.
  // Note: A dedicated bookingService.ts might be a more common place for this.
  getBookingDetails: async (bookingId: string): Promise<Booking> => {
    try {
      const response = await axiosInstance.get<Booking>(`/bookings/${bookingId}/`);
      return response.data;
    } catch (error: any) {
      console.error('Error fetching booking details:', error.response?.data || error.message);
      throw error;
    }
  }
};

export default PaymentService;
