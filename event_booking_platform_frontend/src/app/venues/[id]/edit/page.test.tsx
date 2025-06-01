import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EditVenuePage from './page'; // Path to the EditVenuePage component
import { getVenueById, updateVenue, Venue } from '@/services/venueService';
import { AuthProvider } from '@/contexts/AuthContext';

// Mock services and navigation
jest.mock('@/services/venueService');
const mockGetVenueById = getVenueById as jest.MockedFunction<typeof getVenueById>;
const mockUpdateVenue = updateVenue as jest.MockedFunction<typeof updateVenue>;

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
const mockUseParams = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, back: mockRouterBack, replace: jest.fn() })),
  useParams: jest.fn(() => mockUseParams()), // Use the mock function here
  usePathname: jest.fn((() => '/venues/1/edit')),
}));

// Mock the withAuth HOC
jest.mock('@/components/auth/withAuth', () => (WrappedComponent) => {
    // eslint-disable-next-line react/display-name
    return (props) => <WrappedComponent {...props} />;
});

const mockVenueData: Venue = {
  id: 1,
  name: 'Existing Venue',
  address: '1 Old Street',
  capacity: 80,
  amenities: ['Tables', 'Chairs'],
  pricing_per_hour: '40.00',
  pricing_per_day: '250.00',
  is_available: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// Helper to render with AuthProvider
const renderWithAuthProvider = (ui: React.ReactElement) => {
  return render(
    <AuthProvider>
      {ui}
    </AuthProvider>
  );
};

describe('EditVenuePage Component', () => {
  beforeEach(() => {
    mockGetVenueById.mockClear();
    mockUpdateVenue.mockClear();
    mockRouterPush.mockClear();
    mockRouterBack.mockClear();
    // Setup mock useParams to return a specific ID for each test
    mockUseParams.mockReturnValue({ id: '1' });
  });

  it('fetches venue data and pre-fills the form', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData);
    renderWithAuthProvider(<EditVenuePage />);

    await waitFor(() => {
      expect(mockGetVenueById).toHaveBeenCalledWith('1');
    });

    await waitFor(() => {
        expect(screen.getByLabelText(/name/i)).toHaveValue(mockVenueData.name);
    });
    expect(screen.getByLabelText(/address/i)).toHaveValue(mockVenueData.address);
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(mockVenueData.capacity);
    expect(screen.getByLabelText(/amenities/i)).toHaveValue((mockVenueData.amenities as string[]).join(', '));
  });

  it('calls updateVenue and redirects on successful submission', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData);
    const updatedVenueDetails = {
      name: 'Updated Venue Name',
      address: '1 New Street',
      capacity: 90,
      amenities: ['New Amenity'],
      pricing_per_hour: "45.00",
      pricing_per_day: null,
      is_available: false,
    };
    mockUpdateVenue.mockResolvedValueOnce({ ...updatedVenueDetails, id: 1, created_at: '', updated_at: '' });

    renderWithAuthProvider(<EditVenuePage />);
    await waitFor(() => expect(screen.getByLabelText(/name/i)).toHaveValue(mockVenueData.name)); // Ensure form is pre-filled

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: updatedVenueDetails.name } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: updatedVenueDetails.address } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: String(updatedVenueDetails.capacity) } });
    fireEvent.change(screen.getByLabelText(/amenities/i), { target: { value: (updatedVenueDetails.amenities as string[]).join(', ') } });
    fireEvent.change(screen.getByLabelText(/price per hour/i), { target: { value: updatedVenueDetails.pricing_per_hour } });
    fireEvent.change(screen.getByLabelText(/price per day/i), { target: { value: '' } }); // Explicitly clear the field for null
    fireEvent.click(screen.getByLabelText(/is available/i)); // Toggle to false

    fireEvent.submit(screen.getByRole('button', { name: /update venue/i }));

    await waitFor(() => {
      expect(mockUpdateVenue).toHaveBeenCalledTimes(1);
      expect(mockUpdateVenue).toHaveBeenCalledWith('1', updatedVenueDetails);
    });

    expect(screen.getByText(/venue "Updated Venue Name" updated successfully!/i)).toBeInTheDocument();
    await waitFor(() => {
        expect(mockRouterPush).toHaveBeenCalledWith('/venues');
    }, { timeout: 3000 });
  });

  it('displays an error message if getVenueById fails', async () => {
    mockGetVenueById.mockRejectedValueOnce(new Error('Venue fetch failed'));
    renderWithAuthProvider(<EditVenuePage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch venue details: Venue fetch failed/i)).toBeInTheDocument();
    });
  });

  it('displays an error message if updateVenue fails', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData);
    mockUpdateVenue.mockRejectedValueOnce(new Error('Update Failed'));
    renderWithAuthProvider(<EditVenuePage />);
    await waitFor(() => expect(screen.getByLabelText(/name/i)).toHaveValue(mockVenueData.name));

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Attempt Update' } });
    fireEvent.submit(screen.getByRole('button', { name: /update venue/i }));

    await waitFor(() => {
      expect(screen.getByText(/failed to update venue: Update Failed/i)).toBeInTheDocument();
    });
    expect(mockRouterPush).not.toHaveBeenCalled();
  });
});
