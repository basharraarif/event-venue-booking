'use client';

import React from 'react';
import RoleRequired from '@/components/auth/RoleRequired';
import EventForm from '@/components/events/EventForm'; // Assuming a reusable EventForm component exists

// Define role constants
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_ADMIN = 'ADMIN';

const CreateEventPage = () => {
  return (
    <div className="container mx-auto p-4">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Create New Event
        </h1>
      </header>

      {/*
        The EventForm component would handle the actual form fields for creating an event.
        It would use eventService.createEvent() on submission.
        For this task, we are focusing on role protection.
      */}
      <EventForm />
    </div>
  );
};

const ProtectedCreateEventPage = () => {
  return (
    <RoleRequired
      requiredRoles={[ROLE_ADMIN, ROLE_EVENT_ORGANIZER]}
      showError={true}
      fallbackUrl="/dashboard"
    >
      <CreateEventPage />
    </RoleRequired>
  );
};

export default ProtectedCreateEventPage;

// Placeholder for EventForm component if it doesn't exist:
// Create a file like src/components/events/EventForm.tsx
//
// import React from 'react';
// const EventForm = () => (
//   <form className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
//     <div className="mb-4">
//       <label htmlFor="eventName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Event Name</label>
//       <input type="text" name="eventName" id="eventName" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm dark:bg-gray-700 dark:border-gray-600" />
//     </div>
//     {/* Add more fields: description, venue select, categories, start/end times, ticket price, etc. */}
//     <button type="submit" className="btn btn-primary">Submit Event</button>
//   </form>
// );
// export default EventForm;
//
// This placeholder EventForm is extremely basic. A real form would use react-hook-form or similar,
// fetch venues and categories for selection, handle date/time inputs, and call eventService.createEvent.
