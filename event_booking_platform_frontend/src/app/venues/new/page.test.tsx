import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import AddVenuePageInternal from './page'; // Import the actual page component (default export)
import { createVenue } from '@/services/venueService';
import { useAuth } from '@/contexts/AuthContext'; // Will be mocked

// Mock services and navigation
jest.mock('@/services/venueService');
const mockCreateVenue = createVenue as jest.MockedFunction<typeof createVenue>;

const mockRouterPush = jest.fn();
const mockRouterReplace = jest.fn(); // For RoleRequired redirection
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: mockRouterPush,
    replace: mockRouterReplace,
  })),
  useParams: jest.fn(() => ({})),
  usePathname: jest.fn(() => '/venues/new'),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext');
const mockUseAuth = useAuth as jest.Mock;

// Mock RoleRequired to simplify testing:
// It will use the mocked useAuth. If auth fails, it renders nothing or a message.
// If auth passes, it renders children.
jest.mock(
  '@/components/auth/RoleRequired',
  () =>
    ({ children, requiredRoles, showError }: any) => {
      const auth = useAuth(); // Uses the mocked useAuth
      const rolesToCheck = Array.isArray(requiredRoles)
        ? requiredRoles
        : [requiredRoles];
      const userHasRequiredRole = rolesToCheck.some((role: string) =>
        auth.hasRole(role)
      );

      if (auth.isLoading) return <div>Mock Loading Auth...</div>;
      if (!auth.isAuthenticated) {
        if (showError)
          return (
            <div data-testid="mock-role-error">
              Not Authenticated (RoleRequired Mock)
            </div>
          );
        // mockRouterReplace('/login-mock-redirect'); // Simulate redirect
        return null;
      }
      if (!userHasRequiredRole) {
        if (showError)
          return (
            <div data-testid="mock-role-error">
              Access Denied: Missing Role (RoleRequired Mock)
            </div>
          );
        // mockRouterReplace('/fallback-mock-redirect'); // Simulate redirect
        return null;
      }
      return <>{children}</>;
    }
);

// Helper to render with specific AuthContext values
const renderPage = (authContextValue: Partial<ReturnType<typeof useAuth>>) => {
  mockUseAuth.mockReturnValue({
    isAuthenticated: false,
    user: null,
    isLoading: false,
    hasRole: jest.fn().mockReturnValue(false),
    login: jest.fn(),
    logout: jest.fn(),
    fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
    token: null,
    ...authContextValue,
  });
  return render(<AddVenuePageInternal />);
};

describe('AddVenuePage Component (with Role Protection)', () => {
  const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
  const ROLE_CUSTOMER = 'CUSTOMER';

  beforeEach(() => {
    mockCreateVenue.mockClear();
    mockRouterPush.mockClear();
    mockRouterReplace.mockClear();
    mockUseAuth.mockReset();
  });

  it('does not render form for unauthenticated user (RoleRequired handles this)', () => {
    renderPage({ isAuthenticated: false, isLoading: false });
    // Expect RoleRequired's mock to prevent rendering or show its own message/redirect
    expect(
      screen.queryByRole('heading', { name: /add new venue/i })
    ).not.toBeInTheDocument();
    // Depending on RoleRequired mock, check for redirect or specific message if showError were true
  });

  it('does not render form for authenticated user without VENUE_MANAGER role', () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 'user1', roles: [ROLE_CUSTOMER] } as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_CUSTOMER,
    });
    expect(
      screen.queryByRole('heading', { name: /add new venue/i })
    ).not.toBeInTheDocument();
    // Check for RoleRequired's specific error message if showError={true} was used on the page
    // As page uses showError={true}, we expect the message from the RoleRequired mock
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent(
      'Access Denied: Missing Role (RoleRequired Mock)'
    );
  });

  it('renders the VenueForm for authenticated VENUE_MANAGER', () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 'vm1', roles: [ROLE_VENUE_MANAGER] } as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
    });
    expect(
      screen.getByRole('heading', { name: /add new venue/i })
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /create venue/i })
    ).toBeInTheDocument();
  });

  it('calls createVenue and redirects on successful submission for VENUE_MANAGER', async () => {
    renderPage({
      // Ensure user has VENUE_MANAGER role
      isAuthenticated: true,
      user: { id: 'vm1', roles: [ROLE_VENUE_MANAGER] } as any,
      isLoading: false,
      hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
    });
    const newVenueData = {
      name: 'Test Create Venue',
      address: '123 Create St',
      capacity: 100,
      amenities: ['Pool'],
      pricing_per_hour: '100',
      pricing_per_day: null,
      is_available: true,
    };
    mockCreateVenue.mockResolvedValueOnce({
      ...newVenueData,
      id: 3,
      created_at: '',
      updated_at: '',
    });

    renderWithAuthProvider(<AddVenuePageInternal />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: newVenueData.name },
    });
    fireEvent.change(screen.getByLabelText(/address/i), {
      target: { value: newVenueData.address },
    });
    fireEvent.change(screen.getByLabelText(/capacity/i), {
      target: { value: String(newVenueData.capacity) },
    });
    fireEvent.change(screen.getByLabelText(/amenities/i), {
      target: { value: (newVenueData.amenities as string[]).join(', ') },
    });
    fireEvent.change(screen.getByLabelText(/price per hour/i), {
      target: { value: newVenueData.pricing_per_hour },
    });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
      expect(mockCreateVenue).toHaveBeenCalledTimes(1);
      expect(mockCreateVenue).toHaveBeenCalledWith(newVenueData);
    });

    expect(
      screen.getByText(/venue "Test Create Venue" created successfully!/i)
    ).toBeInTheDocument();

    // Check for redirect (may need to adjust timing if there's a delay in component)
    await waitFor(
      () => {
        expect(mockRouterPush).toHaveBeenCalledWith('/venues');
      },
      { timeout: 3000 }
    ); // Increased timeout for the setTimeout in component
  });

  it('displays an error message if createVenue fails', async () => {
    mockCreateVenue.mockRejectedValueOnce(new Error('Creation Failed'));
    renderWithAuthProvider(<AddVenuePageInternal />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: 'Fail Venue' },
    });
    fireEvent.change(screen.getByLabelText(/address/i), {
      target: { value: 'Fail Address' },
    });
    fireEvent.change(screen.getByLabelText(/capacity/i), {
      target: { value: '50' },
    });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/failed to create venue: Creation Failed/i)
      ).toBeInTheDocument();
    });
    expect(mockRouterPush).not.toHaveBeenCalled();
  });

  it('shows submitting state on button when form is being submitted', async () => {
    mockCreateVenue.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(
            () =>
              resolve({
                id: 1,
                name: 'Delayed Venue',
                address: '',
                capacity: 1,
                amenities: [],
                pricing_per_hour: null,
                pricing_per_day: null,
                is_available: true,
                created_at: '',
                updated_at: '',
              }),
            100
          )
        )
    );
    renderWithAuthProvider(<AddVenuePageInternal />);

    fireEvent.change(screen.getByLabelText(/name/i), {
      target: { value: 'Submitting Venue' },
    });
    fireEvent.change(screen.getByLabelText(/address/i), {
      target: { value: 'Submitting Address' },
    });
    fireEvent.change(screen.getByLabelText(/capacity/i), {
      target: { value: '60' },
    });

    fireEvent.submit(screen.getByRole('button', { name: /create venue/i }));

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /submitting.../i })
      ).toBeDisabled();
    });
    // Wait for the submission to complete to avoid state update issues after unmount
    await waitFor(
      () => {
        expect(
          screen.getByText(/venue "Delayed Venue" created successfully!/i)
        ).toBeInTheDocument();
      },
      { timeout: 150 }
    );
  });
});
