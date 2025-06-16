import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EditVenuePageInternal from './page'; // Import the actual page component
import { getVenueById, updateVenue, Venue } from '@/services/venueService';
import { useAuth } from '@/contexts/AuthContext'; // Will be mocked

// Mock services and navigation
jest.mock('@/services/venueService');
const mockGetVenueById = getVenueById as jest.MockedFunction<typeof getVenueById>;
const mockUpdateVenue = updateVenue as jest.MockedFunction<typeof updateVenue>;

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
const mockRouterReplace = jest.fn(); // For RoleRequired redirection
let mockParams = { id: '1' }; // Default mock params
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, back: mockRouterBack, replace: mockRouterReplace })),
  useParams: jest.fn(() => mockParams),
  usePathname: jest.fn((() => '/venues/1/edit')),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext');
const mockUseAuth = useAuth as jest.Mock;

// Mock RoleRequired
jest.mock('@/components/auth/RoleRequired', () => ({ children, requiredRoles, showError }: any) => {
  const auth = useAuth(); // Uses the mocked useAuth
  const rolesToCheck = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles];
  const userHasRequiredRole = rolesToCheck.some((role: string) => auth.hasRole(role));

  if (auth.isLoading) return <div>Mock Loading Auth...</div>;
  if (!auth.isAuthenticated) {
    if (showError) return <div data-testid="mock-role-error">Not Authenticated (RoleRequired Mock)</div>;
    return null;
  }
  if (!userHasRequiredRole) {
    if (showError) return <div data-testid="mock-role-error">Access Denied: Missing Role (RoleRequired Mock)</div>;
    return null;
  }
  return <>{children}</>;
});

// Mock common components
jest.mock('@/components/common/LoadingSpinner', () => ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>);
jest.mock('@/components/common/AlertMessage', () => ({ message, type }: { message: string, type: string }) => <div data-testid="alert-message" data-type={type}>{message}</div>);


const mockVenueData: Venue = {
  id: "1", // Changed to string to match typical UUIDs if used, or keep as number if backend uses number IDs
  name: 'Existing Venue',
  address: '1 Old Street',
  capacity: 80,
  amenities: ['Tables', 'Chairs'],
  pricing_per_hour: '40.00',
  pricing_per_day: '250.00',
  is_available: true,
  owner: { id: "venueOwner123", username: "venueOwnerUser" } as any, // Add owner for tests
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};


// Helper to render with specific AuthContext values (already defined in previous diff)
const renderPage = (authContextValue: Partial<ReturnType<typeof useAuth>>, currentParams = { id: '1' }) => {
  mockUseAuth.mockReturnValue({
    isAuthenticated: false, user: null, isLoading: false, hasRole: jest.fn().mockReturnValue(false),
    login: jest.fn(), logout: jest.fn(), fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined), token: null,
    ...authContextValue,
  });
  mockParams = currentParams; // Update mockParams for useParams()
  return render(<EditVenuePageInternal />);
};


describe('EditVenuePage Component (with Role and Ownership Protection)', () => {
  const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
  const ROLE_CUSTOMER = 'CUSTOMER';
  const venueOwnerUser = { id: "venueOwner123", username: "venueOwnerUser", roles: [ROLE_VENUE_MANAGER] };
  const nonOwnerUser = { id: "nonOwnerUser456", username: "nonOwner", roles: [ROLE_VENUE_MANAGER] };
  const customerUser = { id: "customer789", username: "customer", roles: [ROLE_CUSTOMER] };

  beforeEach(() => {
    mockGetVenueById.mockClear();
    mockUpdateVenue.mockClear();
    mockRouterPush.mockClear();
    mockRouterBack.mockClear();
    mockRouterReplace.mockClear();
    mockUseAuth.mockReset();
    mockParams = { id: '1' }; // Reset to default params
  });

  it('redirects unauthenticated user', async () => {
    renderPage({ isAuthenticated: false, isLoading: false });
    // RoleRequired mock will cause redirect or render its specific message
    // Check that the main form content is not rendered
    expect(screen.queryByRole('heading', { name: /edit venue/i })).not.toBeInTheDocument();
  });

  it('redirects authenticated user without VENUE_MANAGER role', async () => {
    renderPage({
      isAuthenticated: true,
      user: customerUser as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_CUSTOMER,
    });
    expect(screen.queryByRole('heading', { name: /edit venue/i })).not.toBeInTheDocument();
    // Check for RoleRequired's mock message
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent('Access Denied: Missing Role (RoleRequired Mock)');
  });

  it('shows error for VENUE_MANAGER who is not the owner', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData); // mockVenueData owner is venueOwner123
    renderPage({
      isAuthenticated: true,
      user: nonOwnerUser as any, // This user is a VM but not the owner of mockVenueData
      isLoading: false,
      hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
    });

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('You are not authorized to edit this venue.');
    });
    expect(screen.queryByRole('heading', { name: /edit venue/i })).not.toBeInTheDocument();
  });

  it('fetches venue data and pre-fills the form for VENUE_MANAGER owner', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData);
    renderPage({
      isAuthenticated: true,
      user: venueOwnerUser as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
    });

    await waitFor(() => expect(mockGetVenueById).toHaveBeenCalledWith('1'));
    await waitFor(() => expect(screen.getByLabelText(/name/i)).toHaveValue(mockVenueData.name));
    expect(screen.getByLabelText(/address/i)).toHaveValue(mockVenueData.address);
    expect(screen.getByLabelText(/capacity/i)).toHaveValue(mockVenueData.capacity);
    // Ensure amenities are joined correctly if they are an array
    const amenitiesValue = Array.isArray(mockVenueData.amenities) ? mockVenueData.amenities.join(', ') : mockVenueData.amenities;
    expect(screen.getByLabelText(/amenities/i)).toHaveValue(amenitiesValue);
  });

  it('calls updateVenue and redirects on successful submission for VENUE_MANAGER owner', async () => {
    mockGetVenueById.mockResolvedValueOnce(mockVenueData);
    renderPage({
      isAuthenticated: true,
      user: venueOwnerUser as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
    });
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
