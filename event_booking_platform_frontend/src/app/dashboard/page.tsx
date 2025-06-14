'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext'; // Assuming this path is correct
import Link from 'next/link';

// Import services
import bookingService, { Booking } from '@/services/bookingService';
import eventService, { Event } from '@/services/eventService';
import venueService, { Venue } from '@/services/venueService';
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Import common components
import AlertMessage from '@/components/common/AlertMessage';   // Import common components

const DashboardPage = () => {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();

  const [myBookings, setMyBookings] = useState<Booking[]>([]);
  const [loadingBookings, setLoadingBookings] = useState(true);
  const [errorBookings, setErrorBookings] = useState<string | null>(null);

  const [myEvents, setMyEvents] = useState<Event[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [errorEvents, setErrorEvents] = useState<string | null>(null);

  const [myVenues, setMyVenues] = useState<Venue[]>([]);
  const [loadingVenues, setLoadingVenues] = useState(true);
  const [errorVenues, setErrorVenues] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated && user && user.id) { // Ensure user.id is available
      // Fetch My Bookings
      setLoadingBookings(true);
      bookingService.getMyBookings() // Assumes backend filters by authenticated user via token
        .then(data => setMyBookings(data))
        .catch(err => {
            console.error("Error fetching bookings:", err);
            setErrorBookings('Failed to load your bookings. Please try refreshing.');
        })
        .finally(() => setLoadingBookings(false));

      // Fetch My Events if user is an organizer
      if (user.roles && user.roles.includes('organizer')) {
        setLoadingEvents(true);
        eventService.getEvents({ organizer: user.id })
          .then(data => setMyEvents(data))
          .catch(err => {
            console.error("Error fetching events:", err);
            setErrorEvents('Failed to load your events. Please try refreshing.');
          })
          .finally(() => setLoadingEvents(false));
      } else {
        setLoadingEvents(false);
      }

      // Fetch My Venues if user is a venue_manager
      if (user.roles && user.roles.includes('venue_manager')) {
        setLoadingVenues(true);
        venueService.getVenues({ owner: user.id })
          .then(data => setMyVenues(data.results || [])) // Ensure results is an array
          .catch(err => {
            console.error("Error fetching venues:", err);
            setErrorVenues('Failed to load your venues. Please try refreshing.');
          })
          .finally(() => setLoadingVenues(false));
      } else {
        setLoadingVenues(false);
      }
    } else if (!authLoading && !isAuthenticated) {
      setLoadingBookings(false);
      setLoadingEvents(false);
      setLoadingVenues(false);
    }
  }, [user, isAuthenticated, authLoading]);

  if (authLoading) {
    return <LoadingSpinner message="Loading user information..." />;
  }

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto p-4 text-center">
        <AlertMessage message="Please log in to view your dashboard." type="info" />
        <Link href="/login" legacyBehavior>
          <a className="btn btn-primary mt-4">Login</a>
        </Link>
      </div>
    );
  }

  if (!user) { // Should be caught by !isAuthenticated if authLoading is false
    return (
        <div className="container mx-auto p-4 text-center">
            <AlertMessage message="Could not load user data. Please try logging in again." type="error" />
            <Link href="/login" legacyBehavior>
                <a className="btn btn-primary mt-4">Login</a>
            </Link>
        </div>
    );
  }

  return (
    <div className="container mx-auto p-4 md:p-6 lg:p-8">
      <header className="mb-10 text-center md:text-left">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-800 dark:text-white">Your Dashboard</h1>
        <p className="text-md md:text-lg text-gray-600 dark:text-gray-400">Welcome back, {user.username || user.email}!</p>
      </header>

      {/* My Bookings Section */}
      <section className="mb-12 p-4 md:p-6 bg-white dark:bg-gray-800 shadow-lg rounded-lg">
        <h2 className="text-xl md:text-2xl font-semibold text-gray-700 dark:text-white mb-6">My Bookings</h2>
        {loadingBookings && <LoadingSpinner message="Loading your bookings..." />}
        {errorBookings && <AlertMessage message={errorBookings} type="error" />}
        {!loadingBookings && !errorBookings && myBookings.length === 0 && (
          <p className="text-gray-500 dark:text-gray-400">You have no bookings yet. Why not <Link href="/events" className="link-primary">find an event</Link>?</p>
        )}
        {!loadingBookings && !errorBookings && myBookings.length > 0 && (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Event</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Date</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Tickets</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Status</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Total</th>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {myBookings.map(booking => (
                  <tr key={booking.id}>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">{booking.event_details?.name || 'N/A'}</td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">
                      {booking.event_details?.start_time ? new Date(booking.event_details.start_time).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">{booking.number_of_tickets}</td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        booking.status === 'confirmed' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                        booking.status === 'pending' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' :
                                                        'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' // cancelled
                      }`}>
                        {booking.status}
                      </span>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${booking.total_price}</td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm font-medium">
                      {booking.status === 'pending' && booking.id && (
                        <Link href={`/checkout/${booking.id}`} className="link-primary">
                          Pay Now
                        </Link>
                      )}
                       {/* Add other actions like 'View Details' if applicable */}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* My Events Section (for Organizers) */}
      {user.roles && user.roles.includes('organizer') && (
        <section className="mb-12 p-4 md:p-6 bg-white dark:bg-gray-800 shadow-lg rounded-lg">
          <h2 className="text-xl md:text-2xl font-semibold text-gray-700 dark:text-white mb-6">My Events (Organized by Me)</h2>
          {loadingEvents && <LoadingSpinner message="Loading your events..." />}
          {errorEvents && <AlertMessage message={errorEvents} type="error" />}
          {!loadingEvents && !errorEvents && myEvents.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400">You have not organized any events yet.
              {/* <Link href="/events/create" className="link-primary">Create one now!</Link> */}
            </p>
          )}
          {!loadingEvents && !errorEvents && myEvents.length > 0 && (
            <ul className="space-y-3">
              {myEvents.map(event => (
                <li key={event.id} className="p-3 border dark:border-gray-700 rounded-md flex justify-between items-center">
                  <div>
                    <h3 className="text-md font-medium text-indigo-600 dark:text-indigo-400">{event.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-300">Date: {new Date(event.start_time).toLocaleDateString()} | Status: {event.status}</p>
                  </div>
                  <button className="btn btn-secondary btn-sm opacity-50 cursor-not-allowed" disabled>Edit (Soon)</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {/* My Venues Section (for Venue Managers) */}
      {user.roles && user.roles.includes('venue_manager') && (
        <section className="p-4 md:p-6 bg-white dark:bg-gray-800 shadow-lg rounded-lg">
          <h2 className="text-xl md:text-2xl font-semibold text-gray-700 dark:text-white mb-6">My Venues (Managed by Me)</h2>
          {loadingVenues && <LoadingSpinner message="Loading your venues..." />}
          {errorVenues && <AlertMessage message={errorVenues} type="error" />}
          {!loadingVenues && !errorVenues && myVenues.length === 0 && (
            <p className="text-gray-500 dark:text-gray-400">You are not managing any venues yet.
              <Link href="/venues/create" className="link-primary">Add a venue!</Link>
            </p>
          )}
          {!loadingVenues && !errorVenues && myVenues.length > 0 && (
            <ul className="space-y-3">
              {myVenues.map(venue => (
                <li key={venue.id} className="p-3 border dark:border-gray-700 rounded-md flex justify-between items-center">
                  <div>
                    <h3 className="text-md font-medium text-indigo-600 dark:text-indigo-400">{venue.name}</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-300">Capacity: {venue.capacity}</p>
                  </div>
                  <button className="btn btn-secondary btn-sm opacity-50 cursor-not-allowed" disabled>Edit (Soon)</button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
};

export default DashboardPage;
