'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import RoleRequired from '@/components/auth/RoleRequired';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import AlertMessage from '@/components/common/AlertMessage';
import eventService, { Event } from '@/services/eventService'; // Assuming EventForm will be added later

// Define role constants
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_ADMIN = 'ADMIN';

const EditEventPageInternal: React.FC = () => {
  const router = useRouter();
  const params = useParams();
  const eventId = params.eventId as string;

  const { user, isLoading: authIsLoading, hasRole } = useAuth();
  const [event, setEvent] = useState<Event | null>(null);
  const [isLoading, setIsLoading] = useState(true); // For event data loading
  const [error, setError] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (authIsLoading) return;

    if (!user) {
      setError('Authentication required to edit events.');
      setIsLoading(false);
      return;
    }

    if (eventId && user) {
      setIsLoading(true);
      eventService
        .getEventById(eventId)
        .then((fetchedEvent) => {
          setEvent(fetchedEvent);
          // Authorization check: Admin OR (Event Organizer AND owner)
          if (
            hasRole(ROLE_ADMIN) ||
            (hasRole(ROLE_EVENT_ORGANIZER) &&
              fetchedEvent.organizer === user.id)
          ) {
            setIsAuthorized(true);
          } else {
            setError('You are not authorized to edit this event.');
            setIsAuthorized(false);
          }
        })
        .catch((err) => {
          console.error(`Failed to fetch event ${eventId}:`, err);
          setError('Failed to load event details for editing.');
          setIsAuthorized(false);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else if (!eventId) {
      setError('Event ID is missing.');
      setIsLoading(false);
    }
  }, [eventId, user, authIsLoading, hasRole]);

  if (authIsLoading || isLoading) {
    return <LoadingSpinner message="Loading event details for editing..." />;
  }

  if (error) {
    return (
      <div className="container mx-auto p-4 text-center">
        <AlertMessage message={error} type="error" />
        <button
          onClick={() => router.back()}
          className="mt-4 btn btn-secondary"
        >
          Go Back
        </button>
      </div>
    );
  }

  if (!event || !isAuthorized) {
    return (
      <div className="container mx-auto p-4 text-center">
        <AlertMessage
          message={
            !event
              ? 'Event not found.'
              : 'You are not authorized to edit this event.'
          }
          type="error"
        />
        <button
          onClick={() => router.back()}
          className="mt-4 btn btn-secondary"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <header className="mb-6">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">
          Edit Event: {event.name}
        </h1>
      </header>
      {/* Placeholder for EventForm component */}
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md">
        <p className="text-gray-700 dark:text-gray-300">
          Event editing form will be here.
        </p>
        <p className="mt-2">Event ID: {event.id}</p>
        <p className="mt-2">Current Organizer ID: {event.organizer}</p>
        {/* <EventForm eventData={event} onSubmit={handleUpdateEvent} /> */}
      </div>
    </div>
  );
};

const ProtectedEditEventPage = () => {
  return (
    // Outer protection for role, inner component handles ownership
    <RoleRequired
      requiredRoles={[ROLE_ADMIN, ROLE_EVENT_ORGANIZER]}
      showError={true}
      fallbackUrl="/dashboard"
    >
      <EditEventPageInternal />
    </RoleRequired>
  );
};

export default ProtectedEditEventPage;
