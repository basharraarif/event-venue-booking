import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import VenueList from './VenueList';
import * as venueService from '../../services/venueService';
import { Venue } from '../../services/venueService'; // Import Venue type

// Mock venueService
jest.mock('../../services/venueService');
const mockGetVenues = venueService.getVenues as jest.Mock;

// Mock useAuth hook
jest.mock('@/contexts/AuthContext');
import { useAuth } from '@/contexts/AuthContext'; // Import the actual hook
const mockUseAuth = useAuth as jest.Mock;

// Mock Next.js Link component
jest.mock('next/link', () => {
  return ({ children, href }: { children: React.ReactNode; href: string }) => {
    // Ensure children is a valid ReactNode. If it's an empty string or null, provide a default.
    // Or, more simply, just render children directly if they are always expected to be valid.
    return <a href={href}>{children || 'MockLink'}</a>;
  };
});

// Mock lodash.debounce to make it execute immediately
jest.mock('lodash', () => ({
  ...jest.requireActual('lodash'),
  debounce: (fn: (...args: any[]) => any) => fn,
}));

const mockVenues: Venue[] = [
  {
    id: 1,
    name: 'Test Venue 1',
    address: '123 Test St',
    capacity: 100,
    is_available: true,
    pricing_per_hour: '100.00',
    pricing_per_day: '800.00',
    description: 'A great venue',
    amenities: { wifi: true, parking: true },
    photos: [],
    owner: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 2,
    name: 'Test Venue 2',
    address: '456 Another Ave',
    capacity: 50,
    is_available: false,
    pricing_per_hour: '75.00',
    pricing_per_day: '600.00',
    description: 'Another great venue',
    amenities: { projector: true },
    photos: [],
    owner: 2,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];

describe('VenueList Component', () => {
  beforeEach(() => {
    mockGetVenues.mockClear();
    // Default mock implementation for most tests
    mockGetVenues.mockResolvedValue({
      results: [],
      next: null,
      previous: null,
    });
  });

  test('renders loading state initially and fetches venues with default params', async () => {
    render(<VenueList />);
    expect(screen.getByText(/loading venues.../i)).toBeInTheDocument();

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1));
    expect(mockGetVenues).toHaveBeenCalledWith(1, {
      search: '',
      capacity: '',
      availability: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
    });
  });

  test('displays venues correctly when API returns data', async () => {
    mockGetVenues.mockResolvedValueOnce({
      results: mockVenues,
      next: 'http://test.com/api/venues?page=2',
      previous: null,
    });
    render(<VenueList />);

    await waitFor(() => {
      expect(screen.getByText('Test Venue 1')).toBeInTheDocument();
      expect(screen.getByText('Test Venue 2')).toBeInTheDocument();
    });

    // Check for pagination info
    expect(screen.getByText('Page 1')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /next/i })).toBeEnabled();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
  });

  test('shows error message if getVenues fails', async () => {
    mockGetVenues.mockRejectedValueOnce(new Error('API Error'));
    render(<VenueList />);

    await waitFor(() => {
      expect(screen.getByText(/failed to fetch venues/i)).toBeInTheDocument();
    });
  });

  test('shows "no venues found" message if API returns empty list', async () => {
    mockGetVenues.mockResolvedValueOnce({
      results: [],
      next: null,
      previous: null,
    });
    render(<VenueList />);

    // Initial loading
    expect(screen.getByText(/loading venues.../i)).toBeInTheDocument();

    await waitFor(() => {
      // After loading, the "no venues" message should appear
      // The exact text might vary based on your component's implementation
      expect(
        screen.getByText(/no venues match your criteria or none available/i)
      ).toBeInTheDocument();
    });
  });

  test('calls getVenues with search filter and resets to page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1)); // Initial fetch

    const searchInput = screen.getByLabelText(/search/i);
    await userEvent.type(searchInput, 'Test Search');

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2)); // Debounced fetch
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      search: 'Test Search',
      capacity: '',
      availability: '',
      minPrice: '',
      maxPrice: '',
    });
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  test('calls getVenues with capacity filter and resets to page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1));

    const capacityInput = screen.getByLabelText(/min. capacity/i);
    await userEvent.type(capacityInput, '100');

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2));
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      search: '',
      capacity: '100',
      availability: '',
      minPrice: '',
      maxPrice: '',
    });
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  test('calls getVenues with availability filter and resets to page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1));

    const availabilitySelect = screen.getByLabelText(/availability/i);
    await userEvent.selectOptions(availabilitySelect, 'true');

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2));
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      search: '',
      capacity: '',
      availability: 'true',
      minPrice: '',
      maxPrice: '',
    });
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  test('calls getVenues with min and max price filters and resets to page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1));

    const minPriceInput = screen.getByLabelText(/min. price/i);
    const maxPriceInput = screen.getByLabelText(/max. price/i);

    await userEvent.type(minPriceInput, '50');
    // Since debounce is immediate, this will be one call
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2));
    expect(mockGetVenues).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({ minPrice: '50' })
    );

    await userEvent.type(maxPriceInput, '200');
    // And this another
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(3));
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      search: '',
      capacity: '',
      availability: '',
      minPricePerHour: '50',
      maxPricePerHour: '200',
      minPricePerDay: '',
      maxPricePerDay: '',
    });
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  test('pagination: clicking Next calls getVenues with incremented page', async () => {
    mockGetVenues.mockResolvedValueOnce({
      results: mockVenues, // Needs some results to enable next
      next: 'http://test.com/api/venues?page=2',
      previous: null,
    });
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1)); // Initial

    const nextButton = screen.getByRole('button', { name: /next/i });
    expect(nextButton).toBeEnabled();
    await userEvent.click(nextButton);

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2));
    expect(mockGetVenues).toHaveBeenLastCalledWith(2, {
      // Page 2
      search: '',
      capacity: '',
      availability: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
    });
    // Assuming the component updates to show "Page 2"
    // This requires the mock to return appropriate next/prev for page 2 as well if we want to test further
    // For now, just checking the call is enough.
  });

  test('pagination: clicking Previous calls getVenues with decremented page', async () => {
    // Setup for page 2 initially
    mockGetVenues.mockResolvedValueOnce({
      results: mockVenues,
      next: 'http://test.com/api/venues?page=3',
      previous: 'http://test.com/api/venues?page=1',
    });

    // To get to a state where "Previous" is clickable, we need to simulate being on page > 1
    // We can't directly set the page state, so we'll "click" next first.
    // 1. Initial render (page 1, but we'll provide data as if it's page 2 to enable previous)

    render(<VenueList />); // Renders page 1 initially

    // Simulate being on page 2 by clicking next, then test previous
    // First call for initial load (page 1)
    await waitFor(() =>
      expect(mockGetVenues).toHaveBeenCalledWith(1, expect.anything())
    );

    // Provide response for page 1 that allows going to page 2
    mockGetVenues.mockResolvedValueOnce({
      results: mockVenues,
      next: 'http://test.com/api/venues?page=2',
      previous: null,
    });
    // (This is tricky as the component state for `page` is internal)
    // Let's assume the component is already on page 2 for this specific test of "Previous"
    // We can achieve this by manipulating the component or providing a more complex initial state if the component allowed it.
    // Given the current structure, let's test the state after a "Next" click.

    // Initial render, page 1
    const nextButton = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextButton); // Go to page 2

    // API call for page 2
    await waitFor(() =>
      expect(mockGetVenues).toHaveBeenCalledWith(2, expect.anything())
    );

    // Now, assume API for page 2 returns data that enables "Previous"
    mockGetVenues.mockResolvedValueOnce({
      results: mockVenues,
      next: 'http://test.com/api/venues?page=3',
      previous: 'http://test.com/api/venues?page=1',
    });
    // The component re-renders with page 2 data, "Previous" should be enabled
    // Wait for UI to update (e.g. Page 2 text)
    await screen.findByText('Page 2'); // Make sure we are on page 2

    const prevButton = screen.getByRole('button', { name: /previous/i });
    expect(prevButton).toBeEnabled();
    await userEvent.click(prevButton);

    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(3)); // Initial, Next, Previous
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      // Back to page 1
      search: '',
      capacity: '',
      availability: '',
      minPrice: '',
      maxPrice: '',
    });
  });

  describe('"Create New Venue" Link/Button Visibility', () => {
    const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
    const ROLE_CUSTOMER = 'CUSTOMER';

    it('shows "Create New Venue" link for Venue Manager', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: { id: 'vm1', roles: [ROLE_VENUE_MANAGER] },
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
        isLoading: false,
      });
      render(<VenueList />);
      // Check both potential locations for the button
      const createLinks = screen.queryAllByText(/create new venue/i);
      expect(createLinks.length).toBeGreaterThan(0); // Could be 1 or 2
      createLinks.forEach((link) => {
        expect(link.closest('a')).toHaveAttribute('href', '/venues/create');
      });
    });

    it('does not show "Create New Venue" link for Customer', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: true,
        user: { id: 'cust1', roles: [ROLE_CUSTOMER] },
        hasRole: (role: string) => role === ROLE_CUSTOMER,
        isLoading: false,
      });
      render(<VenueList />);
      expect(screen.queryByText(/create new venue/i)).not.toBeInTheDocument();
    });

    it('does not show "Create New Venue" link for unauthenticated user', () => {
      mockUseAuth.mockReturnValue({
        isAuthenticated: false,
        user: null,
        hasRole: () => false,
        isLoading: false,
      });
      render(<VenueList />);
      expect(screen.queryByText(/create new venue/i)).not.toBeInTheDocument();
    });
  });

  test('calls getVenues with price per day filters and resets to page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1)); // Initial fetch

    const minPriceDayInput = screen.getByLabelText(/min. price \(\$\/day\)/i);
    await userEvent.type(minPriceDayInput, '300');
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2));
    expect(mockGetVenues).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({ minPricePerDay: '300' })
    );

    const maxPriceDayInput = screen.getByLabelText(/max. price \(\$\/day\)/i);
    await userEvent.type(maxPriceDayInput, '1000');
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(3));
    expect(mockGetVenues).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({
        minPricePerDay: '300',
        maxPricePerDay: '1000',
      })
    );
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  test('clear filters button resets all filters and fetches with default params on page 1', async () => {
    render(<VenueList />);
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(1)); // Initial fetch

    // Apply some filters
    const searchInput = screen.getByLabelText(/search/i);
    await userEvent.type(searchInput, 'Test Search');
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(2)); // Debounced fetch for search

    const capacityInput = screen.getByLabelText(/min. capacity/i);
    await userEvent.type(capacityInput, '100');
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(3)); // Debounced fetch for capacity

    // Check if filters were applied
    expect(mockGetVenues).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({
        search: 'Test Search',
        capacity: '100',
      })
    );

    // Click clear filters
    const clearButton = screen.getByRole('button', { name: /clear filters/i });
    await userEvent.click(clearButton);

    // Should fetch again with initial (empty) filters and on page 1
    await waitFor(() => expect(mockGetVenues).toHaveBeenCalledTimes(4));
    expect(mockGetVenues).toHaveBeenLastCalledWith(1, {
      search: '',
      capacity: '',
      availability: '',
      minPricePerHour: '',
      maxPricePerHour: '',
      minPricePerDay: '',
      maxPricePerDay: '',
    });
    expect(screen.getByText('Page 1')).toBeInTheDocument(); // Stays on page 1 or resets to it
  });
});
