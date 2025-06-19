'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation'; // For redirection
import VenueForm, { VenueFormData } from '../../../components/venues/VenueForm'; // Adjust path
import { createVenue } from '../../../services/venueService'; // Adjust path
// import withAuth from '../../../components/auth/withAuth'; // Replaced with RoleRequired
import RoleRequired from '../../../components/auth/RoleRequired'; // Import RoleRequired

const ROLE_VENUE_MANAGER = 'VENUE_MANAGER'; // Define role constant

const AddVenuePageInternal = () => {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (data: VenueFormData) => {
    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const newVenue = await createVenue(data);
      setSuccessMessage(`Venue "${newVenue.name}" created successfully!`);
      // Optionally redirect after a delay or on button click
      setTimeout(() => {
        router.push('/venues'); // Redirect to the main venues list
        // Or redirect to the new venue's detail page if you have one:
        // router.push(`/venues/${newVenue.id}`);
      }, 2000);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(`Failed to create venue: ${errorMessage}`);
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <RoleRequired requiredRoles={ROLE_VENUE_MANAGER} showError={true}>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800 dark:text-white">
          Add New Venue
        </h1>

        {error && (
          <div
            className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4"
            role="alert"
          >
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        )}

        {successMessage && (
          <div
            className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4"
            role="alert"
          >
            <strong className="font-bold">Success: </strong>
            <span className="block sm:inline">{successMessage}</span>
          </div>
        )}

        <VenueForm
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
          submitButtonText="Create Venue"
        />
      </div>
    </RoleRequired>
  );
};

// const AddVenuePage = withAuth(AddVenuePageInternal); // Old HOC
export default AddVenuePageInternal; // Exporting the component directly, RoleRequired handles auth
