import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Header from './Header';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext'; // Import the actual hook

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));

// Mock useAuth hook
jest.mock('@/contexts/AuthContext', () => ({
  ...jest.requireActual('@/contexts/AuthContext'), // Important to keep other exports if any
  useAuth: jest.fn(),
}));

const ROLE_ADMIN = 'ADMIN';
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_CUSTOMER = 'CUSTOMER';

describe('Header Component', () => {
  const mockPush = jest.fn();
  let mockLogin = jest.fn();
  let mockLogout = jest.fn();
  let mockHasRole = jest.fn();

  beforeEach(() => {
    mockLogin.mockClear();
    mockLogout.mockClear();
    mockHasRole.mockClear().mockReturnValue(false);
    (useRouter as jest.Mock).mockReturnValue({ push: mockPush });
    (useAuth as jest.Mock).mockReturnValue({
      user: null,
      isAuthenticated: false,
      login: mockLogin,
      logout: mockLogout,
      isLoading: false,
      hasRole: mockHasRole,
      token: null,
      fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
    });
  });
  it('renders basic links for unauthenticated users', () => {
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: false, user: null, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    expect(screen.getByText('EventPilot')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
    expect(screen.getByText('Venues')).toBeInTheDocument();
    expect(screen.getByText('Login')).toBeInTheDocument();
    expect(screen.getByText('Sign Up')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Logout')).not.toBeInTheDocument();
  });

  it('renders links for authenticated customer user', () => {
    const customerUser = { id: 'cust1', username: 'customer', email: 'cust@example.com', roles: [ROLE_CUSTOMER] };
    mockHasRole = jest.fn((roleName: string) => customerUser.roles.includes(roleName));
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: true, user: customerUser, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText(`Logout (${customerUser.username})`)).toBeInTheDocument();
    // Customer should not see Create Event or Create Venue
    expect(screen.queryByText('Create Event')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Venue')).not.toBeInTheDocument();
  });

  it('shows "Create Event" link for Event Organizer', () => {
    const eventOrganizerUser = { id: 'eo1', username: 'eventorg', email: 'eo@example.com', roles: [ROLE_EVENT_ORGANIZER] };
    mockHasRole = jest.fn((roleName: string) => eventOrganizerUser.roles.includes(roleName));
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: true, user: eventOrganizerUser, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    expect(screen.getByText('Create Event')).toBeInTheDocument();
    expect(screen.queryByText('Create Venue')).not.toBeInTheDocument();
  });

  it('shows "Create Venue" link for Venue Manager', () => {
    const venueManagerUser = { id: 'vm1', username: 'venueman', email: 'vm@example.com', roles: [ROLE_VENUE_MANAGER] };
    mockHasRole = jest.fn((roleName: string) => venueManagerUser.roles.includes(roleName));
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: true, user: venueManagerUser, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    expect(screen.getByText('Create Venue')).toBeInTheDocument();
    expect(screen.queryByText('Create Event')).not.toBeInTheDocument();
  });

  it('shows both "Create Event" and "Create Venue" links for user with both roles', () => {
    const multiRoleUser = { id: 'mr1', username: 'multirole', email: 'mr@example.com', roles: [ROLE_EVENT_ORGANIZER, ROLE_VENUE_MANAGER] };
    mockHasRole = jest.fn((roleName: string) => multiRoleUser.roles.includes(roleName));
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: true, user: multiRoleUser, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    expect(screen.getByText('Create Event')).toBeInTheDocument();
    expect(screen.getByText('Create Venue')).toBeInTheDocument();
  });

  it('calls logout function from context when logout button is clicked', () => {
    const user = { id: 'user1', username: 'testlogout', email: 'logout@example.com', roles: [] };
    (useAuth as jest.Mock).mockReturnValueOnce({ isAuthenticated: true, user: user, isLoading: false, logout: mockLogout, hasRole: mockHasRole });
    render(<Header />);
    fireEvent.click(screen.getByText(`Logout (${user.username})`));
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

});
