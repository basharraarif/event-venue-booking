import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import VenueCard from './VenueCard'; // Adjust path if your file structure is different
import { Venue } from '@/services/venueService'; // Assuming path alias is set up for @/

// Mock Next.js Link component
jest.mock('next/link', () => {
  return ({ children, href }) => {
    return <a href={href}>{children}</a>;
  };
});

const mockVenue: Venue = {
  id: 1,
  name: 'Test Venue Name',
  address: '123 Test Address, Test City',
  capacity: 120,
  amenities: ['WiFi', 'Projector'],
  pricing_per_hour: '50.00',
  pricing_per_day: '400.00',
  is_available: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('VenueCard Component', () => {
  it('renders venue details correctly', () => {
    render(<VenueCard venue={mockVenue} />);

    expect(screen.getByText(mockVenue.name)).toBeInTheDocument();
    expect(screen.getByText(mockVenue.address)).toBeInTheDocument();
    expect(
      screen.getByText(`Capacity: ${mockVenue.capacity}`)
    ).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument(); // Since is_available is true

    // Check pricing (ensure parseFloat and toFixed are handled if values can be null)
    if (mockVenue.pricing_per_hour) {
      expect(
        screen.getByText(
          `Price per hour: $${parseFloat(mockVenue.pricing_per_hour).toFixed(2)}`
        )
      ).toBeInTheDocument();
    }
    if (mockVenue.pricing_per_day) {
      expect(
        screen.getByText(
          `Price per day: $${parseFloat(mockVenue.pricing_per_day).toFixed(2)}`
        )
      ).toBeInTheDocument();
    }
  });

  it('shows "Not Available" when venue is not available', () => {
    const unavailableVenue = { ...mockVenue, is_available: false };
    render(<VenueCard venue={unavailableVenue} />);
    expect(screen.getByText('Not Available')).toBeInTheDocument();
  });

  it('shows "Pricing not available" when prices are null', () => {
    const noPriceVenue = {
      ...mockVenue,
      pricing_per_hour: null,
      pricing_per_day: null,
    };
    render(<VenueCard venue={noPriceVenue} />);
    expect(screen.getByText('Pricing not available')).toBeInTheDocument();
  });

  it('renders amenities if they are an array of strings', () => {
    const venueWithArrayAmenities = {
      ...mockVenue,
      amenities: ['Parking', 'Sound System'],
    };
    render(<VenueCard venue={venueWithArrayAmenities} />);
    expect(screen.getByText(/Parking/i)).toBeInTheDocument();
    expect(screen.getByText(/Sound System/i)).toBeInTheDocument();
  });

  it('renders amenities if they are an object', () => {
    const venueWithObjectAmenities = {
      ...mockVenue,
      amenities: { wifi: 'yes', screen: 'available' },
    };
    render(<VenueCard venue={venueWithObjectAmenities} />);
    expect(screen.getByText(/wifi: yes/i)).toBeInTheDocument();
    expect(screen.getByText(/screen: available/i)).toBeInTheDocument();
  });

  it('has an "Edit" link pointing to the correct URL', () => {
    render(<VenueCard venue={mockVenue} />);
    const editLink = screen.getByRole('link', { name: /edit/i });
    expect(editLink).toBeInTheDocument();
    expect(editLink).toHaveAttribute('href', `/venues/${mockVenue.id}/edit`);
  });

  it('has a "Delete" button', () => {
    render(<VenueCard venue={mockVenue} />);
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    expect(deleteButton).toBeInTheDocument();
    // Further interaction tests for delete would require mocking window.alert or the delete service
  });
});
