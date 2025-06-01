'use client';

import React, { useState, useEffect, FormEvent } from 'react';
import { Venue } from '../../services/venueService'; // Adjust path as necessary

// Data structure for form submission (excluding id, created_at, updated_at)
export type VenueFormData = Omit<Venue, 'id' | 'created_at' | 'updated_at'>;

interface VenueFormProps {
  initialData?: Partial<Venue>; // For pre-filling in edit mode
  onSubmit: (data: VenueFormData) => void;
  isSubmitting?: boolean;
  submitButtonText?: string;
}

const VenueForm: React.FC<VenueFormProps> = ({
  initialData,
  onSubmit,
  isSubmitting = false,
  submitButtonText = 'Submit Venue',
}) => {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [capacity, setCapacity] = useState<number | ''>('');
  const [amenities, setAmenities] = useState(''); // Comma-separated string for simplicity
  const [pricingPerHour, setPricingPerHour] = useState<string | ''>('');
  const [pricingPerDay, setPricingPerDay] = useState<string | ''>('');
  const [isAvailable, setIsAvailable] = useState(true);
  const [errors, setErrors] = useState<Partial<Record<keyof VenueFormData, string>>>({});

  useEffect(() => {
    if (initialData) {
      setName(initialData.name || '');
      setAddress(initialData.address || '');
      setCapacity(initialData.capacity || '');

      // Handle amenities: if it's an array or object, convert to string for the form
      if (Array.isArray(initialData.amenities)) {
        setAmenities(initialData.amenities.join(', '));
      } else if (typeof initialData.amenities === 'object' && initialData.amenities !== null) {
        setAmenities(Object.keys(initialData.amenities).join(', ')); // Or JSON.stringify
      } else {
        setAmenities('');
      }

      setPricingPerHour(initialData.pricing_per_hour || '');
      setPricingPerDay(initialData.pricing_per_day || '');
      setIsAvailable(initialData.is_available === undefined ? true : initialData.is_available);
    }
  }, [initialData]);

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof VenueFormData, string>> = {};
    if (!name.trim()) newErrors.name = 'Name is required.';
    if (!address.trim()) newErrors.address = 'Address is required.';
    if (capacity === '' || Number(capacity) <= 0) newErrors.capacity = 'Capacity must be a positive number.';
    // Add more validation as needed (e.g., for pricing formats)
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!validate()) return;

    // Prepare amenities: convert comma-separated string to array/object or leave as string
    // depending on what your backend expects for the JSONField.
    // For this example, let's assume the backend can handle a list of strings if JSONField is used.
    const amenitiesData = amenities.split(',').map(s => s.trim()).filter(s => s);

    onSubmit({
      name,
      address,
      capacity: Number(capacity),
      amenities: amenitiesData, // Or parse as JSON object if backend expects that
      pricing_per_hour: pricingPerHour || null,
      pricing_per_day: pricingPerDay || null,
      is_available: isAvailable,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 p-4 md:p-8 bg-white shadow-lg rounded-lg max-w-2xl mx-auto">
      <div>
        <label htmlFor="name" className="block text-sm font-medium text-gray-700">Name <span className="text-red-500">*</span></label>
        <input
          type="text"
          id="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`mt-1 block w-full px-3 py-2 border ${errors.name ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
        />
        {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name}</p>}
      </div>

      <div>
        <label htmlFor="address" className="block text-sm font-medium text-gray-700">Address <span className="text-red-500">*</span></label>
        <textarea
          id="address"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          rows={3}
          className={`mt-1 block w-full px-3 py-2 border ${errors.address ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
        />
        {errors.address && <p className="mt-1 text-xs text-red-500">{errors.address}</p>}
      </div>

      <div>
        <label htmlFor="capacity" className="block text-sm font-medium text-gray-700">Capacity <span className="text-red-500">*</span></label>
        <input
          type="number"
          id="capacity"
          value={capacity}
          onChange={(e) => setCapacity(e.target.value === '' ? '' : Number(e.target.value))}
          className={`mt-1 block w-full px-3 py-2 border ${errors.capacity ? 'border-red-500' : 'border-gray-300'} rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm`}
        />
        {errors.capacity && <p className="mt-1 text-xs text-red-500">{errors.capacity}</p>}
      </div>

      <div>
        <label htmlFor="amenities" className="block text-sm font-medium text-gray-700">Amenities (comma-separated)</label>
        <input
          type="text"
          id="amenities"
          value={amenities}
          onChange={(e) => setAmenities(e.target.value)}
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          placeholder="e.g., Wi-Fi, Parking, Projector"
        />
        <p className="mt-1 text-xs text-gray-500">Backend expects a list of strings or a JSON object for amenities.</p>
      </div>

      <div>
        <label htmlFor="pricingPerHour" className="block text-sm font-medium text-gray-700">Price per Hour ($)</label>
        <input
          type="number"
          id="pricingPerHour"
          value={pricingPerHour}
          onChange={(e) => setPricingPerHour(e.target.value)}
          step="0.01"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div>
        <label htmlFor="pricingPerDay" className="block text-sm font-medium text-gray-700">Price per Day ($)</label>
        <input
          type="number"
          id="pricingPerDay"
          value={pricingPerDay}
          onChange={(e) => setPricingPerDay(e.target.value)}
          step="0.01"
          className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
      </div>

      <div className="flex items-center">
        <input
          id="isAvailable"
          type="checkbox"
          checked={isAvailable}
          onChange={(e) => setIsAvailable(e.target.checked)}
          className="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
        />
        <label htmlFor="isAvailable" className="ml-2 block text-sm text-gray-900">
          Is Available
        </label>
      </div>

      <div>
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
        >
          {isSubmitting ? 'Submitting...' : submitButtonText}
        </button>
      </div>
    </form>
  );
};

export default VenueForm;
