'use client';

import React from 'react';
import RoleRequired from '@/components/auth/RoleRequired';
import Link from 'next/link';

// Define role constants - ideally import from a shared roles config file
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER'; // Matches definition in Header.tsx and backend

const VenueManagerDashboardPage = () => {
  // Actual dashboard content would go here
  // e.g., list of venues managed by the user, booking reports for those venues, etc.

  return (
    <div className="container mx-auto p-4">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">Venue Manager Dashboard</h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Placeholder Card: Create New Venue */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">Create New Venue</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Add a new venue to the platform and manage its details and events.
          </p>
          <Link href="/dashboard/manager/venues/create" legacyBehavior>
            <a className="btn btn-primary w-full">Create Venue</a>
          </Link>
        </div>

        {/* Placeholder Card: Manage My Venues */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">Manage My Venues</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            View, edit, or update details for venues you own or manage.
          </p>
          <Link href="/dashboard/manager/my-venues" legacyBehavior>
            <a className="btn btn-secondary w-full">View My Venues</a>
          </Link>
        </div>

        {/* Placeholder Card: View Bookings (for events at my venues) */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">Venue Event Bookings</h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Check booking status and attendee lists for events hosted at your venues.
          </p>
          <Link href="/dashboard/manager/venue-bookings" legacyBehavior>
            <a className="btn btn-secondary w-full">Venue Bookings</a>
          </Link>
        </div>
      </div>

      {/* Add more venue manager-specific content here */}
      {/* e.g., <MyManagedVenuesList /> */}

    </div>
  );
};

// Wrap the page component with RoleRequired to protect it
const ProtectedVenueManagerDashboardPage = () => {
  return (
    <RoleRequired requiredRoles={ROLE_VENUE_MANAGER} showError={true}>
      <VenueManagerDashboardPage />
    </RoleRequired>
  );
};

export default ProtectedVenueManagerDashboardPage;
