import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EventDetailBooking from './EventDetailBooking';
import { useAuth } from '@/contexts/AuthContext';
import eventService, { Event } from '@/services/eventService';
import bookingService from '@/services/bookingService';
import { useRouter } from 'next/navigation';

// Mocks
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));
jest.mock('@/contexts/AuthContext');
jest.mock('@/services/eventService');
jest.mock('@/services/bookingService');

const mockUseAuth = useAuth as jest.Mock;
const mockEventService = eventService as jest.Mocked<typeof eventService>;
const mockBookingService = bookingService as jest.Mocked<typeof bookingService>;
const mockUseRouter = useRouter as jest.Mock;
const mockRouterPush = jest.fn();

// Helper to provide default mock values for AuthContext
const getDefaultAuthMock = (isAuthenticated = true, user = { id: 'user123', roles: ['CUSTOMER'] }) => ({
  isAuthenticated,
  user,
  isLoading: false,
  hasRole: (role: string) => user.roles.includes(role),
  login: jest.fn(),
  logout: jest.fn(),
  fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
  token: 'fake-token',
});

const mockEventBase: Event = {
  id: 'evt1',
  name: 'Test Event with Capacity',
  description: 'A test event.',
  venue: 'venue1',
  organizer: 'org1',
  categories: [],
  start_time: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(), // Tomorrow
  end_time: new Date(Date.now() + 26 * 60 * 60 * 1000).toISOString(),
  status: 'upcoming',
  ticket_price: '20.00',
};

describe('EventDetailBooking Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue({ push: mockRouterPush });
    mockUseAuth.mockReturnValue(getDefaultAuthMock());
  });

  // Helper to render with mocked event data
  const renderComponent = (eventData: Partial<Event> = {}) => {
    const fullEventData = { ...mockEventBase, ...eventData };
    mockEventService.getEventById.mockResolvedValue({ data: fullEventData } as any); // `data` property for axios like structure
    return render(<EventDetailBooking eventId={fullEventData.id} />);
  };

  it('displays event details including capacity information', async () => {
    renderComponent({ max_capacity: 100, active_tickets_count: 20 });
    await waitFor(() => screen.getByText('Test Event with Capacity')); // Wait for event data to load

    expect(screen.getByText(/Max Capacity:/)).toHaveTextContent('Max Capacity: 100');
    expect(screen.getByText(/Tickets Available:/)).toHaveTextContent('Tickets Available: 80');
  });

  it('displays "Sold Out" when no tickets are available', async () => {
    renderComponent({ max_capacity: 50, active_tickets_count: 50 });
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    expect(screen.getByText(/Tickets Available:/)).toHaveTextContent('Sold Out');
    // Also check button text/state
    expect(screen.getByRole('button', { name: /sold out/i })).toBeDisabled();
  });

  it('displays "Unlimited" for capacity and tickets if effectiveCapacity is null', async () => {
    renderComponent({ max_capacity: null, venue_details: { capacity: null } as any, active_tickets_count: 5 });
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    expect(screen.getByText(/Max Capacity:/)).toHaveTextContent('Max Capacity: Unlimited');
    expect(screen.getByText(/Tickets Available:/)).toHaveTextContent('Tickets Available: Unlimited');
  });

  it('disables booking button if event is past or cancelled', async () => {
    renderComponent({ status: 'past', max_capacity: 10, active_tickets_count: 0 });
    await waitFor(() => screen.getByText('Test Event with Capacity'));
    expect(screen.getByRole('button', { name: /event past/i })).toBeDisabled();

    renderComponent({ status: 'cancelled', max_capacity: 10, active_tickets_count: 0 });
    await waitFor(() => screen.getByText('Test Event with Capacity'));
    expect(screen.getByRole('button', { name: /event cancelled/i })).toBeDisabled();
  });

  it('validates number of tickets client-side: cannot exceed available', async () => {
    renderComponent({ max_capacity: 10, active_tickets_count: 8 }); // 2 tickets available
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    const ticketsInput = screen.getByLabelText(/number of tickets/i) as HTMLInputElement;
    fireEvent.change(ticketsInput, { target: { value: '3' } });
    expect(screen.getByText('Only 2 tickets available.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /book tickets/i })).toBeDisabled();

    fireEvent.change(ticketsInput, { target: { value: '2' } });
    expect(screen.queryByText('Only 2 tickets available.')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /book tickets/i })).not.toBeDisabled();
  });

  it('validates number of tickets client-side: must be greater than zero', async () => {
    renderComponent({ max_capacity: 10, active_tickets_count: 5 }); // 5 tickets available
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    const ticketsInput = screen.getByLabelText(/number of tickets/i) as HTMLInputElement;
    fireEvent.change(ticketsInput, { target: { value: '0' } });
    expect(screen.getByText('Number of tickets must be greater than zero.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /book tickets/i })).toBeDisabled();
  });

  it('handles successful booking and redirects for paid event', async () => {
    renderComponent({ max_capacity: 10, active_tickets_count: 5 }); // 5 tickets available
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    // Simulate a booking that requires payment
    const mockPaidBookingResponse = {
      id: 'bookingPaid123',
      status: 'pending_payment',
      total_price: '40.00'
      // other fields as needed by Booking type
    };
    mockBookingService.createBooking.mockResolvedValue(mockPaidBookingResponse as any);

    const ticketsInput = screen.getByLabelText(/number of tickets/i);
    fireEvent.change(ticketsInput, { target: { value: '2' } });

    const bookButton = screen.getByRole('button', { name: /book tickets/i });
    fireEvent.click(bookButton);

    expect(bookButton).toHaveTextContent('Processing...');
    await waitFor(() => expect(mockBookingService.createBooking).toHaveBeenCalledWith({
      event: mockEventBase.id,
      number_of_tickets: 2,
    }));
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith('/checkout/bookingPaid123'));
  });

  it('handles successful booking and redirects for free event', async () => {
    renderComponent({ ticket_price: '0.00', max_capacity: 10, active_tickets_count: 5 }); // Free event
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    // Simulate a booking that is confirmed (free event)
    const mockFreeBookingResponse = {
      id: 'bookingFree456',
      status: 'confirmed',
      total_price: '0.00'
      // other fields as needed
    };
    mockBookingService.createBooking.mockResolvedValue(mockFreeBookingResponse as any);

    // Mock window.alert
    const mockAlert = jest.spyOn(window, 'alert').mockImplementation(() => {});

    const ticketsInput = screen.getByLabelText(/number of tickets/i);
    fireEvent.change(ticketsInput, { target: { value: '1' } });

    const bookButton = screen.getByRole('button', { name: /book tickets/i });
    fireEvent.click(bookButton);

    expect(bookButton).toHaveTextContent('Processing...');
    await waitFor(() => expect(mockBookingService.createBooking).toHaveBeenCalledWith({
      event: mockEventBase.id,
      number_of_tickets: 1,
    }));
    await waitFor(() => expect(mockAlert).toHaveBeenCalledWith('Booking successful! This event requires no payment and is confirmed.'));
    await waitFor(() => expect(mockRouterPush).toHaveBeenCalledWith('/dashboard/my-bookings'));

    mockAlert.mockRestore(); // Clean up mock
  });

  it('displays backend validation error for capacity on booking attempt', async () => {
    renderComponent({ max_capacity: 10, active_tickets_count: 8 }); // 2 available
    await waitFor(() => screen.getByText('Test Event with Capacity'));

    mockBookingService.createBooking.mockRejectedValue({
      response: { data: { detail: "Not enough tickets available from backend." } }
    });

    const ticketsInput = screen.getByLabelText(/number of tickets/i);
    fireEvent.change(ticketsInput, { target: { value: '2' } }); // Client side validation passes

    const bookButton = screen.getByRole('button', { name: /book tickets/i });
    fireEvent.click(bookButton);

    await waitFor(() => {
      expect(screen.getByText("Not enough tickets available from backend.")).toBeInTheDocument();
    });
    expect(bookButton).not.toHaveTextContent('Processing...'); // Back to normal state
  });
});
