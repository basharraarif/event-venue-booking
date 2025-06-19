import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProtectedEditEventPage from './page'; // Default export which includes RoleRequired
import { getEventById, updateEvent, Event } from '@/services/eventService'; // Assuming updateEvent
import { useAuth } from '@/contexts/AuthContext';

// Mock services and navigation
jest.mock('@/services/eventService');
const mockGetEventById = getEventById as jest.MockedFunction<
  typeof getEventById
>;
const mockUpdateEvent = updateEvent as jest.MockedFunction<typeof updateEvent>; // Assuming this exists

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
const mockRouterReplace = jest.fn();
let mockParams = { eventId: 'event1' }; // Default mock params

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: mockRouterPush,
    back: mockRouterBack,
    replace: mockRouterReplace,
  })),
  useParams: jest.fn(() => mockParams),
  usePathname: jest.fn(() => '/dashboard/organizer/events/edit/event1'),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext');
const mockUseAuth = useAuth as jest.Mock;

// Mock RoleRequired HOC/Component behavior for simplicity in page test
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

      if (auth.isLoading)
        return <div data-testid="loading-spinner">Mock Loading Auth...</div>;
      if (!auth.isAuthenticated) {
        if (showError)
          return (
            <div data-testid="mock-role-error">
              Not Authenticated (RoleRequired Mock)
            </div>
          );
        // Simulate redirect if not showing error
        if (typeof window !== 'undefined')
          mockRouterReplace('/login-mock-redirect');
        return null;
      }
      if (!userHasRequiredRole) {
        if (showError)
          return (
            <div data-testid="mock-role-error">
              Access Denied: Missing Role (RoleRequired Mock)
            </div>
          );
        // Simulate redirect if not showing error
        if (typeof window !== 'undefined')
          mockRouterReplace('/fallback-mock-redirect');
        return null;
      }
      return <>{children}</>; // Render children if role check passes
    }
);

// Mock common components
jest.mock(
  '@/components/common/LoadingSpinner',
  () =>
    ({ message }: { message: string }) => (
      <div data-testid="loading-spinner">{message}</div>
    )
);
jest.mock(
  '@/components/common/AlertMessage',
  () =>
    ({ message, type }: { message: string; type: string }) => (
      <div data-testid="alert-message" data-type={type}>
        {message}
      </div>
    )
);

const mockEventData: Event = {
  id: 'event1',
  name: 'Existing Event',
  description: 'An event to edit',
  venue: 'venue1',
  organizer: 'organizerUser123', // This ID should match the test user for ownership checks
  organizer_username: 'eventOrganizerUser',
  categories: [],
  start_time: new Date(Date.now() + 48 * 3600 * 1000).toISOString(),
  end_time: new Date(Date.now() + 50 * 3600 * 1000).toISOString(),
  status: 'upcoming',
  ticket_price: '25.00',
};

// Helper to render with specific AuthContext values
const renderPage = (
  authContextValue: Partial<ReturnType<typeof useAuth>>,
  currentParams = { eventId: 'event1' }
) => {
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
  mockParams = currentParams;
  return render(<ProtectedEditEventPage />);
};

describe('EditEventPage (ProtectedEditEventPage)', () => {
  const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
  const ROLE_ADMIN = 'ADMIN';
  const ROLE_CUSTOMER = 'CUSTOMER';

  const eventOrganizerOwner = {
    id: 'organizerUser123',
    username: 'eventOrganizerUser',
    roles: [ROLE_EVENT_ORGANIZER],
  };
  const eventOrganizerNonOwner = {
    id: 'otherOrganizerUser456',
    username: 'otherEventOrganizer',
    roles: [ROLE_EVENT_ORGANIZER],
  };
  const adminUser = {
    id: 'adminUser789',
    username: 'admin',
    roles: [ROLE_ADMIN],
  };
  const customerUser = {
    id: 'customerUser101',
    username: 'customer',
    roles: [ROLE_CUSTOMER],
  };

  beforeEach(() => {
    mockGetEventById.mockClear();
    if (mockUpdateEvent) mockUpdateEvent.mockClear(); // updateEvent might not be implemented yet
    mockRouterPush.mockClear();
    mockRouterBack.mockClear();
    mockRouterReplace.mockClear();
    mockUseAuth.mockReset();
    mockParams = { eventId: 'event1' };
  });

  it('blocks unauthenticated user (handled by RoleRequired mock)', () => {
    renderPage({ isAuthenticated: false, isLoading: false });
    expect(
      screen.queryByRole('heading', { name: /edit event/i })
    ).not.toBeInTheDocument();
    // Check for RoleRequired's mock message because showError is true on the page
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent(
      'Not Authenticated (RoleRequired Mock)'
    );
  });

  it('blocks authenticated user with incorrect role (e.g., CUSTOMER)', () => {
    renderPage({
      isAuthenticated: true,
      user: customerUser as any,
      isLoading: false,
      hasRole: (role: string) => customerUser.roles.includes(role),
    });
    expect(
      screen.queryByRole('heading', { name: /edit event/i })
    ).not.toBeInTheDocument();
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent(
      'Access Denied: Missing Role (RoleRequired Mock)'
    );
  });

  it('shows error for EVENT_ORGANIZER who is not the owner of the event', async () => {
    mockGetEventById.mockResolvedValueOnce(mockEventData); // mockEventData.organizer is "organizerUser123"
    renderPage({
      isAuthenticated: true,
      user: eventOrganizerNonOwner as any, // This user is an EO but not the owner
      isLoading: false,
      hasRole: (role: string) => eventOrganizerNonOwner.roles.includes(role),
    });

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent(
        'You are not authorized to edit this event.'
      );
    });
    expect(
      screen.queryByRole('heading', { name: /edit event/i })
    ).not.toBeInTheDocument();
  });

  it('renders placeholder form for ADMIN user (even if not owner)', async () => {
    mockGetEventById.mockResolvedValueOnce(mockEventData);
    renderPage({
      isAuthenticated: true,
      user: adminUser as any,
      isLoading: false,
      hasRole: (role: string) => adminUser.roles.includes(role),
    });

    await waitFor(() =>
      expect(mockGetEventById).toHaveBeenCalledWith('event1')
    );
    expect(
      screen.getByRole('heading', { name: `Edit Event: ${mockEventData.name}` })
    ).toBeInTheDocument();
    // Check for placeholder content since EventForm is not implemented
    expect(
      screen.getByText(/event editing form will be here/i)
    ).toBeInTheDocument();
  });

  it('renders placeholder form for EVENT_ORGANIZER who is the owner', async () => {
    mockGetEventById.mockResolvedValueOnce(mockEventData); // organizer is "organizerUser123"
    renderPage({
      isAuthenticated: true,
      user: eventOrganizerOwner as any, // This user is the owner
      isLoading: false,
      hasRole: (role: string) => eventOrganizerOwner.roles.includes(role),
    });

    await waitFor(() =>
      expect(mockGetEventById).toHaveBeenCalledWith('event1')
    );
    expect(
      screen.getByRole('heading', { name: `Edit Event: ${mockEventData.name}` })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/event editing form will be here/i)
    ).toBeInTheDocument();
  });

  it('displays error if event data fetching fails', async () => {
    mockGetEventById.mockRejectedValueOnce(new Error('Failed to fetch event'));
    renderPage({
      isAuthenticated: true,
      user: eventOrganizerOwner as any,
      isLoading: false,
      hasRole: (role: string) => eventOrganizerOwner.roles.includes(role),
    });
    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent(
        'Failed to load event details for editing.'
      );
    });
  });

  // Add tests for form submission (calling updateEvent) once EventForm is implemented
  // For example:
  // it('calls updateEvent on successful submission for authorized user', async () => { ... });
});
