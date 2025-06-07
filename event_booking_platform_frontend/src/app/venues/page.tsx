'use client'; // Important because VenueList uses client-side hooks

import React from 'react';
import VenueList from '@/components/venues/VenueList';

// Static metadata notes:
// If this page needed to export Next.js metadata, it would typically be a Server Component.
// Since VenueList is a client component (due to hooks like useState, useEffect),
// this page also needs to be a client component.
// Static titles/descriptions are often handled in a root layout's metadata template,
// or dynamically within client components using useEffect to update document.title if needed.
// For this integration, we are focusing on rendering VenueList.

const VenuesPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-100">
      {/* A page-specific header or other layout elements could be added here if desired.
          For instance, a <header> element with a title specific to this page.
          <header className="bg-white shadow">
            <div className="container mx-auto px-4 py-6">
              <h1 className="text-3xl font-bold text-gray-800">Explore Our Venues</h1>
            </div>
          </header>
      */}
      <main className="py-8"> {/* Added some padding around the VenueList */}
        <VenueList />
      </main>
      {/* A page-specific footer could also be added here. */}
    </div>
  );
};

export default VenuesPage;
