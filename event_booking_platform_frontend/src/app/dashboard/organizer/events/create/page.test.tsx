import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ProtectedCreateEventPage from './page'; // Default export which includes RoleRequired
import { useAuth } from '@/contexts/AuthContext';
// Assuming EventForm is mocked as it's complex and has its own tests
// For this page-level test, we just want to ensure it renders for authorized users.
jest.mock('@/components/events/EventForm', () => () => <div data-testid="mock-event-form">Mock Event Form</div>);

// Mock services and navigation
const mockRouterPush = jest.fn();
const mockRouterReplace = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, replace: mockRouterReplace })),
  useParams: jest.fn(() => ({})),
  usePathname: jest.fn(() => '/dashboard/organizer/events/create'),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext');
const mockUseAuth = useAuth as jest.Mock;

// Mock RoleRequired HOC/Component behavior
jest.mock('@/components/auth/RoleRequired', () => ({ children, requiredRoles, showError }: any) => {
  const auth = useAuth(); // Uses the mocked useAuth
  const rolesToCheck = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles];
  const userHasRequiredRole = rolesToCheck.some((role: string) => auth.hasRole(role));

  if (auth.isLoading) return <div data-testid="loading-spinner">Mock Loading Auth...</div>;
  if (!auth.isAuthenticated) {
    if (showError) return <div data-testid="mock-role-error">Not Authenticated (RoleRequired Mock)</div>;
    if (typeof window !== 'undefined') mockRouterReplace('/login-mock-redirect');
    return null;
  }
  if (!userHasRequiredRole) {
    if (showError) return <div data-testid="mock-role-error">Access Denied: Missing Role (RoleRequired Mock)</div>;
    if (typeof window !== 'undefined') mockRouterReplace('/fallback-mock-redirect');
    return null;
  }
  return <>{children}</>;
});

// Mock common components that might be used by RoleRequired's error display
jest.mock('@/components/common/LoadingSpinner', () => ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>);
jest.mock('@/components/common/AlertMessage', () => ({ message, type }: { message: string, type: string }) => <div data-testid="alert-message" data-type={type}>{message}</div>);


// Helper to render with specific AuthContext values
const renderPage = (authContextValue: Partial<ReturnType<typeof useAuth>>) => {
  mockUseAuth.mockReturnValue({
    isAuthenticated: false, user: null, isLoading: false, hasRole: jest.fn().mockReturnValue(false),
    login: jest.fn(), logout: jest.fn(), fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined), token: null,
    ...authContextValue,
  });
  return render(<ProtectedCreateEventPage />);
};

describe('ProtectedCreateEventPage', () => {
  const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
  const ROLE_ADMIN = 'ADMIN';
  const ROLE_CUSTOMER = 'CUSTOMER';

  const eventOrganizerUser = { id: "organizerUser123", username: "eventOrganizerUser", roles: [ROLE_EVENT_ORGANIZER] };
  const adminUser = { id: "adminUser789", username: "admin", roles: [ROLE_ADMIN] };
  const customerUser = { id: "customerUser101", username: "customer", roles: [ROLE_CUSTOMER] };

  beforeEach(() => {
    mockRouterPush.mockClear();
    mockRouterReplace.mockClear();
    mockUseAuth.mockReset();
  });

  it('blocks unauthenticated user', () => {
    renderPage({ isAuthenticated: false, isLoading: false });
    expect(screen.queryByRole('heading', { name: /create new event/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent('Not Authenticated (RoleRequired Mock)');
  });

  it('blocks authenticated user with incorrect role (CUSTOMER)', () => {
    renderPage({
      isAuthenticated: true,
      user: customerUser as any,
      isLoading: false,
      hasRole: (role: string) => customerUser.roles.includes(role),
    });
    expect(screen.queryByRole('heading', { name: /create new event/i })).not.toBeInTheDocument();
    expect(screen.getByTestId('mock-role-error')).toHaveTextContent('Access Denied: Missing Role (RoleRequired Mock)');
  });

  it('renders the Create Event page for EVENT_ORGANIZER role', () => {
    renderPage({
      isAuthenticated: true,
      user: eventOrganizerUser as any,
      isLoading: false,
      hasRole: (role: string) => eventOrganizerUser.roles.includes(role),
    });
    expect(screen.getByRole('heading', { name: /create new event/i })).toBeInTheDocument();
    expect(screen.getByTestId('mock-event-form')).toBeInTheDocument(); // Check that EventForm (mocked) is rendered
  });

  it('renders the Create Event page for ADMIN role', () => {
    renderPage({
      isAuthenticated: true,
      user: adminUser as any,
      isLoading: false,
      hasRole: (role: string) => adminUser.roles.includes(role),
    });
    expect(screen.getByRole('heading', { name: /create new event/i })).toBeInTheDocument();
    expect(screen.getByTestId('mock-event-form')).toBeInTheDocument();
  });

  // Further tests would involve interactions with the EventForm itself,
  // which would require a more detailed mock or testing the EventForm component directly.
});
