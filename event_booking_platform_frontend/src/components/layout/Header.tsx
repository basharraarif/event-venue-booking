'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation'; // For redirecting after logout
// Define role constants - ideally import from a shared roles config file
// For now, defining here for clarity, assuming these match backend Role model 'name' field
const ROLE_ADMIN = 'ADMIN';
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_CUSTOMER = 'CUSTOMER';


const Header: React.FC = () => {
  const { isAuthenticated, user, logout, hasRole, isLoading } = useAuth();
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      // await authService.logout(); // authService in AuthContext now handles this
      logout(); // Clears local state & calls authService.logout()
      router.push('/'); // Redirect to homepage after logout
    } catch (error) {
      console.error('Logout failed:', error);
      // Handle logout error display if needed
    }
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  // Don't render header content if auth state is still loading, to prevent flash of wrong links
  // or show a minimal loading state for the header itself.
  // For now, returning null, but a skeleton header could be better.
  // if (isLoading) {
  //   return (
  //     <header className="bg-gray-800 text-white shadow-md">
  //       <div className="container mx-auto px-4 py-4 flex justify-between items-center">
  //         <Link href="/" className="text-xl font-bold">EventPlatform</Link>
  //         <div>Loading...</div>
  //       </div>
  //     </header>
  //   );
  // }


  return (
    <header className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="text-2xl font-extrabold hover:text-indigo-200 transition-colors">
              EventPilot
            </Link>
          </div>

          {/* Desktop Navigation */}
          {!isLoading && (
            <nav className="hidden md:flex space-x-4">
              <Link href="/events" className="nav-link">Events</Link>
              <Link href="/venues" className="nav-link">Venues</Link>
              {isAuthenticated && hasRole(ROLE_EVENT_ORGANIZER) && (
                <Link href="/dashboard/organizer/events/create" className="nav-link">Create Event</Link>
              )}
              {isAuthenticated && hasRole(ROLE_VENUE_MANAGER) && (
                <Link href="/dashboard/manager/venues/create" className="nav-link">Create Venue</Link>
              )}
               {isAuthenticated && hasRole(ROLE_ADMIN) && (
                <Link href="/admin/dashboard" className="nav-link">Admin Panel</Link>
              )}


              {isAuthenticated ? (
                <>
                  <Link href="/dashboard" className="nav-link">Dashboard</Link>
                  <button onClick={handleLogout} className="nav-link-button">Logout ({user?.username})</button>
                </>
              ) : (
                <>
                  <Link href="/login" className="nav-link">Login</Link>
                  <Link href="/register" className="btn btn-primary-inverted ml-2">Sign Up</Link>
                </>
              )}
            </nav>
          )}

          {/* Mobile Menu Button */}
          {!isLoading && (
            <div className="md:hidden">
              <button onClick={toggleMobileMenu} className="text-white hover:text-indigo-200 focus:outline-none">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {isMobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
                  )}
                </svg>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && !isLoading && (
        <div className="md:hidden bg-indigo-700">
          <nav className="px-2 pt-2 pb-4 space-y-1 sm:px-3">
            <Link href="/events" className="mobile-nav-link" onClick={toggleMobileMenu}>Events</Link>
            <Link href="/venues" className="mobile-nav-link" onClick={toggleMobileMenu}>Venues</Link>
            {isAuthenticated && hasRole(ROLE_EVENT_ORGANIZER) && (
              <Link href="/dashboard/organizer/events/create" className="mobile-nav-link" onClick={toggleMobileMenu}>Create Event</Link>
            )}
            {isAuthenticated && hasRole(ROLE_VENUE_MANAGER) && (
              <Link href="/dashboard/manager/venues/create" className="mobile-nav-link" onClick={toggleMobileMenu}>Create Venue</Link>
            )}
            {isAuthenticated && hasRole(ROLE_ADMIN) && (
              <Link href="/admin/dashboard" className="mobile-nav-link" onClick={toggleMobileMenu}>Admin Panel</Link>
            )}

            {isAuthenticated ? (
              <>
                <Link href="/dashboard" className="mobile-nav-link" onClick={toggleMobileMenu}>Dashboard</Link>
                <button onClick={() => { handleLogout(); toggleMobileMenu(); }} className="mobile-nav-link-button w-full text-left">Logout ({user?.username})</button>
              </>
            ) : (
              <>
                <Link href="/login" className="mobile-nav-link" onClick={toggleMobileMenu}>Login</Link>
                <Link href="/register" className="block w-full text-center px-3 py-2 rounded-md text-base font-medium btn btn-primary-inverted mt-1" onClick={toggleMobileMenu}>Sign Up</Link>
              </>
            )}
          </nav>
        </div>
      )}
      <style jsx>{`
        .nav-link {
          @apply px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-500 hover:text-white transition-colors;
        }
        .nav-link-button {
          @apply px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-500 hover:text-white transition-colors text-left;
        }
        .mobile-nav-link {
          @apply block px-3 py-2 rounded-md text-base font-medium hover:bg-indigo-500 hover:text-white transition-colors;
        }
        .mobile-nav-link-button {
           @apply block w-full px-3 py-2 rounded-md text-base font-medium hover:bg-indigo-500 hover:text-white transition-colors text-left;
        }
        .btn-primary-inverted {
            @apply bg-white text-indigo-600 px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-100 transition-colors;
        }
      `}</style>
    </header>
  );
};

export default Header;
