import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import RoleRequired from './RoleRequired'; // Assuming RoleRequired.tsx is in the same directory
import { AuthContext, AuthContextType, User } from '@/contexts/AuthContext'; // Import actual type
import { useRouter } from 'next/navigation';
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Import actual component for checking
import AlertMessage from '@/components/common/AlertMessage';   // Import actual component

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock common components if they render null or simple placeholders during tests
jest.mock('@/components/common/LoadingSpinner', () => ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>);
jest.mock('@/components/common/AlertMessage', () => ({ message, type }: { message: string, type: string }) => <div data-testid="alert-message" data-type={type}>{message}</div>);


const mockAuthContextValueBase: AuthContextType = {
  isAuthenticated: false,
  user: null,
  token: null,
  isLoading: false,
  login: jest.fn(),
  logout: jest.fn(),
  fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
  hasRole: jest.fn().mockReturnValue(false),
};

const mockPush = jest.fn();
(useRouter as jest.Mock).mockReturnValue({ push: mockPush });


const TestChildComponent = () => <div data-testid="child-component">Protected Content</div>;

const renderRoleRequired = (
  authValue: Partial<AuthContextType>,
  requiredRoles: string[] | string,
  fallbackUrl?: string,
  showError?: boolean
) => {
  const fullAuthValue = { ...mockAuthContextValueBase, ...authValue };
  return render(
    <AuthContext.Provider value={fullAuthValue}>
      <RoleRequired requiredRoles={requiredRoles} fallbackUrl={fallbackUrl} showError={showError}>
        <TestChildComponent />
      </RoleRequired>
    </AuthContext.Provider>
  );
};


describe('RoleRequired Component', () => {
  beforeEach(() => {
    mockAuthContextValueBase.hasRole.mockClear().mockReturnValue(false);
    mockPush.mockClear();
  });

  it('shows loading spinner when auth context is loading', () => {
    renderRoleRequired({ isLoading: true }, 'ANY_ROLE');
    expect(screen.getByTestId('loading-spinner')).toHaveTextContent('Authenticating...');
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
  });

  it('redirects to fallbackUrl if user is not authenticated', async () => {
    renderRoleRequired({ isAuthenticated: false, isLoading: false }, 'ANY_ROLE', '/login');
    // Expect redirection to be called. Since redirection might happen quickly,
    // content might not be rendered or a loader might show briefly.
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login'));
    // Optional: Check that child is not rendered, or a loader specific to redirecting is shown
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
    expect(screen.getByTestId('loading-spinner')).toHaveTextContent('Redirecting...'); // As per RoleRequired's current implementation
  });

  it('renders children if user has the required single role', () => {
    const userWithRole: User = { id: 'user1', username: 'test', email: '', roles: ['USER'] };
    renderRoleRequired(
      { isAuthenticated: true, user: userWithRole, isLoading: false, hasRole: (role) => role === 'USER' },
      'USER'
    );
    expect(screen.getByTestId('child-component')).toBeInTheDocument();
  });

  it('renders children if user has one of the required multiple roles', () => {
    const userWithRole: User = { id: 'user1', username: 'test', email: '', roles: ['EDITOR'] };
    renderRoleRequired(
      { isAuthenticated: true, user: userWithRole, isLoading: false, hasRole: (role) => role === 'EDITOR' },
      ['ADMIN', 'EDITOR']
    );
    expect(screen.getByTestId('child-component')).toBeInTheDocument();
  });

  it('redirects to fallbackUrl if user does not have the required role', async () => {
    const userWithoutRole: User = { id: 'user1', username: 'test', email: '', roles: ['VIEWER'] };
    renderRoleRequired(
      { isAuthenticated: true, user: userWithoutRole, isLoading: false, hasRole: (role) => userWithoutRole.roles.includes(role) },
      'ADMIN',
      '/unauthorized'
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/unauthorized'));
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
  });

  it('shows error message if showError is true and user does not have the role', () => {
    const userWithoutRole: User = { id: 'user1', username: 'test', email: '', roles: ['VIEWER'] };
    renderRoleRequired(
      { isAuthenticated: true, user: userWithoutRole, isLoading: false, hasRole: (role) => userWithoutRole.roles.includes(role) },
      'ADMIN',
      undefined, // No fallbackUrl, relying on showError
      true
    );
    expect(screen.getByTestId('alert-message')).toHaveTextContent('You are not authorized to view this page.');
    expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'error');
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled(); // Should not redirect if showError is true
  });

  it('uses default fallbackUrl if none provided and user unauthorized', async () => {
    const userWithoutRole: User = { id: 'user1', username: 'test', email: '', roles: ['VIEWER'] };
    renderRoleRequired(
      { isAuthenticated: true, user: userWithoutRole, isLoading: false, hasRole: (role) => userWithoutRole.roles.includes(role) },
      'ADMIN'
      // No fallbackUrl, no showError
    );
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/')); // Default fallback is '/'
  });

});
