import axiosInstance from './axiosInstance'; // Use the shared axiosInstance

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

export const login = async (
  credentials: LoginCredentials
): Promise<AuthResponse> => {
  try {
    const response = await axiosInstance.post<AuthResponse>(
      '/auth/login/',
      credentials
    ); // Use axiosInstance
    return response.data;
  } catch (error) {
    console.error('Login failed:', error);
    // Axios wraps errors, error.response.data often has backend messages
    throw error.response?.data || error;
  }
};

export const register = async (
  data: RegistrationData
): Promise<AuthResponse | any> => {
  // Backend might return user details and token, or just a success message
  try {
    // dj-rest-auth registration usually requires password1 and password2
    const payload = {
      ...data,
      password1: data.password,
      password2: data.password2 || data.password,
    };
    // delete payload.password2; // dj-rest-auth.registration expects password1 and password2

    const response = await axiosInstance.post<AuthResponse | any>(
      '/auth/registration/',
      payload
    ); // Use axiosInstance
    return response.data;
  } catch (error) {
    console.error('Registration failed:', error);
    throw error.response?.data || error;
  }
};

export const logout = async (token: string | null): Promise<void> => {
  // Token is now handled by axiosInstance interceptor, but logout endpoint is special (doesn't strictly need it from client)
  // However, dj-rest-auth logout invalidates the token on the backend.
  // The interceptor will add the token if present in localStorage.
  try {
    await axiosInstance.post('/auth/logout/', null); // Body is null, token from interceptor
    // No need to pass token explicitly if axiosInstance handles it
  } catch (error) {
    console.error('Logout failed:', error);
    // Even if backend logout fails, frontend should clear its state.
    // Optionally re-throw if you want to notify user of backend logout failure.
    // throw error.response?.data || error;
  }
};

export const getCurrentUser = async (): Promise<User> => {
  // Token removed from args, assumed by interceptor
  try {
    const response = await axiosInstance.get<User>('/auth/user/'); // Token from interceptor
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
