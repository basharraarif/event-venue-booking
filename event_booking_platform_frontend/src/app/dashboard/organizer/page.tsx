'use client';

import React from 'react';
import RoleRequired from '@/components/auth/RoleRequired';
import Link from 'next/link';
// Define role constants - ideally import from a shared roles config file
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER'; // Matches definition in Header.tsx and backend

const OrganizerDashboardPage = () => {
  // Actual dashboard content would go here
  // For example, a list of events organized by the user, stats, etc.
  // This would involve fetching data using eventService.getMyOrganizedEvents() or similar.

  return (
    <div className="container mx-auto p-4">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Organizer Dashboard
        </h1>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Placeholder Card: Create New Event */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">
            Create New Event
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Ready to host your next big thing? Get started by creating a new
            event.
          </p>
          <Link href="/dashboard/organizer/events/create" legacyBehavior>
            <a className="btn btn-primary w-full">Create Event</a>
          </Link>
        </div>

        {/* Placeholder Card: Manage My Events */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">
            Manage My Events
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            View, edit, or update details for events you are organizing.
          </p>
          <Link href="/dashboard/organizer/my-events" legacyBehavior>
            <a className="btn btn-secondary w-full">View My Events</a>
          </Link>
        </div>

        {/* Placeholder Card: View Bookings (for events) */}
        <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg p-6 hover:shadow-xl transition-shadow">
          <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-3">
            View Bookings
          </h2>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Check booking status and attendee lists for your events.
          </p>
          <Link href="/dashboard/organizer/event-bookings" legacyBehavior>
            <a className="btn btn-secondary w-full">Event Bookings</a>
          </Link>
        </div>
      </div>

      {/* Add more organizer-specific content here */}
      {/* e.g., <MyOrganizedEventsList /> */}
    </div>
  );
};

// Wrap the page component with RoleRequired to protect it
const ProtectedOrganizerDashboardPage = () => {
  return (
    <RoleRequired requiredRoles={ROLE_EVENT_ORGANIZER} showError={true}>
      <OrganizerDashboardPage />
    </RoleRequired>
  );
};

export default ProtectedOrganizerDashboardPage;
