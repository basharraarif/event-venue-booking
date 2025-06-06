'use client'; // This directive is necessary for using hooks like useState, useEffect

import type { Metadata } from 'next'; // Import Metadata type
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import VenueCard from '../../components/venues/VenueCard'; // Adjust path as per your structure
import { getVenues, Venue } from '../../services/venueService'; // Adjust path

// Static metadata for the venues listing page
// Note: 'use client' components cannot export 'metadata' directly.
// This metadata would typically be in a server component version of this page,
// or this page would need to be refactored if it must remain client-side for other reasons
// and metadata handled differently (e.g. via useEffect updating document.title, or a higher-level layout).
// For this subtask, we'll assume this page *could* be a server component for metadata purposes,
// or acknowledge this limitation if it must remain 'use client'.
// If this page MUST be 'use client', then this metadata object won't be used by Next.js directly.
// We'll add it as if it could be used, per subtask instructions.
// A common pattern for 'use client' pages needing dynamic titles is to update via useEffect.
// However, for static titles on client pages, often the layout's template is sufficient.

// Let's add a comment indicating how it would be done if this were a Server Component or for a future refactor.
/*
// Example of how metadata would be exported if this were a Server Component:
export const metadata: Metadata = {
  title: 'Browse Venues | Event Booking Platform',
  description: 'Find and book the perfect venue for your next event. Explore a wide range of venues available.',
  keywords: 'venues, event booking, party halls, conference centers',
};
*/

const VenuesPage = () => {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // State for filters
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [capacity, setCapacity] = useState<string>(''); // Store as string to handle empty input
  const [availability, setAvailability] = useState<string>(''); // '', 'true', 'false'
  const [minPrice, setMinPrice] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');

  const fetchVenues = async (params?: any) => {
    try {
      setLoading(true);
      const data = await getVenues(params);
      setVenues(data.results || []); // Ensure results is an array
      setError(null);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred.');
      }
      console.error(err);
      setVenues([]); // Clear venues on error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVenues(); // Initial fetch with no parameters
  }, []);

  const handleApplyFilters = () => {
    const params: any = {};
    if (searchTerm) params.search = searchTerm;
    if (capacity) params.capacity = parseInt(capacity, 10);
    if (availability) params.is_available = availability === 'true';
    if (minPrice) params.min_price_per_hour = parseFloat(minPrice);
    if (maxPrice) params.max_price_per_hour = parseFloat(maxPrice);
    fetchVenues(params);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setCapacity('');
    setAvailability('');
    setMinPrice('');
    setMaxPrice('');
    fetchVenues(); // Fetch all venues
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p className="text-xl text-gray-700">Loading venues...</p>
        {/* You could add a spinner here */}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col justify-center items-center min-h-screen text-red-600">
        <p className="text-xl">Error loading venues:</p>
        <p>{error}</p>
      </div>
    );
  }

  // No venues found message handled after filter section
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6"> {/* Reduced margin bottom for filter section */}
        <h1 className="text-4xl font-bold text-gray-800">
          Available Venues
        </h1>
        <Link href="/venues/new" className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded shadow-md transition duration-150 ease-in-out">
            Add New Venue
        </Link>
      </div>

      {/* Filters Sidebar */}
      <div className="filters-sidebar mb-6 p-4 border rounded-lg shadow">
        <h3 className="text-xl font-semibold mb-4 text-gray-700">Filter Venues</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 items-end">
          {/* Search Input */}
          <div>
            <label htmlFor="search" className="block text-sm font-medium text-gray-700">Search</label>
            <input type="text" name="search" id="search" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2" placeholder="Name, address, amenities..." />
          </div>
          {/* Availability */}
          <div>
            <label htmlFor="is_available" className="block text-sm font-medium text-gray-700">Availability</label>
            <select name="is_available" id="is_available" value={availability} onChange={e => setAvailability(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2">
              <option value="">Any</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
          {/* Capacity */}
          <div>
            <label htmlFor="capacity" className="block text-sm font-medium text-gray-700">Min. Capacity</label>
            <input type="number" name="capacity" id="capacity" value={capacity} onChange={e => setCapacity(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2" placeholder="e.g., 50" min="0" />
          </div>
          {/* Min Price Per Hour */}
          <div>
            <label htmlFor="min_price_per_hour" className="block text-sm font-medium text-gray-700">Min. Price/Hour</label>
            <input type="number" name="min_price_per_hour" id="min_price_per_hour" value={minPrice} onChange={e => setMinPrice(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2" placeholder="e.g., 20" min="0" />
          </div>
          {/* Max Price Per Hour */}
          <div>
            <label htmlFor="max_price_per_hour" className="block text-sm font-medium text-gray-700">Max. Price/Hour</label>
            <input type="number" name="max_price_per_hour" id="max_price_per_hour" value={maxPrice} onChange={e => setMaxPrice(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm p-2" placeholder="e.g., 100" min="0" />
          </div>
        </div>
        <div className="mt-6 flex flex-col sm:flex-row justify-end space-y-3 sm:space-y-0 sm:space-x-3">
          <button onClick={handleClearFilters} className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Clear Filters</button>
          <button onClick={handleApplyFilters} className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Apply Filters</button>
        </div>
      </div>

      {/* Venues List / No Venues Found Message */}
      {!loading && venues.length === 0 && (
        <div className="text-center py-10">
          <p className="text-xl text-gray-700">No venues found matching your criteria.</p>
        </div>
      )}

      <div className="flex flex-wrap justify-center gap-6"> {/* Added gap for cards */}
        {venues.map((venue) => (
          <VenueCard key={venue.id} venue={venue} />
        ))}
      </div>
    </div>
  );
};

export default VenuesPage;
