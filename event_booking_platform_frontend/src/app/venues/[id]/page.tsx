'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import venueService, { Venue } from '@/services/venueService';
import { useAuth } from '@/contexts/AuthContext';
import Link from 'next/link';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import AlertMessage from '@/components/common/AlertMessage';

const ROLE_VENUE_MANAGER = 'VENUE_MANAGER'; // Define role constant

const VenueDetailPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();
  const venueId = params.id as string; // In App Router, param is 'id' if folder is [id]

  const { user, isAuthenticated, hasRole, isLoading: authLoading } = useAuth();
  const [venue, setVenue] = useState<Venue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    if (venueId) {
      setLoading(true);
      venueService.getVenueById(venueId)
        .then(response => {
          setVenue(response); // Assuming getVenueById returns the venue directly
          setError(null);
        })
        .catch(err => {
          console.error(`Failed to fetch venue ${venueId}:`, err);
          setError('Failed to load venue details.');
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setError("Venue ID is missing.");
      setLoading(false);
    }
  }, [venueId]);

  const handleDeleteVenue = async () => {
    if (!venue || !user || !isAuthenticated || !hasRole(ROLE_VENUE_MANAGER) || venue.owner?.id !== user.id) {
      setError("You are not authorized to delete this venue.");
      return;
    }

    if (window.confirm(`Are you sure you want to delete venue "${venue.name}"? This action cannot be undone.`)) {
      setIsDeleting(true);
      setError(null);
      try {
        await venueService.deleteVenue(venue.id);
        alert("Venue deleted successfully."); // Replace with a more robust notification system
        router.push('/venues'); // Redirect to venues list page
      } catch (err: any) {
        console.error("Failed to delete venue:", err);
        setError(err.response?.data?.detail || "Failed to delete venue. Please try again.");
        setIsDeleting(false);
      }
    }
  };

  if (authLoading || loading) {
    return <LoadingSpinner message="Loading venue details..." />;
  }

  if (error) {
    return <AlertMessage message={error} type="error" />;
  }

  if (!venue) {
    return <AlertMessage message="Venue not found." type="info" />;
  }

  // Check if the current user is the owner for edit/delete buttons
  const isOwner = isAuthenticated && hasRole(ROLE_VENUE_MANAGER) && venue.owner?.id === user?.id;

  return (
    <div className="container mx-auto p-4 md:p-8">
      <div className="bg-white dark:bg-gray-800 shadow-xl rounded-lg overflow-hidden">
        <div className="p-6 md:p-8">
          <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">{venue.name}</h1>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-6">{venue.address}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">Details</h2>
              <p className="text-gray-700 dark:text-gray-400"><span className="font-semibold">Capacity:</span> {venue.capacity || 'N/A'}</p>
              <p className="text-gray-700 dark:text-gray-400"><span className="font-semibold">Availability:</span> {venue.is_available ? 'Available' : 'Not Available'}</p>
              {venue.contact_email && <p className="text-gray-700 dark:text-gray-400"><span className="font-semibold">Email:</span> {venue.contact_email}</p>}
              {venue.contact_phone && <p className="text-gray-700 dark:text-gray-400"><span className="font-semibold">Phone:</span> {venue.contact_phone}</p>}
              {venue.website && <p className="text-gray-700 dark:text-gray-400"><span className="font-semibold">Website:</span> <a href={venue.website} target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300">{venue.website}</a></p>}
            </div>
            {venue.amenities && (
              <div>
                <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">Amenities</h2>
                <ul className="list-disc list-inside text-gray-700 dark:text-gray-400">
                  {/* Assuming amenities is a string that needs parsing or an array */}
                  {typeof venue.amenities === 'string' ? venue.amenities.split(',').map((item, index) => <li key={index}>{item.trim()}</li>) :
                   Array.isArray(venue.amenities) ? venue.amenities.map((item, index) => <li key={index}>{item}</li>) :
                   <li>No amenities listed or format not recognized.</li>}
                </ul>
              </div>
            )}
          </div>

          {venue.description && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-2">Description</h2>
              <p className="text-gray-700 dark:text-gray-400 whitespace-pre-wrap">{venue.description}</p>
            </div>
          )}

          {venue.owner_username && (
             <p className="text-sm text-gray-500 dark:text-gray-400 mt-4">Managed by: {venue.owner_username}</p>
          )}

          {isOwner && (
            <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3">
              <Link href={`/venues/${venue.id}/edit`} legacyBehavior>
                <a className="btn btn-primary w-full sm:w-auto">Edit Venue</a>
              </Link>
              <button
                onClick={handleDeleteVenue}
                disabled={isDeleting}
                className="btn btn-danger w-full sm:w-auto"
              >
                {isDeleting ? 'Deleting...' : 'Delete Venue'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VenueDetailPage;
