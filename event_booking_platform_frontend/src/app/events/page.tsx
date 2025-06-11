'use client'; // EventList will likely use client-side hooks for data fetching

import React from 'react';
import EventList from '@/components/events/EventList'; // Adjust path as needed

const EventsPage = () => {
  return (
    <div className="container mx-auto p-4">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-center text-gray-800 dark:text-white">
          Discover Events
        </h1>
        <p className="text-lg text-center text-gray-600 dark:text-gray-300 mt-2">
          Browse through our exciting list of upcoming and ongoing events.
        </p>
      </header>
      <EventList />
    </div>
  );
};

export default EventsPage;
