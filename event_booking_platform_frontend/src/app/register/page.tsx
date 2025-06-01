'use client';

import React, { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
// Assuming useAuth might be used later for auto-login or fetching user details post-registration
// import { useAuth } from '../../contexts/AuthContext';
import { register as registerUser, RegistrationData } from '../../services/authService'; // Adjust path

const RegisterPage = () => {
  const router = useRouter();
  // const { login: loginContext } = useAuth(); // If auto-login after registration
  const [formData, setFormData] = useState<RegistrationData>({
    username: '',
    email: '',
    password: '',
    password2: '',
  });
  const [error, setError] = useState<Record<string, string[] | string> | string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    if (formData.password !== formData.password2) {
      setError({ password2: ["Passwords do not match."] });
      setIsLoading(false);
      return;
    }
    if (!formData.email || !formData.username || !formData.password) {
        setError("Username, email, and password are required.");
        setIsLoading(false);
        return;
    }

    try {
      // The registerUser service function will map 'password' to 'password1'
      await registerUser(formData);
      setSuccessMessage('Registration successful! Please login.');
      setTimeout(() => {
        router.push('/login');
      }, 2000);
      // If backend auto-logs in and returns token/user:
      // const authResponse = await registerUser(formData);
      // if (authResponse.key && authResponse.user) {
      //   const userDetails = await getCurrentUser(authResponse.key); // Or use authResponse.user
      //   loginContext(authResponse.key, userDetails);
      //   router.push('/venues');
      // } else { ... }
    } catch (err: any) {
      console.error(err);
      if (typeof err === 'object' && err !== null) {
        setError(err); // Expecting error object like { username: ["error msg"], email: ["error msg"] }
      } else {
        setError('Registration failed. An unknown error occurred.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to display errors
  const displayErrors = (field: keyof RegistrationData) => {
    if (typeof error === 'object' && error !== null && error[field]) {
      const fieldErrors = error[field];
      return Array.isArray(fieldErrors) ? fieldErrors.join(' ') : String(fieldErrors);
    }
    return null;
  };


  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 px-4">
      <div className="w-full max-w-md p-8 space-y-6 bg-white shadow-lg rounded-lg">
        <h2 className="text-3xl font-bold text-center text-gray-800">Register</h2>

        {typeof error === 'string' && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <span className="block sm:inline">{error}</span>
          </div>
        )}
        {successMessage && (
             <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4" role="alert">
                <span className="block sm:inline">{successMessage}</span>
            </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700">Username</label>
            <input type="text" name="username" id="username" value={formData.username} onChange={handleChange} required
                   className={`mt-1 block w-full px-3 py-2 border ${displayErrors('username') ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`} />
            {displayErrors('username') && <p className="mt-1 text-xs text-red-500">{displayErrors('username')}</p>}
          </div>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">Email</label>
            <input type="email" name="email" id="email" value={formData.email} onChange={handleChange} required
                   className={`mt-1 block w-full px-3 py-2 border ${displayErrors('email') ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`} />
            {displayErrors('email') && <p className="mt-1 text-xs text-red-500">{displayErrors('email')}</p>}
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">Password</label>
            <input type="password" name="password" id="password" value={formData.password} onChange={handleChange} required
                   className={`mt-1 block w-full px-3 py-2 border ${displayErrors('password') ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`} />
            {displayErrors('password') && <p className="mt-1 text-xs text-red-500">{displayErrors('password')}</p>}
          </div>
          <div>
            <label htmlFor="password2" className="block text-sm font-medium text-gray-700">Confirm Password</label>
            <input type="password" name="password2" id="password2" value={formData.password2} onChange={handleChange} required
                   className={`mt-1 block w-full px-3 py-2 border ${displayErrors('password2') ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`} />
            {displayErrors('password2') && <p className="mt-1 text-xs text-red-500">{displayErrors('password2')}</p>}
          </div>
          <div>
            <button type="submit" disabled={isLoading}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400">
              {isLoading ? 'Registering...' : 'Register'}
            </button>
          </div>
        </form>
        <p className="text-sm text-center text-gray-600">
          Already have an account?{' '}
          <a href="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
            Login here
          </a>
        </p>
      </div>
    </div>
  );
};

export default RegisterPage;
