'use client';

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react';
// Import authService functions here when authService.ts is created
// For now, we'll define placeholder functions or skip direct calls.

interface User {
  id: string; // Changed to string if backend uses UUIDs for user ID consistently
  pk?: string; // dj-rest-auth often returns user details with 'pk' as id (can be string or number)
  username: string;
  email: string;
  roles: string[]; // Added roles
  // Add other user fields as needed
  first_name?: string;
  last_name?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  isLoading: boolean; // For initial auth check
  login: (token: string, userData: User) => void;
  logout: () => void;
  fetchAndUpdateUser: () => Promise<void>; // To refresh user data including roles
  hasRole: (roleName: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Assuming authService.getCurrentUser() exists and fetches user details including roles
import * as authService from '@/services/authService'; // Import your authService using namespace

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null); // No change here
  const [isLoading, setIsLoading] = useState(true);

  const fetchAndUpdateUser = useCallback(
    async (currentToken?: string) => {
      const effectiveToken = currentToken || token;
      if (effectiveToken) {
        try {
          // authService.getCurrentUser() should fetch from /auth/user/ and return User object including roles
          const userData = await authService.getCurrentUser(); // Assumes token is handled by axiosInstance
          if (userData) {
            // Ensure roles are always an array, even if backend might send null/undefined
            const roles =
              userData.roles?.map((r: any) =>
                typeof r === 'string' ? r : r.name
              ) || [];
            const userWithProcessedRoles = { ...userData, roles };

            setUser(userWithProcessedRoles);
            setIsAuthenticated(true);
            localStorage.setItem(
              'authUser',
              JSON.stringify(userWithProcessedRoles)
            ); // Update stored user
          } else {
            // Should not happen if getCurrentUser throws error on failure
            logoutContext(); // If no user data, treat as logout
          }
        } catch (error) {
          console.error('Failed to fetch user data with token', error);
          logoutContext(); // Clear invalid session
        }
      } else {
        // No token, ensure logged out state
        setUser(null);
        setIsAuthenticated(false);
      }
      setIsLoading(false);
    },
    [token]
  );

  useEffect(() => {
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken); // Set token for axios interceptor to pick up
      // Then fetch user data using this token
      // This replaces the simplified localStorage.getItem('authUser')
      fetchAndUpdateUser(storedToken);
    } else {
      setIsLoading(false); // No token, not loading
    }
  }, [fetchAndUpdateUser]);

  const loginContext = (newToken: string, userDataFromLogin: User) => {
    // userDataFromLogin might be basic
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
    // It's crucial that userDataFromLogin includes roles, or we fetch them immediately.
    // If /auth/login/ returns full user details including roles (from UserDetailsSerializer):
    const roles =
      userDataFromLogin.roles?.map((r: any) =>
        typeof r === 'string' ? r : r.name
      ) || [];
    const fullUser = { ...userDataFromLogin, roles };
    setUser(fullUser);
    localStorage.setItem('authUser', JSON.stringify(fullUser));
    setIsAuthenticated(true);
    // If login endpoint doesn't return roles, uncomment and use:
    // fetchAndUpdateUser(newToken);
  };

  const logoutContext = () => {
    // Call backend logout first (important for session invalidation if using session auth)
    authService
      .logout()
      .catch((err) =>
        console.error(
          'Logout API call failed but proceeding with client logout',
          err
        )
      );

    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const hasRole = (roleName: string): boolean => {
    return user?.roles?.includes(roleName) || false;
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        user,
        token,
        isLoading,
        login: loginContext,
        logout: logoutContext,
        fetchAndUpdateUser,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
