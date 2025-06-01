'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '../../contexts/AuthContext'; // Adjust path
import { logout as logoutUserService } from '../../services/authService'; // Adjust path

const AuthNav = () => {
  const { isAuthenticated, user, token, logout: logoutContext } = useAuth();

  const handleLogout = async () => {
    await logoutUserService(token); // Call backend logout
    logoutContext(); // Clear frontend context and local storage
    // No need to redirect here, user will see public view of pages
  };

  return (
    <div className="flex items-center space-x-3">
      {isAuthenticated ? (
        <>
          <span className="text-gray-700 text-sm hidden sm:inline">
            Hi, {user?.username || user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium"
          >
            Logout
          </button>
        </>
      ) : (
        <>
          <Link href="/login" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium">
            Login
          </Link>
          <Link href="/register" className="text-gray-700 hover:text-blue-600 px-3 py-2 text-sm font-medium bg-indigo-500 text-white rounded-md hover:bg-indigo-600">
            Register
          </Link>
        </>
      )}
    </div>
  );
};

export default AuthNav;
