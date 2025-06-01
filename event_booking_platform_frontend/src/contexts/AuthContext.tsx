'use client';

import React,  { createContext, useContext, useState, useEffect, ReactNode } from 'react';
// Import authService functions here when authService.ts is created
// For now, we'll define placeholder functions or skip direct calls.

interface User {
  id: number;
  pk?: number; // dj-rest-auth often returns user details with 'pk' as id
  username: string;
  email: string;
  // Add other user fields as needed from your backend User model
  // e.g. first_name, last_name
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  isLoading: boolean; // For initial auth check
  login: (token: string, userData: User) => void; // Simplified login for context
  logout: () => void; // Simplified logout for context
  // setUser: (user: User | null) => void; // If manual user setting is needed
  // setToken: (token: string | null) => void; // If manual token setting is needed
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true); // True initially until checked

  useEffect(() => {
    // Check for token in localStorage on initial load
    const storedToken = localStorage.getItem('authToken');
    if (storedToken) {
      setToken(storedToken);
      // Here you would typically validate the token by fetching user data
      // For now, we'll assume if a token exists, it's valid for this placeholder.
      // In a real app:
      // async function fetchUser() {
      //   try {
      //     // const userData = await authService.getCurrentUser(storedToken); // Pass token
      //     // setUser(userData);
      //     // setIsAuthenticated(true);
      //     // For placeholder:
      //     const placeholderUser = JSON.parse(localStorage.getItem('authUser') || 'null');
      //     if (placeholderUser) {
      //       setUser(placeholderUser);
      //       setIsAuthenticated(true);
      //     } else {
      //        localStorage.removeItem('authToken'); // Token without user data is invalid
      //     }
      //   } catch (error) {
      //     console.error("Failed to fetch user with stored token", error);
      //     localStorage.removeItem('authToken');
      //     localStorage.removeItem('authUser');
      //     setIsAuthenticated(false);
      //     setUser(null);
      //     setToken(null);
      //   } finally {
      //     setIsLoading(false);
      //   }
      // }
      // fetchUser();

      // Simplified for now: if token exists, try to get user from local storage
      const storedUser = localStorage.getItem('authUser');
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setIsAuthenticated(true);
        } catch (e) {
          console.error("Error parsing stored user", e);
          localStorage.removeItem('authUser');
          localStorage.removeItem('authToken'); // Clear invalid state
          setIsAuthenticated(false);
        }
      } else {
        // If only token exists but no user, it might be an old/invalid state
        // Or you'd fetch user data here. For now, clear if no user.
        localStorage.removeItem('authToken');
        setToken(null);
        setIsAuthenticated(false);
      }

    }
    setIsLoading(false); // Done checking
  }, []);

  const loginContext = (newToken: string, userData: User) => {
    localStorage.setItem('authToken', newToken);
    localStorage.setItem('authUser', JSON.stringify(userData));
    setToken(newToken);
    setUser(userData);
    setIsAuthenticated(true);
  };

  const logoutContext = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    // Here you would also call the backend logout endpoint via authService
    // e.g. authService.logout().catch(err => console.error("Logout API call failed", err));
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, token, isLoading, login: loginContext, logout: logoutContext }}>
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
