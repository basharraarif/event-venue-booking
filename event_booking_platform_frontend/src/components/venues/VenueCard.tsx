import React from 'react';
import Link from 'next/link'; // Import Link
import { Venue } from '../../services/venueService'; // Adjust path as necessary

interface VenueCardProps {
  venue: Venue;
}

const VenueCard: React.FC<VenueCardProps> = ({ venue }) => {
  return (
    // Removed width classes (w-full md:w-1/2 etc.) as grid handles sizing. Added dark mode classes.
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg overflow-hidden m-0 md:m-4" data-cy="venue-card">
      {/* Placeholder for image - consider aspect ratio and object-fit */}
      <div className="w-full h-48 bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
        <span className="text-gray-500 dark:text-gray-400">Venue Image (Placeholder)</span>
      </div>

      <div className="p-4 md:p-6">
        <h2 className="text-xl md:text-2xl font-bold text-gray-800 dark:text-white mb-2" data-cy="venue-name">{venue.name}</h2>
        <p className="text-gray-600 dark:text-gray-300 text-sm mb-4 h-10 overflow-hidden">{venue.address}</p> {/* Added height and overflow for consistency */}

        <div className="mb-4 flex flex-wrap gap-2">
          <span className="inline-block bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 text-xs font-semibold px-2.5 py-0.5 rounded-full" data-cy="venue-capacity">
            Capacity: {venue.capacity}
          </span>
          {venue.is_available ? (
            <span className="inline-block bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300 text-xs font-semibold px-2.5 py-0.5 rounded-full" data-cy="venue-availability-status">
              Available
            </span>
          ) : (
            <span className="inline-block bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300 text-xs font-semibold px-2.5 py-0.5 rounded-full" data-cy="venue-availability-status">
              Not Available
            </span>
          )}
        </div>

        <div className="text-gray-700 dark:text-gray-300 mb-1 text-sm">
          {venue.pricing_per_hour && (
            <p data-cy="venue-price-per-hour"><span className="font-semibold">Hourly:</span> ${parseFloat(venue.pricing_per_hour).toFixed(2)}</p>
          )}
          {venue.pricing_per_day && (
            <p><span className="font-semibold">Daily:</span> ${parseFloat(venue.pricing_per_day).toFixed(2)}</p>
          )}
          {!venue.pricing_per_hour && !venue.pricing_per_day && (
            <p className="text-gray-500 dark:text-gray-400">Pricing not specified</p>
          )}
        </div>

        {/* Amenities rendering - simplified, assuming amenities is an array of strings */}
        {Array.isArray(venue.amenities) && venue.amenities.length > 0 && (
          <div className="mt-3">
            <h4 className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Amenities:</h4>
            <div className="flex flex-wrap gap-1">
              {venue.amenities.slice(0, 3).map((amenity, index) => ( // Show first 3 amenities
                <span key={index} className="text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-0.5 rounded-full">
                  {typeof amenity === 'string' ? amenity : JSON.stringify(amenity)}
                </span>
              ))}
              {venue.amenities.length > 3 && <span className="text-xs text-gray-500 dark:text-gray-400">...</span>}
            </div>
          </div>
        )}


        {/* Action Buttons */}
        <div className="mt-4 pt-4 border-t dark:border-gray-700 flex justify-end space-x-2">
          <Link href={`/venues/${venue.id}`} className="btn btn-secondary btn-sm" legacyBehavior>
             <a className="btn btn-secondary btn-sm">Details</a>
          </Link>
          {/* Edit button might depend on user role/ownership */}
          <Link href={`/venues/${venue.id}/edit`} className="btn btn-primary btn-sm opacity-50 cursor-not-allowed" legacyBehavior>
             <a className="btn btn-primary btn-sm opacity-50 cursor-not-allowed" aria-disabled="true">Edit (Soon)</a>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default VenueCard;
