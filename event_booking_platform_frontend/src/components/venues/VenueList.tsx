'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { getVenues, Venue } from '../../services/venueService'; // Assuming Venue type is exported
import VenueCard from './VenueCard';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext'; // Import useAuth
import { debounce } from 'lodash';
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Import LoadingSpinner
import AlertMessage from '@/components/common/AlertMessage'; // Import AlertMessage

// Define role constants, ideally from a shared file
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';

const VenueList: React.FC = () => {
  const { isAuthenticated, hasRole } = useAuth(); // Get auth context
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [hasNextPage, setHasNextPage] = useState<boolean>(false);
  const [hasPrevPage, setHasPrevPage] = useState<boolean>(false);

  // Consolidated filter state
  const initialFilterParams = {
    capacity: '', // Min capacity
    availability: '', // 'true', 'false', or ''
    minPricePerHour: '',
    maxPricePerHour: '',
    minPricePerDay: '', // New
    maxPricePerDay: '', // New
    search: '', // Generic search for name, address etc.
    // addressContains: '', // Specific address search - can be part of general 'search' or separate
  };
  const [filterParams, setFilterParams] = useState(initialFilterParams);

  const fetchVenues = useCallback(async (currentPage: number, currentFilterParams: typeof initialFilterParams) => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { page: currentPage };
      if (currentFilterParams.search) params.search = currentFilterParams.search;
      // if (currentFilterParams.addressContains) params.address__icontains = currentFilterParams.addressContains; // Example for specific field
      if (currentFilterParams.capacity) params.capacity__gte = currentFilterParams.capacity;
      if (currentFilterParams.availability !== '') params.is_available = currentFilterParams.availability;
      if (currentFilterParams.minPricePerHour) params.pricing_per_hour__gte = currentFilterParams.minPricePerHour;
      if (currentFilterParams.maxPricePerHour) params.pricing_per_hour__lte = currentFilterParams.maxPricePerHour;
      if (currentFilterParams.minPricePerDay) params.pricing_per_day__gte = currentFilterParams.minPricePerDay;
      if (currentFilterParams.maxPricePerDay) params.pricing_per_day__lte = currentFilterParams.maxPricePerDay;

      const response = await getVenues(params); // Ensure getVenues can handle these params
      setVenues(response.results || []); // Handle case where results might be undefined
      setHasNextPage(response.next !== null);
      setHasPrevPage(response.previous !== null);
    } catch (err) {
      setError('Failed to fetch venues. Please try again later.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []); // Empty dependency array: fetchVenues itself doesn't depend on component state/props directly

  // Debounced function to update filterParams and reset page
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const debouncedUpdateFiltersAndResetPage = useCallback(
    debounce((newFilterKeyValue) => {
      setFilterParams(prevParams => ({ ...prevParams, ...newFilterKeyValue }));
      setPage(1); // Reset page to 1 when filters change
    }, 500), // 500ms debounce time
    [] // No dependencies for the debounce wrapper itself
  );

  // Handler for input changes
  const handleFilterChange = (newFilterKeyValue: Partial<typeof initialFilterParams>) => {
    debouncedUpdateFiltersAndResetPage(newFilterKeyValue);
  };

  const clearFilters = () => {
    setFilterParams(initialFilterParams);
    setPage(1); // Reset to page 1
    // fetchVenues(1, initialFilterParams); // Optionally re-fetch immediately or let useEffect handle it
  };

  // Single useEffect for fetching data when page or filterParams change
  useEffect(() => {
    fetchVenues(page, filterParams);
  }, [page, filterParams, fetchVenues]);

  // Initial loading state for the very first load or when filters result in no items yet
  if (loading && venues.length === 0 && page === 1) {
    return <LoadingSpinner message="Fetching venues..." />;
  }

  // Subsequent loading (e.g., pagination, or applying filters when some venues are already shown)
  // This can be a more subtle indicator, or handled by disabling inputs/buttons.
  // For now, the main spinner above covers initial load, and buttons have disabled states.

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-4">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">Venues</h1>
        {isAuthenticated && hasRole(ROLE_VENUE_MANAGER) && (
          <Link href="/venues/create" legacyBehavior>
            <a className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50">
              Create New Venue
            </a>
          </Link>
        )}
      </div>

      {/* Filter Section */}
      <div className="mb-8 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg shadow">
        <h2 className="text-xl font-semibold text-gray-700 dark:text-gray-200 mb-4">Filter Venues</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 items-end">
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Search</label>
            <input
              type="text"
              id="search"
              name="search" // Ensure name attribute for handleFilterChange
              data-cy="search-input"
              value={filterParams.search}
              onChange={(e) => handleFilterChange({ search: e.target.value })}
              placeholder="Name, address..."
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="capacityMin" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Min. Capacity</label>
            <input
              type="number"
              id="capacityMin"
              name="capacity" // Ensure name attribute
              data-cy="filter-capacity-input"
              value={filterParams.capacity}
              onChange={(e) => handleFilterChange({ capacity: e.target.value })}
              placeholder="e.g., 50"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="availability" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Availability</label>
            <select
              id="availability"
              name="availability" // Ensure name attribute
              data-cy="filter-availability-select"
              value={filterParams.availability}
              onChange={(e) => handleFilterChange({ availability: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="">Any</option>
              <option value="true">Available</option>
              <option value="false">Not Available</option>
            </select>
          </div>
          <div>
            <label htmlFor="minPricePerHour" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Min. Price ($/hr)</label>
            <input
              type="number"
              id="minPricePerHour"
              name="minPricePerHour" // Ensure name attribute
              data-cy="filter-min-price-per-hour-input"
              value={filterParams.minPricePerHour}
              onChange={(e) => handleFilterChange({ minPricePerHour: e.target.value })}
              placeholder="e.g., 100"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="maxPricePerHour" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max. Price ($/hr)</label>
            <input
              type="number"
              id="maxPricePerHour"
              name="maxPricePerHour" // Ensure name attribute
              data-cy="filter-max-price-per-hour-input"
              value={filterParams.maxPricePerHour}
              onChange={(e) => handleFilterChange({ maxPricePerHour: e.target.value })}
              placeholder="e.g., 500"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          {/* New Price Per Day Filters */}
          <div>
            <label htmlFor="minPricePerDay" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Min. Price ($/day)</label>
            <input
              type="number"
              id="minPricePerDay"
              name="minPricePerDay" // Ensure name attribute
              data-cy="filter-min-price-per-day-input"
              value={filterParams.minPricePerDay}
              onChange={(e) => handleFilterChange({ minPricePerDay: e.target.value })}
              placeholder="e.g., 500"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="maxPricePerDay" className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max. Price ($/day)</label>
            <input
              type="number"
              id="maxPricePerDay"
              name="maxPricePerDay" // Ensure name attribute
              data-cy="filter-max-price-per-day-input"
              value={filterParams.maxPricePerDay}
              onChange={(e) => handleFilterChange({ maxPricePerDay: e.target.value })}
              placeholder="e.g., 2000"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div className="sm:col-span-2 md:col-span-3 lg:col-span-1 flex items-end"> {/* Adjust span for button layout */}
            <button
              onClick={clearFilters}
              data-cy="clear-filters-button"
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
      {loading && venues.length > 0 && (
         <div className="text-center py-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">Applying filters...</p>
         </div>
      )}

      {venues.length === 0 && !loading && !error && (
        <div className="text-center py-10" data-cy="no-venues-message">
          <p className="text-xl text-gray-700 dark:text-gray-300">No venues match your criteria or none available.</p>
            {isAuthenticated && hasRole(ROLE_VENUE_MANAGER) && (
              <Link href="/venues/create" legacyBehavior>
                <a className="mt-4 inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-md shadow-sm transition duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-opacity-50">
                  Create New Venue
                </a>
              </Link>
            )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8" data-cy="venue-list-container">
        {venues.map((venue) => (
          <VenueCard key={venue.id} venue={venue} />
        ))}
      </div>

      {venues.length > 0 && !loading && (
        <div className="mt-12 flex justify-center items-center space-x-4">
          <button
            data-cy="pagination-prev-button"
            onClick={() => setPage(page - 1)}
            disabled={!hasPrevPage || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-sm text-gray-700" data-cy="pagination-page-display">Page {page}</span>
          <button
            data-cy="pagination-next-button"
            onClick={() => setPage(page + 1)}
            disabled={!hasNextPage || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};

export default VenueList;
