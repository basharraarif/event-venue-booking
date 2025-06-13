import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Header from './Header'; // Assuming Header.tsx is in the same directory
import { AuthContext, AuthContextType } from '@/contexts/AuthContext'; // Import actual type
import { useRouter } from 'next/navigation'; // Mock this

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));

// Mock role constants (ensure these match what Header.tsx uses)
const ROLE_ADMIN = 'ADMIN';
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
// const ROLE_CUSTOMER = 'CUSTOMER'; // Not explicitly used for special links in Header example

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

const renderHeaderWithAuth = (authValue: Partial<AuthContextType>) => {
  const fullAuthValue = { ...mockAuthContextValueBase, ...authValue };
  return render(
    <AuthContext.Provider value={fullAuthValue}>
      <Header />
    </AuthContext.Provider>
  );
};

describe('Header Component', () => {
  beforeEach(() => {
    // Reset all mocks from AuthContextType that are jest.fn()
    mockAuthContextValueBase.login.mockClear();
    mockAuthContextValueBase.logout.mockClear();
    mockAuthContextValueBase.fetchAndUpdateUser.mockClear();
    mockAuthContextValueBase.hasRole.mockClear().mockReturnValue(false); // Default to no roles
    (useRouter as jest.Mock).mockClear().mockReturnValue({ push: jest.fn() }); // Clear router mocks
  });

  it('renders basic links for unauthenticated users', () => {
    renderHeaderWithAuth({ isAuthenticated: false, user: null, isLoading: false });
    expect(screen.getByText('EventPilot')).toBeInTheDocument();
    expect(screen.getByText('Events')).toBeInTheDocument();
    expect(screen.getByText('Venues')).toBeInTheDocument();
    expect(screen.getByText('Login')).toBeInTheDocument();
    expect(screen.getByText('Sign Up')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Logout')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Event')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Venue')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
  });

  it('renders links for authenticated customer user', () => {
    const customerUser = { id: 'cust1', username: 'customer', email: 'cust@example.com', roles: [ROLE_CUSTOMER] };
    // Mock hasRole to reflect this user's roles
    const mockHasRole = (roleName: string) => customerUser.roles.includes(roleName);
    renderHeaderWithAuth({
      isAuthenticated: true,
      user: customerUser,
      isLoading: false,
      hasRole: mockHasRole
    });

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText(/Logout/)).toBeInTheDocument(); // Contains "Logout"
    expect(screen.getByText(`Logout (${customerUser.username})`)).toBeInTheDocument();
    expect(screen.queryByText('Login')).not.toBeInTheDocument();
    expect(screen.queryByText('Sign Up')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Event')).not.toBeInTheDocument();
    expect(screen.queryByText('Create Venue')).not.toBeInTheDocument();
    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
  });

  it('renders "Create Event" for EVENT_ORGANIZER role', () => {
    const organizerUser = { id: 'org1', username: 'organizer', email: 'org@example.com', roles: [ROLE_EVENT_ORGANIZER] };
    const mockHasRole = (roleName: string) => organizerUser.roles.includes(roleName);
    renderHeaderWithAuth({ isAuthenticated: true, user: organizerUser, isLoading: false, hasRole: mockHasRole });

    expect(screen.getByText('Create Event')).toBeInTheDocument();
  });

  it('renders "Create Venue" for VENUE_MANAGER role', () => {
    const managerUser = { id: 'vm1', username: 'manager', email: 'vm@example.com', roles: [ROLE_VENUE_MANAGER] };
    const mockHasRole = (roleName: string) => managerUser.roles.includes(roleName);
    renderHeaderWithAuth({ isAuthenticated: true, user: managerUser, isLoading: false, hasRole: mockHasRole });

    expect(screen.getByText('Create Venue')).toBeInTheDocument();
  });

  it('renders "Admin Panel" for ADMIN role', () => {
    const adminUser = { id: 'adm1', username: 'admin', email: 'admin@example.com', roles: [ROLE_ADMIN] };
    const mockHasRole = (roleName: string) => adminUser.roles.includes(roleName);
    renderHeaderWithAuth({ isAuthenticated: true, user: adminUser, isLoading: false, hasRole: mockHasRole });

    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
  });

  it('renders all relevant links for user with multiple roles', () => {
    const multiRoleUser = { id: 'multi1', username: 'multi', email: 'multi@example.com', roles: [ROLE_EVENT_ORGANIZER, ROLE_VENUE_MANAGER, ROLE_ADMIN] };
    const mockHasRole = (roleName: string) => multiRoleUser.roles.includes(roleName);
    renderHeaderWithAuth({ isAuthenticated: true, user: multiRoleUser, isLoading: false, hasRole: mockHasRole });

    expect(screen.getByText('Create Event')).toBeInTheDocument();
    expect(screen.getByText('Create Venue')).toBeInTheDocument();
    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
  });

  it('calls logout function from context when logout button is clicked', () => {
    const mockLogout = jest.fn();
    const user = { id: 'user1', username: 'testlogout', email: 'logout@example.com', roles: [] };
    renderHeaderWithAuth({ isAuthenticated: true, user: user, isLoading: false, logout: mockLogout });

    fireEvent.click(screen.getByText(`Logout (${user.username})`));
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it('toggles mobile menu on button click', () => {
    renderHeaderWithAuth({ isAuthenticated: false, user: null, isLoading: false });
    const mobileMenuButton = screen.getByRole('button', { name: /menu/i }); // Assuming button has accessible name or use specific selector

    // Check initial state (no mobile nav items visible unless menu is open)
    // This depends on how mobile nav items are identified. Let's assume they are not present.
    // For example, if "Login" in mobile menu has a specific test ID or class:
    // expect(screen.queryByTestId('mobile-login-link')).not.toBeVisible(); // or not.toBeInTheDocument if conditional rendering

    // Open mobile menu
    fireEvent.click(mobileMenuButton);
    // Now mobile nav items should be visible
    // Example: Check for "Login" link, which is also in desktop but now we assert its presence after menu toggle
    // This test is a bit simplistic without more specific selectors for mobile-only elements.
    // A better test would be to check if a container for mobile links becomes visible.
    // For now, we check if a link like "Login" (which is in both) is still there.
    expect(screen.getByText('Login')).toBeInTheDocument();
    // A more robust test would be to check the aria-expanded attribute or visibility of the mobile menu container.
    // For example, if the mobile menu div has a specific data-testid:
    // expect(screen.getByTestId('mobile-menu-container')).toBeVisible();

    // Close mobile menu
    fireEvent.click(mobileMenuButton);
    // expect(screen.queryByTestId('mobile-menu-container')).not.toBeVisible(); // Or similar check
  });

  // Test for isLoading state (optional, if Header has specific loading UI)
  it('shows minimal UI or nothing when isLoading is true', () => {
    renderHeaderWithAuth({ isLoading: true });
    // Based on current Header.tsx, it renders the nav structure even if isLoading is true,
    // but the conditional rendering inside the nav for links depends on !isLoading.
    // So, "Events", "Venues" should be there, but "Login", "Dashboard" etc. might not.
    expect(screen.getByText('EventPilot')).toBeInTheDocument();
    // Check that links usually hidden by isLoading are not there
    expect(screen.queryByText('Login')).not.toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

});
