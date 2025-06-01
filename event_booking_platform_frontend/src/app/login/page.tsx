'use client';

import React, { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../contexts/AuthContext'; // Adjust path
import { login as loginUser, LoginCredentials, getCurrentUser } from '../../services/authService'; // Adjust path

const LoginPage = () => {
  const router = useRouter();
  const { login: loginContext } = useAuth(); // login from AuthContext
  const [credentials, setCredentials] = useState<LoginCredentials>({ email: '', password: '' });
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCredentials({ ...credentials, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    if (!credentials.email || !credentials.password) {
        setError("Email and password are required.");
        setIsLoading(false);
        return;
    }

    // Determine if login is via username or email
    // For this example, we'll use 'email' as the primary field for login
    // but dj-rest-auth can be configured for 'username' or 'email' as login field
    const loginPayload: LoginCredentials = {
        email: credentials.email, // Assuming login with email
        // username: credentials.username, // If using username
        password: credentials.password,
    };


    try {
      const authResponse = await loginUser(loginPayload); // Call from authService
      if (authResponse.key) {
        // Fetch full user details if not returned by login, or to ensure data is fresh
        const userDetails = await getCurrentUser(authResponse.key);
        loginContext(authResponse.key, userDetails); // Update AuthContext
        router.push('/venues'); // Redirect to a protected or dashboard page
      } else {
        setError('Login failed: No token received.');
      }
    } catch (err: any) {
      console.error(err);
      let errorMessage = 'Login failed. Please check your credentials.';
      if (err && err.non_field_errors) {
        errorMessage = err.non_field_errors.join(' ');
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err.detail) {
        errorMessage = err.detail;
      }
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 px-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-white shadow-lg rounded-lg">
        <h2 className="text-3xl font-bold text-center text-gray-800">Login</h2>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              Email or Username
            </label>
            <input
              type="text" // Changed to text to allow username or email
              name="email" // Keep as email, or use a generic 'loginField'
              id="email"
              value={credentials.email}
              onChange={handleChange}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="your@email.com or username"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              type="password"
              name="password"
              id="password"
              value={credentials.password || ''}
              onChange={handleChange}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
            >
              {isLoading ? 'Logging in...' : 'Login'}
            </button>
          </div>
        </form>
        <p className="text-sm text-center text-gray-600">
          Don&apos;t have an account?{' '}
          <a href="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
            Register here
          </a>
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
