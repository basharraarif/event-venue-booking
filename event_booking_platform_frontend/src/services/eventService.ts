import axiosInstance from './axiosInstance';

// Interface for Venue (can be simplified if only ID/name is needed for nesting)
export interface NestedVenue {
  id: string;
  name: string;
  address?: string;
  capacity?: number | null; // Add capacity here
}

// Interface for Organizer/User (can be simplified)
export interface NestedUser {
  id: string; // Assuming User model ID is string (like UUID) or number
  username: string;
  email?: string; // Optional
}

// Interface for Category (assuming categories are returned as strings or simple objects)
// If categories are objects with id/name, define a NestedCategory interface
// For now, assuming array of strings (names) as per EventSerializer in backend
export type CategoryType = string | { id: string; name: string };


export interface Event {
  id: string; // Assuming UUID
  name: string;
  description?: string | null;
  venue: string; // Venue ID (still useful for FK relations)
  venue_details?: NestedVenue; // Expanded venue details
  organizer: string; // User ID
  organizer_username?: string; // Read-only from serializer
  categories: CategoryType[];
  start_time: string;
  end_time: string;
  status: 'upcoming' | 'ongoing' | 'past' | 'cancelled';
  ticket_price: string;
  max_capacity?: number | null;      // From backend Event.max_capacity
  active_tickets_count?: number; // From backend (e.g., SerializerMethodField)
  // venue_capacity is effectively venue_details.capacity
  created_at?: string;
  updated_at?: string;
}

// For query parameters, e.g., for filtering
export interface Category {
  id: string; // Or number, depending on your backend
  name: string;
  description?: string | null;
}

export interface GetEventsParams {
  name?: string;
  venue?: string; // Venue ID
  organizer?: string; // Organizer User ID
  status?: 'upcoming' | 'ongoing' | 'past' | 'cancelled';
  category_name?: string;
  start_time_after?: string; // YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
  start_time_before?: string; // YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
  // Add other potential filter params here
}

const eventService = {
  getEvents: async (params?: GetEventsParams): Promise<Event[]> => {
    try {
      const response = await axiosInstance.get<Event[]>('/events-management/events/', { params });
      return response.data;
    } catch (error: any) {
      console.error('Error fetching events:', error.response?.data || error.message);
      throw error;
    }
  },

  getEventById: async (id: string): Promise<Event> => {
    try {
      const response = await axiosInstance.get<Event>(`/events-management/events/${id}/`);
      return response.data;
    } catch (error: any) {
      console.error(`Error fetching event ${id}:`, error.response?.data || error.message);
      throw error;
    }
  },

  getCategories: async (): Promise<Category[]> => {
    try {
      const response = await axiosInstance.get<Category[]>('/events-management/categories/');
      return response.data;
    } catch (error: any) {
      console.error('Error fetching categories:', error.response?.data || error.message);
      throw error;
    }
  },

  // Placeholder for createEvent if needed later
  // createEvent: async (eventData: Omit<Event, 'id' | 'created_at' | 'updated_at'>): Promise<Event> => {
  //   try {
  //     const response = await axiosInstance.post<Event>('/events-management/events/', eventData);
  //     return response.data;
  //   } catch (error: any) {
  //     console.error('Error creating event:', error.response?.data || error.message);
  //     throw error;
  //   }
  // },
};

export default eventService;
