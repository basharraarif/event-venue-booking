import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AddVenuePage from './page'; // Path to the AddVenuePage component
import { createVenue } from '@/services/venueService';
import { AuthProvider } from '@/contexts/AuthContext'; // To wrap page as it uses withAuth HOC

// Mock services and navigation
jest.mock('@/services/venueService');
const mockCreateVenue = createVenue as jest.MockedFunction<typeof createVenue>;

const mockRouterPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, replace: jest.fn() })),
  useParams: jest.fn(() => ({})), // Not used here but good to have a default mock
  usePathname: jest.fn(() => '/venues/new'),
}));

// Mock the withAuth HOC to just render the wrapped component
// Or provide a mock AuthContext if withAuth relies on it directly and deeply
jest.mock('@/components/auth/withAuth', () => (WrappedComponent) => {
    // eslint-disable-next-line react/display-name
    return (props) => <WrappedComponent {...props} />;
});


// Helper to render with AuthProvider, as AddVenuePage is wrapped by withAuth which uses useAuth
const renderWithAuthProvider = (ui: React.ReactElement) => {
  return render(
    <AuthProvider>
      {ui}
    </AuthProvider>
  );
};

describe('AddVenuePage Component', () => {
  beforeEach(() => {
    mockCreateVenue.mockClear();
    mockRouterPush.mockClear();
  });

  it('renders the VenueForm', () => {
    renderWithAuthProvider(<AddVenuePage />);
    expect(screen.getByRole('heading', { name: /add new venue/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument(); // Check for a form field
    expect(screen.getByRole('button', { name: /create venue/i })).toBeInTheDocument();
  });

  it('calls createVenue and redirects on successful submission', async () => {
    const newVenueData = {
      name: 'Test Create Venue',
      address: '123 Create St',
      capacity: 100,
      amenities: ['Pool'],
      pricing_per_hour: "100",
      pricing_per_day: null,
      is_available: true,
    };
    mockCreateVenue.mockResolvedValueOnce({ ...newVenueData, id: 3, created_at: '', updated_at: '' });

    renderWithAuthProvider(<AddVenuePage />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: newVenueData.name } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: newVenueData.address } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: String(newVenueData.capacity) } });
    fireEvent.change(screen.getByLabelText(/amenities/i), { target: { value: (newVenueData.amenities as string[]).join(', ') } });
    fireEvent.change(screen.getByLabelText(/price per hour/i), { target: { value: newVenueData.pricing_per_hour } });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
      expect(mockCreateVenue).toHaveBeenCalledTimes(1);
      expect(mockCreateVenue).toHaveBeenCalledWith(newVenueData);
    });

    expect(screen.getByText(/venue "Test Create Venue" created successfully!/i)).toBeInTheDocument();

    // Check for redirect (may need to adjust timing if there's a delay in component)
    await waitFor(() => {
        expect(mockRouterPush).toHaveBeenCalledWith('/venues');
    }, { timeout: 3000 }); // Increased timeout for the setTimeout in component
  });

  it('displays an error message if createVenue fails', async () => {
    mockCreateVenue.mockRejectedValueOnce(new Error('Creation Failed'));
    renderWithAuthProvider(<AddVenuePage />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Fail Venue' } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Fail Address' } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '50' } });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
      expect(screen.getByText(/failed to create venue: Creation Failed/i)).toBeInTheDocument();
    });
    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it('shows submitting state on button when form is being submitted', async () => {
    mockCreateVenue.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ id: 1, name: 'Delayed Venue', address:'', capacity:1, amenities:[], pricing_per_hour:null, pricing_per_day:null, is_available:true, created_at:'', updated_at:'' }), 100)));
    renderWithAuthProvider(<AddVenuePage />);

    fireEvent.change(screen.getByLabelText(/name/i), { target: { value: 'Submitting Venue' } });
    fireEvent.change(screen.getByLabelText(/address/i), { target: { value: 'Submitting Address' } });
    fireEvent.change(screen.getByLabelText(/capacity/i), { target: { value: '60' } });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
        expect(screen.getByRole('button', { name: /submitting.../i })).toBeDisabled();
    });
    // Wait for the submission to complete to avoid state update issues after unmount
    await waitFor(() => {
        expect(screen.getByText(/venue "Delayed Venue" created successfully!/i)).toBeInTheDocument();
    }, {timeout: 150});
  });
});
