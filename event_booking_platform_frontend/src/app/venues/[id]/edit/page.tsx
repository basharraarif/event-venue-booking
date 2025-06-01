'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import VenueForm, { VenueFormData } from '../../../../components/venues/VenueForm'; // Adjust path
import { getVenueById, updateVenue, Venue } from '../../../../services/venueService'; // Adjust path
import withAuth from '../../../../components/auth/withAuth'; // Import HOC

const EditVenuePageInternal = () => { // Renamed original component
  const router = useRouter();
  const params = useParams();
  const id = params.id as string; // Type assertion, ensure 'id' is always a string

  const [venue, setVenue] = useState<Venue | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      const fetchVenueDetails = async () => {
        setIsLoading(true);
        setError(null);
        try {
          const data = await getVenueById(id);
          setVenue(data);
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
          setError(`Failed to fetch venue details: ${errorMessage}`);
          console.error(err);
        } finally {
          setIsLoading(false);
        }
      };
      fetchVenueDetails();
    }
  }, [id]);

  const handleSubmit = async (data: VenueFormData) => {
    if (!id) {
      setError("Venue ID is missing. Cannot update.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const updatedVenue = await updateVenue(id, data);
      setSuccessMessage(`Venue "${updatedVenue.name}" updated successfully!`);
      // Optionally redirect
      setTimeout(() => {
        router.push('/venues'); // Or to the venue detail page: /venues/${id}
      }, 2000);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(`Failed to update venue: ${errorMessage}`);
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="flex justify-center items-center min-h-screen"><p>Loading venue details...</p></div>;
  }

  if (error && !venue) { // Show critical error if venue couldn't be loaded
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <h1 className="text-3xl font-bold text-red-600 mb-4">Error</h1>
        <p className="text-red-500">{error}</p>
        <button onClick={() => router.back()} className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600">
          Go Back
        </button>
      </div>
    );
  }

  if (!venue) { // Should ideally be covered by isLoading or error state
    return <div className="flex justify-center items-center min-h-screen"><p>Venue not found.</p></div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-center mb-8 text-gray-800">Edit Venue: {venue?.name}</h1>

      {error && ( // For non-critical errors during submit
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded relative mb-4" role="alert">
          <strong className="font-bold">Success: </strong>
          <span className="block sm:inline">{successMessage}</span>
        </div>
      )}

      <VenueForm
        initialData={venue} // Pass the fetched venue data
        onSubmit={handleSubmit}
        isSubmitting={isSubmitting}
        submitButtonText="Update Venue"
      />
    </div>
  );
};

// export default EditVenuePage; // Original export

const EditVenuePage = withAuth(EditVenuePageInternal); // Wrap component with HOC
export default EditVenuePage;
