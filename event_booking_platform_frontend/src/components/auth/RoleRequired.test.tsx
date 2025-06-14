import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import RoleRequired from './RoleRequired';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));

// Mock common components
jest.mock('@/components/common/LoadingSpinner', () => ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>);
jest.mock('@/components/common/AlertMessage', () => ({ message, type }: { message: string, type: string }) => <div data-testid="alert-message" data-type={type}>{message}</div>);

// Mock useAuth hook
jest.mock('@/contexts/AuthContext', () => ({
  ...jest.requireActual('@/contexts/AuthContext'), // Keep other exports
  useAuth: jest.fn(),
}));

const TestChildComponent = () => <div data-testid="child-component">Protected Content</div>;

describe('RoleRequired Component', () => {
  const mockPush = jest.fn();
  let mockHasRole = jest.fn();
  const baseMockUser = { id: 'user1', username: 'testuser', email: 'test@example.com', roles: [] };

  beforeEach(() => {
    mockPush.mockClear();
    mockHasRole.mockClear().mockReturnValue(false);
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
    (useAuth as jest.Mock).mockReturnValue({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      hasRole: mockHasRole,
      token: null,
      login: jest.fn(),
      logout: jest.fn(),
      fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
    });
  });
  it('shows loading spinner when auth context is loading', () => {
    (useAuth as jest.Mock).mockReturnValueOnce({ isLoading: true, isAuthenticated: false, user: null, hasRole: mockHasRole });
    render(<RoleRequired requiredRoles='ANY_ROLE'><TestChildComponent /></RoleRequired>);
    expect(screen.getByTestId('loading-spinner')).toHaveTextContent('Authenticating...');
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
  });
  it('redirects to fallbackUrl if user is not authenticated', async () => {
    (useAuth as jest.Mock).mockReturnValueOnce({ isLoading: false, isAuthenticated: false, user: null, hasRole: mockHasRole });
    render(<RoleRequired requiredRoles='ANY_ROLE' fallbackUrl='/login'><TestChildComponent /></RoleRequired>);
    await waitFor(() => expect(mockPush).toHaveBeenCalledWith('/login'));
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
  });
  it('renders children if user has the required single role', () => {
    const userWithRole = { ...baseMockUser, roles: ['USER'] };
    mockHasRole = jest.fn((role: string) => userWithRole.roles.includes(role));
    (useAuth as jest.Mock).mockReturnValueOnce({ isLoading: false, isAuthenticated: true, user: userWithRole, hasRole: mockHasRole });
    render(<RoleRequired requiredRoles='USER'><TestChildComponent /></RoleRequired>);
    expect(screen.getByTestId('child-component')).toBeInTheDocument();
  });
  it('shows error message if showError is true and user does not have the role', () => {
    const userWithoutRole = { ...baseMockUser, roles: ['VIEWER'] };
    mockHasRole = jest.fn((role: string) => userWithoutRole.roles.includes(role));
    (useAuth as jest.Mock).mockReturnValueOnce({ isLoading: false, isAuthenticated: true, user: userWithoutRole, hasRole: mockHasRole });
    render(<RoleRequired requiredRoles='ADMIN' showError={true}><TestChildComponent /></RoleRequired>);
    expect(screen.getByTestId('alert-message')).toHaveTextContent('You are not authorized to view this page.');
    expect(screen.queryByTestId('child-component')).not.toBeInTheDocument();
  });

});
