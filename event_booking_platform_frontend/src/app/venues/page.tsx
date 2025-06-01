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

  useEffect(() => {
    const fetchVenues = async () => {
      try {
        setLoading(true);
        const data = await getVenues(); // No params for now, fetches all
        setVenues(data.results); // Assuming results is the array of venues
        setError(null);
      } catch (err) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unknown error occurred.');
        }
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchVenues();
  }, []);

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

  if (venues.length === 0) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <p className="text-xl text-gray-700">No venues found.</p>
      </div>
    );
  }

// ... (other imports remain the same)

// ... (component logic remains the same up to the return statement)

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-12">
        <h1 className="text-4xl font-bold text-gray-800">
          Available Venues
        </h1>
        <Link href="/venues/new" className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded shadow-md transition duration-150 ease-in-out">
            Add New Venue
        </Link>
      </div>
      <div className="flex flex-wrap justify-center">
        {venues.map((venue) => (
          <VenueCard key={venue.id} venue={venue} />
        ))}
      </div>
    </div>
  );
};

export default VenuesPage;
