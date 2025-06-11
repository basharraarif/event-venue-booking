'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '../../contexts/AuthContext'; // Adjust path
import { logout as logoutUserService } from '../../services/authService'; // Adjust path

const AuthNav = () => {
  const { isAuthenticated, user, token, logout: logoutContext } = useAuth();

  const handleLogout = async () => {
    if (token) { // Ensure token exists before trying to logout
      await logoutUserService(token);
    }
    logoutContext();
  };

  return (
    <div className="flex items-center space-x-2 md:space-x-3">
      {isAuthenticated ? (
        <>
          <span className="text-gray-700 dark:text-gray-300 text-sm hidden sm:inline">
            Hi, {user?.username || user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="btn btn-secondary btn-sm" // Using smaller button variant if defined, or just btn-secondary
          >
            Logout
          </button>
        </>
      ) : (
        <>
          <Link href="/login" className="link-primary px-3 py-2 text-sm font-medium">
            Login
          </Link>
          <Link href="/register" className="btn btn-primary btn-sm"> {/* Using smaller button variant */}
            Register
          </Link>
        </>
      )}
    </div>
  );
};

export default AuthNav;
