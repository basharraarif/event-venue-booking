import axios from 'axios'; // Reuse or create a new instance if specific config needed

// Base API client from venueService - assuming it's configured for general use
// If not, create a new one:
const authApiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interfaces
export interface LoginCredentials {
  username?: string; // Support username or email login
  email?: string;
  password?: string; // Ensure password is not optional if always required by backend
}

export interface RegistrationData {
  username?: string;
  email?: string;
  password?: string;
  password2?: string; // Password confirmation
  // Add any other fields required by your backend registration endpoint
}

// User interface matching dj-rest-auth /user/ endpoint structure
// It often returns 'pk' as the primary key, along with other fields.
export interface User {
  pk: number; // Typically 'pk' from dj-rest-auth
  id?: number; // Sometimes 'id' might also be present or preferred in frontend
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  // Add any other fields your User model might have and are exposed
}

export interface AuthResponse {
  key: string; // This is the token from dj-rest-auth
  user?: User; // User details might be returned on login/registration by some configs
}


// API Functions

export const login = async (credentials: LoginCredentials): Promise<AuthResponse> => {
  try {
    const response = await authApiClient.post<AuthResponse>('/auth/login/', credentials);
    return response.data;
  } catch (error) {
    console.error('Login failed:', error);
    // Axios wraps errors, error.response.data often has backend messages
    throw error.response?.data || error;
  }
};

export const register = async (data: RegistrationData): Promise<AuthResponse | any> => {
  // Backend might return user details and token, or just a success message
  try {
    // dj-rest-auth registration usually requires password1 and password2
    const payload = { ...data, password1: data.password, password2: data.password2 || data.password };
    delete payload.password2; // remove if not needed directly by endpoint

    const response = await authApiClient.post<AuthResponse | any>('/auth/registration/', payload);
    return response.data;
  } catch (error) {
    console.error('Registration failed:', error);
    throw error.response?.data || error;
  }
};

export const logout = async (token: string | null): Promise<void> => {
  if (!token) return Promise.resolve(); // No token, nothing to do for backend
  try {
    await authApiClient.post('/auth/logout/', null, { // Logout endpoint might not need a body
      headers: {
        'Authorization': `Token ${token}`
      }
    });
  } catch (error) {
    console.error('Logout failed:', error);
    // Even if backend logout fails, frontend should clear its state.
    // Optionally re-throw if you want to notify user of backend logout failure.
    // throw error.response?.data || error;
  }
};

export const getCurrentUser = async (token: string): Promise<User> => {
  try {
    const response = await authApiClient.get<User>('/auth/user/', {
      headers: {
        'Authorization': `Token ${token}`
      }
    });
    // Map pk to id if your frontend User interface expects 'id' primarily
    if (response.data && response.data.pk && !response.data.id) {
        response.data.id = response.data.pk;
    }
    return response.data;
  } catch (error) {
    console.error('Fetching current user failed:', error);
    throw error.response?.data || error;
  }
};
