import axiosInstance from './axiosInstance';
import { NestedUser, NestedEvent } from './eventService'; // Assuming simplified nested types from eventService are suitable

// Interface for Booking, mirroring backend BookingSerializer structure as much as possible
export interface Booking {
  id: string; // UUID
  event: string; // Event ID (writable for create, though create might be via specific endpoint)
  event_details?: NestedEvent; // Read-only, nested object
  user?: string; // User ID (usually read-only, set by backend)
  user_details?: NestedUser; // Read-only, nested object
  number_of_tickets: number;
  price_per_ticket_at_booking?: string; // Decimal as string, read-only
  total_price: string; // Decimal as string, read-only
  booking_time: string; // ISO 8601 datetime string, read-only
  status: 'pending' | 'confirmed' | 'cancelled' | 'pending_payment'; // Added 'pending_payment'
}

export interface CreateBookingPayload {
  event: string; // Event ID
  number_of_tickets: number;
}

// For query parameters when fetching bookings
export interface GetBookingsParams {
  user?: string; // Filter by User ID
  event?: string; // Filter by Event ID
  status?: 'pending' | 'confirmed' | 'cancelled' | 'pending_payment'; // Added 'pending_payment'
  // Add other potential filter params here, e.g., date ranges
}

const bookingService = {
  // Fetches bookings for the currently authenticated user (token-based auth)
  getMyBookings: async (params?: GetBookingsParams): Promise<Booking[]> => {
    try {
      // The backend should automatically filter by user based on the token.
      // If explicit filtering by user ID is needed and allowed by backend:
      // const response = await axiosInstance.get<Booking[]>('/bookings/', { params: { ...params, user: userId } });
      const response = await axiosInstance.get<Booking[]>('/bookings/', { params }); // Assumes backend filters by authenticated user
      return response.data;
    } catch (error: any) {
      console.error('Error fetching my bookings:', error.response?.data || error.message);
      throw error;
    }
  },

  getBookingById: async (id: string): Promise<Booking> => {
    try {
      const response = await axiosInstance.get<Booking>(`/bookings/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error(`Error fetching booking ${id}:`, error.response?.data || error.message);
      throw error;
    }
  },

  createBooking: async (payload: CreateBookingPayload): Promise<Booking> => {
    try {
      const response = await axiosInstance.post<Booking>('/bookings/', payload);
      return response.data;
    } catch (error: any) {
      console.error('Error creating booking:', error.response?.data || error.message);
      throw error;
    }
  },

  // Example: Cancel a booking
  cancelBooking: async (id: string): Promise<Booking> => {
    try {
      // Backend might expect a PATCH with status: 'cancelled'
      const response = await axiosInstance.patch<Booking>(`/bookings/${id}/`, { status: 'cancelled' });
      return response.data;
    } catch (error: any) {
      console.error(`Error cancelling booking ${id}:`, error.response?.data || error.message);
      throw error;
    }
  }
};

export default bookingService;
