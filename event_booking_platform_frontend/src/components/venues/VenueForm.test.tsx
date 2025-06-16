import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VenueForm, { VenueFormData } from './VenueForm'; // Adjust path
import { Venue } from '@/services/venueService'; // Assuming path alias

const mockInitialData: Partial<Venue> = {
  name: 'Initial Name',
  address: 'Initial Address',
  capacity: 100,
  amenities: ['WiFi', 'Parking'],
  pricing_per_hour: '50.00',
  pricing_per_day: '300.00',
  is_available: true,
};

describe('VenueForm Component', () => {
  const mockOnSubmit = jest.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
  });

  it('renders empty form correctly', () => {
    render(<VenueForm onSubmit={mockOnSubmit} />);
    expect(screen.getByLabelText(/name/i)).toHaveValue('');
    expect(screen.getByLabelText(/address/i)).toHaveValue('');
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(null); // Number input empty
    expect(screen.getByLabelText(/amenities/i)).toHaveValue('');
    expect(screen.getByLabelText(/price per hour/i)).toHaveValue(null);
    expect(screen.getByLabelText(/price per day/i)).toHaveValue(null);
    expect(screen.getByLabelText(/is available/i)).toBeChecked();
  });

  it('renders form with initial data', () => {
    render(<VenueForm onSubmit={mockOnSubmit} initialData={mockInitialData} />);
    expect(screen.getByLabelText(/name/i)).toHaveValue(mockInitialData.name);
    expect(screen.getByLabelText(/address/i)).toHaveValue(mockInitialData.address);
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(mockInitialData.capacity);
    expect(screen.getByLabelText(/amenities/i)).toHaveValue((mockInitialData.amenities as string[]).join(', '));
    expect(screen.getByLabelText(/price per hour/i)).toHaveValue(parseFloat(mockInitialData.pricing_per_hour!));
    expect(screen.getByLabelText(/price per day/i)).toHaveValue(parseFloat(mockInitialData.pricing_per_day!));
    expect(screen.getByLabelText(/is available/i)).toBeChecked();
  });

  it('allows user to fill the form', () => {
    render(<VenueForm onSubmit={mockOnSubmit} />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'New Venue' } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'New Address' } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '150' } });
    fireEvent.change(screen.getByLabelText(/amenities/i), { target: { value: 'Projector, Stage' } });
    fireEvent.change(screen.getByLabelText(/price per hour/i), { target: { value: '75.50' } });
    fireEvent.click(screen.getByLabelText(/is available/i)); // Uncheck

    expect(screen.getByLabelText(/name/i)).toHaveValue('New Venue');
    expect(screen.getByLabelText(/address/i)).toHaveValue('New Address');
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(150);
    expect(screen.getByLabelText(/amenities/i)).toHaveValue('Projector, Stage');
    expect(screen.getByLabelText(/price per hour/i)).toHaveValue(75.50);
    expect(screen.getByLabelText(/is available/i)).not.toBeChecked();
  });

  it('calls onSubmit with correct data when form is valid', async () => {
    render(<VenueForm onSubmit={mockOnSubmit} />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Valid Venue' } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Valid Address' } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '200' } });
    fireEvent.change(screen.getByLabelText(/amenities/i), { target: { value: 'Sound System' } });
    fireEvent.change(screen.getByLabelText(/price per day/i), { target: { value: '500' } });

    fireEvent.submit(screen.getByRole('button', { name: /submit venue/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledTimes(1);
      expect(mockOnSubmit).toHaveBeenCalledWith({
        name: 'Valid Venue',
        address: 'Valid Address',
        capacity: 200,
        amenities: ['Sound System'],
        pricing_per_hour: null, // Because it wasn't filled
        pricing_per_day: '500',
        is_available: true,
      } as VenueFormData);
    });
  });

  it('shows validation errors for required fields', async () => {
    render(<VenueForm onSubmit={mockOnSubmit} />);
    fireEvent.submit(screen.getByRole('button', { name: /submit venue/i }));

    await waitFor(() => {
      expect(mockOnSubmit).not.toHaveBeenCalled();
      expect(screen.getByText('Name is required.')).toBeInTheDocument();
      expect(screen.getByText('Address is required.')).toBeInTheDocument();
      expect(screen.getByText('Capacity must be a positive number.')).toBeInTheDocument();
    });
  });

  it('shows validation error for invalid capacity', async () => {
    render(<VenueForm onSubmit={mockOnSubmit} />);
    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Test' } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Test Addr' } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '0' } }); // Invalid capacity
    fireEvent.submit(screen.getByRole('button', { name: /submit venue/i }));

    await waitFor(() => {
      expect(mockOnSubmit).not.toHaveBeenCalled();
      expect(screen.getByText('Capacity must be a positive number.')).toBeInTheDocument();
    });
  });

  it('displays custom submit button text', () => {
    render(<VenueForm onSubmit={mockOnSubmit} submitButtonText="Update Venue" />);
    expect(screen.getByRole('button', { name: /update venue/i })).toBeInTheDocument();
  });

  it('disables submit button when isSubmitting is true', () => {
    render(<VenueForm onSubmit={mockOnSubmit} isSubmitting={true} />);
    expect(screen.getByRole('button', { name: /submitting.../i })).toBeDisabled();
  });

  it('correctly processes amenities string for submission', async () => {
    // Test with various amenity string inputs
    const testCases = [
      { input: 'WiFi, Projector, Stage', expected: ['WiFi', 'Projector', 'Stage'] },
      { input: '  WiFi ,  Projector  ,Stage  ', expected: ['WiFi', 'Projector', 'Stage'] }, // Test with extra spaces
      { input: 'SingleAmenity', expected: ['SingleAmenity'] },
      { input: '', expected: [] }, // Test with empty string
      { input: ', ,', expected: [] }, // Test with only commas and spaces
      { input: 'WiFi,,Projector', expected: ['WiFi', 'Projector'] }, // Test with empty segments
    ];

    for (const tc of testCases) {
      mockOnSubmit.mockClear(); // Clear mock for each case
      render(<VenueForm onSubmit={mockOnSubmit} />);

      // Fill required fields to pass validation
      fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Amenity Test Venue' } });
      fireEvent.change(screen.getByLabelText(/address/i), { target: { value: '123 Amenity St' } });
      fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '100' } });

      // Set the amenities input
      fireEvent.change(screen.getByLabelText(/amenities/i), { target: { value: tc.input } });

      fireEvent.submit(screen.getByRole('button', { name: /submit venue/i }));

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledTimes(1);
        const submittedData = mockOnSubmit.mock.calls[0][0] as VenueFormData;
        expect(submittedData.amenities).toEqual(tc.expected);
      });
    }
  });
});
