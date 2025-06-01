import React from 'react';
import Link from 'next/link'; // Import Link
import { Venue } from '../../services/venueService'; // Adjust path as necessary

interface VenueCardProps {
  venue: Venue;
}

const VenueCard: React.FC<VenueCardProps> = ({ venue }) => {
  return (
    <div className="bg-white shadow-lg rounded-lg overflow-hidden m-4 w-full md:w-1/2 lg:w-1/3 xl:w-1/4">
      {/* You can add an image here later if venues have images */}
      {/* <img className="w-full h-48 object-cover" src={venue.imageUrl || '/placeholder-image.jpg'} alt={venue.name} /> */}

      <div className="p-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2">{venue.name}</h2>
        <p className="text-gray-600 text-sm mb-4">{venue.address}</p>

        <div className="mb-4">
          <span className="inline-block bg-blue-100 text-blue-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
            Capacity: {venue.capacity}
          </span>
          {venue.is_available && (
            <span className="inline-block bg-green-100 text-green-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
              Available
            </span>
          )}
          {!venue.is_available && (
            <span className="inline-block bg-red-100 text-red-800 text-xs font-semibold mr-2 px-2.5 py-0.5 rounded">
              Not Available
            </span>
          )}
        </div>

        <div className="text-gray-700 mb-1">
          {venue.pricing_per_hour && (
            <p><strong>Price per hour:</strong> ${parseFloat(venue.pricing_per_hour).toFixed(2)}</p>
          )}
          {venue.pricing_per_day && (
            <p><strong>Price per day:</strong> ${parseFloat(venue.pricing_per_day).toFixed(2)}</p>
          )}
          {!venue.pricing_per_hour && !venue.pricing_per_day && (
            <p className="text-gray-500">Pricing not available</p>
          )}
        </div>

        {/* Example of displaying amenities if they are an array of strings */}
        {/* {Array.isArray(venue.amenities) && venue.amenities.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Amenities:</h4>
            <div className="flex flex-wrap gap-2">
              {venue.amenities.map((amenity, index) => (
                <span key={index} className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded-full">
                  {typeof amenity === 'string' ? amenity : JSON.stringify(amenity)}
                </span>
              ))}
            </div>
          </div>
        )} */}

        {/* Example for object amenities - adapt based on actual structure */}
        {typeof venue.amenities === 'object' && !Array.isArray(venue.amenities) && Object.keys(venue.amenities).length > 0 && (
           <div className="mt-4">
             <h4 className="text-sm font-semibold text-gray-700 mb-1">Amenities:</h4>
             <div className="flex flex-wrap gap-2">
               {Object.entries(venue.amenities).map(([key, value]) => (
                 <span key={key} className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded-full">
                   {key}: {String(value)}
                 </span>
               ))}
             </div>
           </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end space-x-3">
          <Link href={`/venues/${venue.id}/edit`} className="text-sm font-medium text-indigo-600 hover:text-indigo-500 px-4 py-2 rounded-md border border-indigo-600 hover:bg-indigo-50 transition-colors">
            Edit
          </Link>
          <button
            onClick={() => alert('Delete functionality not implemented yet.')} // Placeholder
            className="text-sm font-medium text-red-600 hover:text-red-500 px-4 py-2 rounded-md border border-red-600 hover:bg-red-50 transition-colors"
          >
            Delete
          </button>
        </div>

      </div>
    </div>
  );
};

export default VenueCard;
