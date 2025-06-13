'use client';

import React, { useState, useEffect } from 'react';
// Define role constants - ideally import from a shared roles config file
// Ensure these match definitions used elsewhere (e.g., AuthContext, Header)
const ROLE_ADMIN = 'ADMIN';
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
// const ROLE_VENUE_MANAGER = 'VENUE_MANAGER'; // Not used in this component directly for now
// const ROLE_CUSTOMER = 'CUSTOMER'; // Not used in this component directly for now

import { useRouter } from 'next/navigation'; // Using next/navigation for App Router
import eventService, { Event } from '@/services/eventService'; // Assuming Event type is exported
import bookingService, { BookingCreatePayload, Booking } from '@/services/bookingService';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import AlertMessage from '@/components/common/AlertMessage';

interface EventDetailBookingProps {
  eventId: string;
}

const EventDetailBooking: React.FC<EventDetailBookingProps> = ({ eventId }) => {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, hasRole } = useAuth();

  const [event, setEvent] = useState<Event | null>(null);
  const [loadingEvent, setLoadingEvent] = useState(true);
  const [effectiveCapacity, setEffectiveCapacity] = useState<number | null | undefined>(undefined); // undefined: not yet calculated, null: unlimited
  const [availableTickets, setAvailableTickets] = useState<number | null>(null); // null for unlimited or if not calculated
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [isBooking, setIsBooking] = useState(false);
  const [numberOfTickets, setNumberOfTickets] = useState(1); // Default to 1 ticket

  useEffect(() => {
    if (eventId) {
      setLoadingEvent(true);
      eventService.getEventById(eventId)
        .then(response => {
          const fetchedEvent = response.data;
          setEvent(fetchedEvent);

          // Calculate effective capacity and available tickets
          let cap: number | null = null; // null means unlimited
          if (fetchedEvent.max_capacity !== null && fetchedEvent.max_capacity !== undefined) {
            cap = fetchedEvent.max_capacity;
          } else if (fetchedEvent.venue_details?.capacity !== null && fetchedEvent.venue_details?.capacity !== undefined) {
            cap = fetchedEvent.venue_details.capacity;
          }
          setEffectiveCapacity(cap);

          const activeTickets = fetchedEvent.active_tickets_count || 0;
          if (cap !== null) {
            setAvailableTickets(Math.max(0, cap - activeTickets));
          } else {
            setAvailableTickets(null); // Unlimited
          }

          setLoadingEvent(false);
        })
        .catch(err => {
          console.error("Failed to fetch event details:", err);
          setBookingError("Could not load event details.");
          setLoadingEvent(false);
        });
    }
  }, [eventId]);

  const handleBooking = async () => {
    if (!event || !isAuthenticated || !user) {
      setBookingError("Please log in to book tickets.");
      // Could also redirect to login: router.push('/login');
      return;
    }
    if (numberOfTickets <= 0) {
      setBookingError("Please select a valid number of tickets.");
      return;
    }

    setIsBooking(true);
    setBookingError(null);

    const bookingPayload: BookingCreatePayload = {
      event: event.id,
      number_of_tickets: numberOfTickets,
    };

    try {
      const newBooking: Booking = await bookingService.createBooking(bookingPayload);
      // Successfully created booking, now check payment status for redirection
      if (newBooking.payment_status === 'pending' && newBooking.id) {
        router.push(`/checkout/${newBooking.id}`);
      } else if (newBooking.payment_status === 'not_required') {
        // For free events or if payment is not needed for other reasons
        alert("Booking successful! This event requires no payment."); // Replace with a proper notification
        router.push('/dashboard/bookings'); // Or event page, or a booking confirmation page
      } else {
        // Handle other statuses or unexpected scenarios
        setBookingError("Booking created, but payment status is unclear. Please check your bookings.");
      }
    } catch (error: any) {
      console.error("Booking failed:", error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || "An unexpected error occurred while creating your booking.";
      setBookingError(errorMessage);
    } finally {
      setIsBooking(false);
    }
  };

  if (authLoading || loadingEvent) {
    return <LoadingSpinner message="Loading event details..." />;
  }

  if (!event) {
    return <AlertMessage message={bookingError || "Event not found."} type="error" />;
  }

  return (
    <div className="event-booking-section p-4 border rounded-lg shadow-md bg-white dark:bg-gray-800">
      <h2 className="text-2xl font-bold mb-2 text-gray-800 dark:text-white">{event.name}</h2>
      <p className="text-gray-700 dark:text-gray-300 mb-3">{event.description || "No description available."}</p>
      <div className="grid grid-cols-2 gap-x-4 mb-3">
        <p className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold">Price:</span> ${event.ticket_price ? parseFloat(event.ticket_price).toFixed(2) : 'Free'}
        </p>
        <p className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold">Date:</span> {new Date(event.start_time).toLocaleString()}
        </p>
        <p className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold">Max Capacity:</span> {effectiveCapacity === null ? 'Unlimited' : effectiveCapacity}
        </p>
        <p className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold">Tickets Available:</span>
          {availableTickets === null ? 'Unlimited' : (availableTickets <= 0 ? <span className="font-bold text-red-500">Sold Out</span> : availableTickets)}
        </p>
      </div>

      {bookingError && <AlertMessage message={bookingError} type="error" className="my-4" />}

      <div className="mb-4">
        <label htmlFor="numberOfTickets" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Number of Tickets:</label>
        <input
          type="number"
          id="numberOfTickets"
          name="numberOfTickets"
          value={numberOfTickets}
          onChange={(e) => {
            const newNumTickets = parseInt(e.target.value, 10);
            setNumberOfTickets(newNumTickets);
            if (newNumTickets <= 0) {
              setBookingError('Number of tickets must be greater than zero.');
            } else if (availableTickets !== null && newNumTickets > availableTickets) {
              setBookingError(`Only ${availableTickets} tickets available.`);
            } else {
              setBookingError(null); // Clear error if valid
            }
          }}
          min="1"
          max={availableTickets !== null ? Math.max(1, availableTickets) : undefined} // Ensure max is at least 1 if tickets available
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          disabled={availableTickets !== null && availableTickets <= 0} // Disable if sold out
        />
      </div>

      <button
        onClick={handleBooking}
        disabled={
          isBooking ||
          !isAuthenticated ||
          !!bookingError || // Disable if there's a ticket number error
          (availableTickets !== null && availableTickets <= 0) || // Sold out
          numberOfTickets <= 0 || // Double check, though input min="1"
          event.status === 'cancelled' ||
          new Date(event.start_time) < new Date()
        }
        className="w-full btn btn-primary disabled:opacity-50 mb-4"
      >
        {isBooking ? 'Processing...' :
         ((availableTickets !== null && availableTickets <= 0) ? 'Sold Out' :
          (event.status === 'cancelled' ? 'Event Cancelled' :
          (new Date(event.start_time) < new Date() ? 'Event Past' : 'Book Tickets')))
        }
      </button>
      {!isAuthenticated && <p className="text-sm text-red-500 mt-2">Please log in to book tickets.</p>}

      {/* Edit and Delete Buttons based on role and ownership */}
      {isAuthenticated && event && user && (
        (hasRole(ROLE_ADMIN) || (hasRole(ROLE_EVENT_ORGANIZER) && event.organizer === user.id)) && (
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-700 dark:text-white mb-3">Event Actions</h3>
            <div className="flex space-x-3">
              <Link href={`/dashboard/organizer/events/edit/${event.id}`} legacyBehavior>
                <a className="btn btn-secondary">Edit Event</a>
              </Link>
              <button
                onClick={() => { /* Implement delete logic: call service, show confirmation */ alert('Delete clicked - implement me!'); }}
                className="btn btn-danger"
              >
                Delete Event
              </button>
            </div>
          </div>
        )
      )}
    </div>
  );
};

export default EventDetailBooking;

// This component would typically be used on a dynamic event detail page, e.g.,
// `src/app/events/[eventId]/page.tsx`, where `eventId` is passed as a prop.
// Example usage in such a page:
//
// import EventDetailBooking from '@/components/events/EventDetailBooking';
//
// export default function EventDetailPage({ params }: { params: { eventId: string } }) {
//   return (
//     <div className="container mx-auto p-4">
//       {/* Other event details could be displayed here */}
//       <EventDetailBooking eventId={params.eventId} />
//     </div>
//   );
// }
//
