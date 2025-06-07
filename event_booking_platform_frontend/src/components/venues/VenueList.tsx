'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { getVenues, Venue } from '../../services/venueService';
import VenueCard from './VenueCard';
import Link from 'next/link';
import { debounce } from 'lodash';

const VenueList: React.FC = () => {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [hasNextPage, setHasNextPage] = useState<boolean>(false);
  const [hasPrevPage, setHasPrevPage] = useState<boolean>(false);

  // Consolidated filter state
  const [filterParams, setFilterParams] = useState({
    capacity: '', // Min capacity
    availability: '', // 'true', 'false', or ''
    minPrice: '',
    maxPrice: '',
    search: '', // New search field
  });

  const fetchVenues = useCallback(async (currentPage: number, currentFilterParams: typeof filterParams) => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { page: currentPage };
      if (currentFilterParams.search) params.search = currentFilterParams.search;
      if (currentFilterParams.capacity) params.capacity__gte = currentFilterParams.capacity;
      if (currentFilterParams.availability !== '') params.is_available = currentFilterParams.availability;
      if (currentFilterParams.minPrice) params.pricing_per_hour__gte = currentFilterParams.minPrice;
      if (currentFilterParams.maxPrice) params.pricing_per_hour__lte = currentFilterParams.maxPrice;

      const response = await getVenues(params);
      setVenues(response.results);
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
  const handleFilterChange = (newFilterKeyValue: Partial<typeof filterParams>) => {
    debouncedUpdateFiltersAndResetPage(newFilterKeyValue);
  };

  // Single useEffect for fetching data when page or filterParams change
  useEffect(() => {
    fetchVenues(page, filterParams);
  }, [page, filterParams, fetchVenues]);


  if (loading && venues.length === 0 && page === 1) {
    return (
      <div className="text-center py-10" data-cy="loading-venues-message">
        <p className="text-xl text-gray-700">Loading venues...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-10" data-cy="error-venues-message">
        <p className="text-xl text-red-600 bg-red-100 p-4 rounded-md">{error}</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-800">Venues</h1>
        <Link href="/venues/create" legacyBehavior>
          <a className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-md shadow-sm">
            Create New Venue
          </a>
        </Link>
      </div>

      {/* Filter Section */}
      <div className="mb-8 p-4 bg-gray-50 rounded-lg shadow">
        <h2 className="text-xl font-semibold text-gray-700 mb-4">Filter Venues</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700">Search</label>
            <input
              type="text"
              id="search"
              data-cy="search-input"
              value={filterParams.search}
              onChange={(e) => handleFilterChange({ search: e.target.value })}
              placeholder="Name, address..."
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="capacityMin" className="block text-sm font-medium text-gray-700">Min. Capacity</label>
            <input
              type="number"
              id="capacityMin"
              data-cy="filter-capacity-input"
              value={filterParams.capacity}
              onChange={(e) => handleFilterChange({ capacity: e.target.value })}
              placeholder="e.g., 50"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="availability" className="block text-sm font-medium text-gray-700">Availability</label>
            <select
              id="availability"
              data-cy="filter-availability-select"
              value={filterParams.availability}
              onChange={(e) => handleFilterChange({ availability: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            >
              <option value="">Any</option>
              <option value="true">Available</option>
              <option value="false">Not Available</option>
            </select>
          </div>
          <div>
            <label htmlFor="minPrice" className="block text-sm font-medium text-gray-700">Min. Price ($/hr)</label>
            <input
              type="number"
              id="minPrice"
              data-cy="filter-min-price-input"
              value={filterParams.minPrice}
              onChange={(e) => handleFilterChange({ minPrice: e.target.value })}
              placeholder="e.g., 100"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <label htmlFor="maxPrice" className="block text-sm font-medium text-gray-700">Max. Price ($/hr)</label>
            <input
              type="number"
              id="maxPrice"
              data-cy="filter-max-price-input"
              value={filterParams.maxPrice}
              onChange={(e) => handleFilterChange({ maxPrice: e.target.value })}
              placeholder="e.g., 500"
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
        </div>
      </div>

      {loading && <p className="text-center text-gray-600 py-4">Applying filters / Loading page...</p>}

      {venues.length === 0 && !loading && (
        <div className="text-center py-10" data-cy="no-venues-message">
          <p className="text-xl text-gray-700">No venues match your criteria or none available.</p>
           <Link href="/venues/create" legacyBehavior>
            <a className="mt-4 inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-md shadow-sm">
              Create New Venue
            </a>
          </Link>
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
