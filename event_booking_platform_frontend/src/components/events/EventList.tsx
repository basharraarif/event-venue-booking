'use client';

import React, { useEffect, useState, useCallback, ChangeEvent } from 'react';
import eventService, { Event, GetEventsParams, Category } from '@/services/eventService';
// import Link from 'next/link'; // Link for event details can be added later
import { debounce } from 'lodash';
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Import LoadingSpinner
import AlertMessage from '@/components/common/AlertMessage'; // Import AlertMessage

const EventList: React.FC = () => {
  const [events, setEvents] = useState<Event[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  // const [page, setPage] = useState<number>(1); // Pagination can be added later

  const initialFilterParams: GetEventsParams = {
    name: '', // nameContains
    category_name: '',
    start_time_after: '',
    start_time_before: '',
    // venueId: '', // Assuming venue is filtered by ID string. Backend uses 'venue' for venue ID.
    venue: '', // venueId for filtering
    status: '', // upcoming, ongoing, past, cancelled
  };
  const [filterParams, setFilterParams] = useState<GetEventsParams>(initialFilterParams);

  const eventStatusChoices = ['upcoming', 'ongoing', 'past', 'cancelled'];

  const fetchEventsAndCategories = useCallback(async (currentFilterParams: GetEventsParams) => {
    setLoading(true);
    setError(null);
    try {
      // Fetch categories only once or if they might change
      if (categories.length === 0) {
        const fetchedCategories = await eventService.getCategories();
        setCategories(fetchedCategories);
      }

      // Construct params, removing empty values
      const activeFilters: GetEventsParams = {};
      for (const key in currentFilterParams) {
        if (currentFilterParams[key as keyof GetEventsParams]) {
          activeFilters[key as keyof GetEventsParams] = currentFilterParams[key as keyof GetEventsParams];
        }
      }
      const data = await eventService.getEvents(activeFilters);
      setEvents(data || []);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data. Please try again later.');
      console.error("Error in EventList:", err);
    } finally {
      setLoading(false);
    }
  }, [categories.length]); // categories.length dependency to re-run if categories were just fetched.

  // Debounced function for text inputs
  const debouncedUpdateFilters = useCallback(
    debounce((newFilterKeyValue) => {
      setFilterParams(prevParams => ({ ...prevParams, ...newFilterKeyValue }));
    }, 700), // 700ms debounce
    []
  );

  const handleInputChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    // For text inputs that benefit from debounce
    if (name === "name" || name === "venue") {
         debouncedUpdateFilters({ [name]: value });
    } else {
        // Apply immediately for selects and date pickers
        setFilterParams(prevParams => ({ ...prevParams, [name]: value }));
    }
  };

  const handleApplyFilters = () => {
    // This function can be used if we have a dedicated "Apply" button.
    // For now, filters apply on change (debounced for text, immediate for select/date).
    fetchEventsAndCategories(filterParams);
  };

  const clearFilters = () => {
    setFilterParams(initialFilterParams);
    // fetchEventsAndCategories(initialFilterParams); // Re-fetch with cleared filters
  };

  useEffect(() => {
    fetchEventsAndCategories(filterParams);
  }, [filterParams, fetchEventsAndCategories]);

  // Initial loading state
  if (loading && events.length === 0) {
    return <LoadingSpinner message="Fetching events..." />;
  }

  return (
    <div>
      {/* Filter Section */}
      <div className="mb-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg shadow">
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-4">Filter Events</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 items-end">
          {/* Name Contains */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Event Name</label>
            <input
              type="text"
              name="name"
              id="name"
              value={filterParams.name}
              onChange={handleInputChange}
              placeholder="Search by name..."
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            />
          </div>
          {/* Category */}
          <div>
            <label htmlFor="category_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Category</label>
            <select
              name="category_name"
              id="category_name"
              value={filterParams.category_name}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.name}>{cat.name}</option>
              ))}
            </select>
          </div>
          {/* Status */}
          <div>
            <label htmlFor="status" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
            <select
              name="status"
              id="status"
              value={filterParams.status}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            >
              <option value="">All Statuses</option>
              {eventStatusChoices.map(choice => (
                <option key={choice} value={choice}>{choice.charAt(0).toUpperCase() + choice.slice(1)}</option>
              ))}
            </select>
          </div>
          {/* Start Time After */}
          <div>
            <label htmlFor="start_time_after" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Starts After</label>
            <input
              type="date"
              name="start_time_after"
              id="start_time_after"
              value={filterParams.start_time_after}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            />
          </div>
          {/* Start Time Before */}
          <div>
            <label htmlFor="start_time_before" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Starts Before</label>
            <input
              type="date"
              name="start_time_before"
              id="start_time_before"
              value={filterParams.start_time_before}
              onChange={handleInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            />
          </div>
           {/* Venue ID */}
           <div>
            <label htmlFor="venue" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Venue ID</label>
            <input
              type="text"
              name="venue"
              id="venue"
              value={filterParams.venue}
              onChange={handleInputChange}
              placeholder="Enter Venue ID"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition duration-150 ease-in-out"
            />
          </div>
          <div className="sm:col-span-2 md:col-span-3 lg:col-span-1 flex items-end"> {/* Adjust span for button layout */}
            <button
              onClick={clearFilters}
              className="mt-1 w-full bg-gray-300 hover:bg-gray-400 dark:bg-gray-600 dark:hover:bg-gray-500 text-gray-800 dark:text-white font-semibold py-2 px-4 rounded-md shadow-sm sm:text-sm transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-opacity-75"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Display error message if error state is set */}
      {error && (
        <div className="my-6">
          <AlertMessage message={error} type="error" />
        </div>
      )}

      {/* More nuanced loading state for when filters are applied but list isn't empty */}
      {loading && events.length > 0 && (
         <div className="text-center py-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">Applying filters...</p>
         </div>
      )}

      {!loading && events.length === 0 && !error &&(
         <div className="text-center py-10">
            <p className="text-lg text-gray-500 dark:text-gray-400">No events match your current filters. Try adjusting them or clearing filters.</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {events.map((event) => (
          <div key={event.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300 ease-in-out">
            <div className="p-6">
              <h2 className="text-2xl font-semibold mb-2 text-gray-800 dark:text-white">{event.name}</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Date: {new Date(event.start_time).toLocaleDateString()} - {new Date(event.end_time).toLocaleDateString()}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                Time: {new Date(event.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(event.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-1">
                Venue: {event.venue_name || 'To be announced'} (ID: {event.venue})
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300 mb-3">
                Price: ${parseFloat(event.ticket_price).toFixed(2)}
              </p>
              <p className="text-gray-700 dark:text-gray-300 mb-4 line-clamp-3">
                {event.description || 'No description available.'}
              </p>
              <div className="flex justify-between items-center">
                <span className={`px-3 py-1 text-xs font-semibold rounded-full ${
                  event.status === 'upcoming' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300' :
                  event.status === 'ongoing' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' :
                  event.status === 'past' ? 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300' :
                  'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300' // cancelled
                }`}>
                  {event.status.charAt(0).toUpperCase() + event.status.slice(1)}
                </span>
                <a className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50 cursor-not-allowed opacity-50"
                   aria-disabled="true"
                >
                  View Details (Soon)
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EventList;
