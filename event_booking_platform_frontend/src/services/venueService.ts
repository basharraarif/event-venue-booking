import axios from 'axios';

// 1. Define the Venue interface
export interface Venue {
  id: number;
  name: string;
  address: string;
  capacity: number;
  amenities: Record<string, any> | string[]; // Can be a JSON object or an array of strings
  pricing_per_hour: string | null; // DecimalFields are often returned as strings
  pricing_per_day: string | null;  // DecimalFields are often returned as strings
  is_available: boolean;
  created_at: string; // DateTimeFields are typically returned as ISO strings
  updated_at: string; // DateTimeFields are typically returned as ISO strings
}

// 2. Create a base axios instance
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers['Authorization'] = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 3. Create the getVenues function
interface VenuesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Venue[];
}

export const getVenues = async (params?: any): Promise<VenuesResponse> => {
  try {
    const response = await apiClient.get<VenuesResponse>('/venues/', { params });
    return response.data;
  } catch (error) {
    console.error('Error fetching venues:', error);
    // It's good practice to throw the error or return a structured error response
    // For simplicity here, re-throwing, but you might want to handle it more gracefully
    throw error;
  }
};

// Example of a function to get a single venue by ID (if needed later)
export const getVenueById = async (id: string): Promise<Venue> => {
  try {
    const response = await apiClient.get<Venue>(`/venues/${id}/`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching venue with id ${id}:`, error);
    throw error;
  }
};

// Function to create a new venue
export const createVenue = async (venueData: Omit<Venue, 'id' | 'created_at' | 'updated_at'>): Promise<Venue> => {
  try {
    const response = await apiClient.post<Venue>('/venues/', venueData);
    return response.data;
  } catch (error) {
    console.error('Error creating venue:', error);
    throw error;
  }
};

// Function to update an existing venue
export const updateVenue = async (id: string, venueData: Partial<Omit<Venue, 'id' | 'created_at' | 'updated_at'>>): Promise<Venue> => {
  try {
    const response = await apiClient.put<Venue>(`/venues/${id}/`, venueData); // Or PATCH if you prefer partial updates
    return response.data;
  } catch (error) {
    console.error(`Error updating venue with id ${id}:`, error);
    throw error;
  }
};

// Function to delete a venue
export const deleteVenue = async (id: string): Promise<void> => {
  try {
    await apiClient.delete(`/venues/${id}/`);
  } catch (error) {
    console.error(`Error deleting venue with id ${id}:`, error);
    throw error;
  }
};
