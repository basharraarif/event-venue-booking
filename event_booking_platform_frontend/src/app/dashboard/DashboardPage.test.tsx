import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import DashboardPage from './page';
import { useAuth } from '@/contexts/AuthContext';
import bookingService from '@/services/bookingService';
import eventService from '@/services/eventService';
import venueService from '@/services/venueService';

jest.mock('@/services/bookingService');
jest.mock('@/services/eventService');
jest.mock('@/services/venueService');

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

const mockUseAuth = useAuth as jest.Mock;

// Define role constants matching those used in AuthContext and components
const ROLE_CUSTOMER = 'CUSTOMER';
const ROLE_EVENT_ORGANIZER = 'EVENT_ORGANIZER';
const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_ADMIN = 'ADMIN';


describe('DashboardPage', () => {
  beforeEach(() => {
    // Clear all mocks and reset default implementations
    jest.clearAllMocks();
    (bookingService.getMyBookings as jest.Mock).mockResolvedValue([]);
    (eventService.getEvents as jest.Mock).mockResolvedValue([]);
    (venueService.getVenues as jest.Mock).mockResolvedValue({ results: [] });
  });

  // Helper to set up mock useAuth return value for a test
  const setupMockAuth = (user: any, roles: string[] = []) => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: !!user,
      isLoading: false,
      user: user ? { ...user, roles } : null,
      hasRole: (role: string) => roles.includes(role),
      // Add other AuthContext values if needed by DashboardPage
      login: jest.fn(),
      logout: jest.fn(),
      fetchAndUpdateUser: jest.fn(),
      token: user ? 'fake-token' : null,
    });
  };

  const mockUserCustomer = { id: 'user-cust-123', username: 'customer1' };
  const mockUserOrganizer = { id: 'user-org-456', username: 'organizer1' };
  const mockUserVenueManager = { id: 'user-vm-789', username: 'manager1' };
  const mockUserAllRoles = { id: 'user-all-000', username: 'multirole' };


  test('shows login prompt if not authenticated', () => {
    setupMockAuth(null);
    render(<DashboardPage />);
    expect(screen.getByText(/please log in to view your dashboard/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /login/i })).toBeInTheDocument();
  });

  test('shows loading state while auth is loading', () => {
    mockUseAuth.mockReturnValueOnce({ isAuthenticated: false, isLoading: true, user: null, hasRole: () => false });
    render(<DashboardPage />);
    expect(screen.getByText(/loading user information.../i)).toBeInTheDocument();
  });

  test('fetches and displays "My Bookings" for any authenticated user', async () => {
    setupMockAuth(mockUserCustomer, [ROLE_CUSTOMER]);
    (bookingService.getMyBookings as jest.Mock).mockResolvedValue([{ id: 'b1', event_details: { name: 'My Booked Event' }, number_of_tickets: 2, total_price: '50.00', status: 'confirmed' }]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/my bookings/i)).toBeInTheDocument();
      expect(screen.getByText(/my booked event/i)).toBeInTheDocument();
    });
    expect(bookingService.getMyBookings as jest.Mock).toHaveBeenCalledTimes(1);
  });

  test('displays "My Events" section and fetches events for an Event Organizer', async () => {
    setupMockAuth(mockUserOrganizer, [ROLE_EVENT_ORGANIZER]);
    (eventService.getEvents as jest.Mock).mockResolvedValue([{ id: 'e1', name: 'My Organized Event', start_time: new Date().toISOString(), status: 'upcoming' }]);

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/my events \(organized by me\)/i)).toBeInTheDocument();
      expect(screen.getByText(/my organized event/i)).toBeInTheDocument();
    });
    expect(eventService.getEvents as jest.Mock).toHaveBeenCalledWith({ organizer: mockUserOrganizer.id });
  });

  test('does not display "My Events" section for a non-organizer (e.g. Customer)', async () => {
    setupMockAuth(mockUserCustomer, [ROLE_CUSTOMER]);

    render(<DashboardPage />);

    await waitFor(() => expect(bookingService.getMyBookings as jest.Mock).toHaveBeenCalled());
    expect(screen.queryByText(/my events \(organized by me\)/i)).not.toBeInTheDocument();
    expect(eventService.getEvents as jest.Mock).not.toHaveBeenCalled();
  });

  test('displays "My Venues" section and fetches venues for a Venue Manager', async () => {
    setupMockAuth(mockUserVenueManager, [ROLE_VENUE_MANAGER]);
    (venueService.getVenues as jest.Mock).mockResolvedValue({ results: [{ id: 'v1', name: 'My Managed Venue', capacity: 100 }] });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/my venues \(managed by me\)/i)).toBeInTheDocument();
      expect(screen.getByText(/my managed venue/i)).toBeInTheDocument();
    });
    expect(venueService.getVenues as jest.Mock).toHaveBeenCalledWith({ owner: mockUserVenueManager.id });
  });

  test('does not display "My Venues" section for a non-venue manager (e.g. Customer)', async () => {
    setupMockAuth(mockUserCustomer, [ROLE_CUSTOMER]);

    render(<DashboardPage />);

    await waitFor(() => expect(bookingService.getMyBookings as jest.Mock).toHaveBeenCalled());
    expect(screen.queryByText(/my venues \(managed by me\)/i)).not.toBeInTheDocument();
    expect(venueService.getVenues as jest.Mock).not.toHaveBeenCalled();
  });

  test('displays all relevant sections for a user with multiple roles', async () => {
    setupMockAuth(mockUserAllRoles, [ROLE_CUSTOMER, ROLE_EVENT_ORGANIZER, ROLE_VENUE_MANAGER]);
    (bookingService.getMyBookings as jest.Mock).mockResolvedValue([{ id: 'b1', event_details: { name: 'Multi-role Booking' }, number_of_tickets: 1, total_price: '20.00', status: 'pending' }]);
    (eventService.getEvents as jest.Mock).mockResolvedValue([{ id: 'e1', name: 'Multi-role Event', start_time: new Date().toISOString(), status: 'upcoming' }]);
    (venueService.getVenues as jest.Mock).mockResolvedValue({ results: [{ id: 'v1', name: 'Multi-role Venue', capacity: 200 }] });

    render(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText(/my bookings/i)).toBeInTheDocument();
      expect(screen.getByText(/multi-role booking/i)).toBeInTheDocument();
      expect(screen.getByText(/my events \(organized by me\)/i)).toBeInTheDocument();
      expect(screen.getByText(/multi-role event/i)).toBeInTheDocument();
      expect(screen.getByText(/my venues \(managed by me\)/i)).toBeInTheDocument();
      expect(screen.getByText(/multi-role venue/i)).toBeInTheDocument();
    });
    expect(bookingService.getMyBookings as jest.Mock).toHaveBeenCalledTimes(1);
    expect(eventService.getEvents as jest.Mock).toHaveBeenCalledWith({ organizer: mockUserAllRoles.id });
    expect(venueService.getVenues as jest.Mock).toHaveBeenCalledWith({ owner: mockUserAllRoles.id });
  });

  test('shows error message for bookings if fetching fails', async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: true, isLoading: false, user: mockUserCustomer });
    (bookingService.getMyBookings as jest.Mock).mockRejectedValueOnce(new Error('Failed to load bookings'));
    render(<DashboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/failed to load your bookings/i)).toBeInTheDocument();
    });
  });

});
