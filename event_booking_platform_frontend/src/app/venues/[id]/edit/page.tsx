'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import VenueForm, {
  VenueFormData,
} from '../../../../components/venues/VenueForm'; // Adjust path
import {
  getVenueById,
  updateVenue,
  Venue,
} from '../../../../services/venueService'; // Adjust path
// import withAuth from '../../../../components/auth/withAuth'; // Replaced with RoleRequired
import RoleRequired from '../../../../components/auth/RoleRequired'; // Import RoleRequired
import { useAuth } from '../../../../contexts/AuthContext'; // Import useAuth for ownership check
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Assuming common components
import AlertMessage from '@/components/common/AlertMessage'; // Assuming common components

const ROLE_VENUE_MANAGER = 'VENUE_MANAGER'; // Define role constant

const EditVenuePageInternal = () => {
  const router = useRouter();
  const params = useParams();
  const { user, isLoading: authIsLoading, hasRole } = useAuth(); // Get user for ownership check
  const id = params.id as string; // Type assertion, ensure 'id' is always a string

  const [venue, setVenue] = useState<Venue | null>(null);
  const [isLoading, setIsLoading] = useState(true); // For venue data loading
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isAuthorized, setIsAuthorized] = useState(false); // For ownership check

  useEffect(() => {
    if (authIsLoading) return; // Wait for auth data

    if (id && user) {
      // Ensure user is loaded before checking ownership
      const fetchVenueDetailsAndCheckOwnership = async () => {
        setIsLoading(true);
        setError(null);
        try {
          const fetchedVenue = await getVenueById(id);
          setVenue(fetchedVenue);
          // Ownership check
          if (
            fetchedVenue.owner?.id === user.id &&
            hasRole(ROLE_VENUE_MANAGER)
          ) {
            setIsAuthorized(true);
          } else {
            setError('You are not authorized to edit this venue.');
            setIsAuthorized(false);
          }
        } catch (err) {
          const errorMessage =
            err instanceof Error ? err.message : 'An unknown error occurred.';
          setError(`Failed to fetch venue details: ${errorMessage}`);
          console.error(err);
          setIsAuthorized(false);
        } finally {
          setIsLoading(false);
        }
      };
      fetchVenueDetailsAndCheckOwnership();
    } else if (!user && !authIsLoading) {
      // If user is not logged in (after auth check)
      setError('Authentication required to edit venues.');
      setIsLoading(false);
    } else if (!id) {
      setError('Venue ID is missing.');
      setIsLoading(false);
    }
  }, [id, user, authIsLoading, hasRole]);

  const handleSubmit = async (data: VenueFormData) => {
    if (!id || !isAuthorized) {
      setError('Cannot update venue. Missing ID or unauthorized.');
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
      const errorMessage =
        err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(`Failed to update venue: ${errorMessage}`);
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (authIsLoading || isLoading) {
    return <LoadingSpinner message="Loading venue details..." />;
  }

  // If there was an error during data fetching or authorization check
  if (error) {
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <AlertMessage message={error} type="error" />
        <button
          onClick={() => router.back()}
          className="mt-4 btn btn-secondary"
        >
          Go Back
        </button>
      </div>
    );
  }

  if (!venue || !isAuthorized) {
    // Fallback if not authorized and no specific error message set
    return (
      <div className="container mx-auto px-4 py-8 text-center">
        <AlertMessage
          message={
            !venue
              ? 'Venue not found.'
              : 'You are not authorized to edit this venue.'
          }
          type="error"
        />
        <button
          onClick={() => router.back()}
          className="mt-4 btn btn-secondary"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <RoleRequired requiredRoles={ROLE_VENUE_MANAGER} showError={true}>
      {' '}
      {/* Outer role check */}
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-gray-800 dark:text-white">
          Edit Venue: {venue?.name}
        </h1>

        {successMessage && (
          <AlertMessage message={successMessage} type="success" />
        )}
        {/* Display submit error if it occurs during form submission, distinct from initial load/auth error */}
        {error &&
          !isLoading && ( // Ensure this error is from submission, not initial load
            <AlertMessage message={error} type="error" />
          )}

        <VenueForm
          initialData={venue} // Pass the fetched venue data
          onSubmit={handleSubmit}
          isSubmitting={isSubmitting}
          submitButtonText="Update Venue"
        />
      </div>
    </RoleRequired>
  );
};

// const EditVenuePage = withAuth(EditVenuePageInternal); // Old HOC
export default EditVenuePageInternal; // Exporting the component directly
