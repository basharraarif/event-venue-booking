import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import VenuesPage from './page'; // Path to the VenuesPage component
import { getVenues, Venue } from '@/services/venueService'; // Import the original service
import { AuthProvider } from '@/contexts/AuthContext'; // To wrap page if it uses useAuth

// Mock the venueService
jest.mock('@/services/venueService');
const mockGetVenues = getVenues as jest.MockedFunction<typeof getVenues>;

// Mock Next.js Link and other navigation components if not globally mocked in jest.setup.js
jest.mock('next/link', () => {
    // eslint-disable-next-line react/display-name
    return ({ children, href }) => <a href={href}>{children}</a>;
});
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn() })),
  useParams: jest.fn(() => ({})),
  usePathname: jest.fn(() => '/venues'), // Mock current pathname
}));


const mockVenuesData: Venue[] = [
  { id: 1, name: 'Venue Alpha', address: '1 Alpha St', capacity: 100, amenities: [], pricing_per_hour: '50', pricing_per_day: '500', is_available: true, created_at: '', updated_at: '' },
  { id: 2, name: 'Venue Beta', address: '2 Beta Rd', capacity: 200, amenities: [], pricing_per_hour: '70', pricing_per_day: '700', is_available: false, created_at: '', updated_at: '' },
];

// Helper to render with AuthProvider, as VenuesPage might indirectly use useAuth via other components or future enhancements
const renderWithAuthProvider = (ui: React.ReactElement) => {
  return render(
    <AuthProvider>
      {ui}
    </AuthProvider>
  );
};


describe('VenuesPage Component', () => {
  beforeEach(() => {
    mockGetVenues.mockClear();
  });

  it('displays loading state initially', () => {
    mockGetVenues.mockReturnValue(new Promise(() => {})); // Keep promise pending
    renderWithAuthProvider(<VenuesPage />);
    expect(screen.getByText(/loading venues.../i)).toBeInTheDocument();
  });

  it('fetches and displays venues successfully', async () => {
    mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
    renderWithAuthProvider(<VenuesPage />);

    // Wait for loading to disappear and venues to appear
    await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

    expect(screen.getByText('Venue Alpha')).toBeInTheDocument();
    expect(screen.getByText('Venue Beta')).toBeInTheDocument();
    expect(screen.getByText(/add new venue/i)).toBeInTheDocument(); // Check for the link
  });

  it('displays an error message when fetching venues fails', async () => {
    mockGetVenues.mockRejectedValueOnce(new Error('Failed to fetch venues'));
    renderWithAuthProvider(<VenuesPage />);

    await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

    expect(screen.getByText(/error loading venues:/i)).toBeInTheDocument();
    expect(screen.getByText('Failed to fetch venues')).toBeInTheDocument();
  });

  it('displays "No venues found" when no venues are returned', async () => {
    mockGetVenues.mockResolvedValueOnce({ results: [], count: 0, next: null, previous: null });
    renderWithAuthProvider(<VenuesPage />);

    await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

    expect(screen.getByText(/no venues found matching your criteria./i)).toBeInTheDocument(); // Updated text
  });

  it('has a link to "Add New Venue" page', async () => {
    mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
    renderWithAuthProvider(<VenuesPage />);
    await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

    const addVenueLink = screen.getByRole('link', { name: /add new venue/i });
    expect(addVenueLink).toBeInTheDocument();
    expect(addVenueLink).toHaveAttribute('href', '/venues/new');
  });

  describe('Filtering Functionality', () => {
    beforeEach(() => {
      // Ensure initial load for each filtering test
      mockGetVenues.mockResolvedValue({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
    });

    it('renders all filter UI elements', async () => {
      renderWithAuthProvider(<VenuesPage />);
      await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

      expect(screen.getByLabelText(/search/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/availability/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/min. capacity/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/min. price\/hour/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/max. price\/hour/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /apply filters/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /clear filters/i })).toBeInTheDocument();
    });

    it('updates input fields on user interaction', async () => {
      renderWithAuthProvider(<VenuesPage />);
      await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

      const searchInput = screen.getByLabelText(/search/i) as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: 'Test Search' } });
      expect(searchInput.value).toBe('Test Search');

      const capacityInput = screen.getByLabelText(/min. capacity/i) as HTMLInputElement;
      fireEvent.change(capacityInput, { target: { value: '150' } });
      expect(capacityInput.value).toBe('150');

      const availabilitySelect = screen.getByLabelText(/availability/i) as HTMLSelectElement;
      fireEvent.change(availabilitySelect, { target: { value: 'true' } });
      expect(availabilitySelect.value).toBe('true');

      const minPriceInput = screen.getByLabelText(/min. price\/hour/i) as HTMLInputElement;
      fireEvent.change(minPriceInput, { target: { value: '30' } });
      expect(minPriceInput.value).toBe('30');

      const maxPriceInput = screen.getByLabelText(/max. price\/hour/i) as HTMLInputElement;
      fireEvent.change(maxPriceInput, { target: { value: '90' } });
      expect(maxPriceInput.value).toBe('90');
    });

    it('fetches venues with correct parameters when "Apply Filters" is clicked', async () => {
      // Initial load with all venues
      mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
      renderWithAuthProvider(<VenuesPage />);
      await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

      // Mock response for filtered data
      const filteredVenue = { ...mockVenuesData[0], name: 'Filtered Alpha' };
      mockGetVenues.mockResolvedValueOnce({ results: [filteredVenue], count: 1, next: null, previous: null });

      fireEvent.change(screen.getByLabelText(/search/i), { target: { value: 'Alpha' } });
      fireEvent.change(screen.getByLabelText(/min. capacity/i), { target: { value: '50' } });
      fireEvent.change(screen.getByLabelText(/availability/i), { target: { value: 'true' } });
      fireEvent.change(screen.getByLabelText(/min. price\/hour/i), { target: { value: '40' } });
      fireEvent.change(screen.getByLabelText(/max. price\/hour/i), { target: { value: '60' } });

      fireEvent.click(screen.getByRole('button', { name: /apply filters/i }));

      await waitFor(() => {
        expect(mockGetVenues).toHaveBeenLastCalledWith({
          search: 'Alpha',
          capacity: 50,
          is_available: true,
          min_price_per_hour: 40,
          max_price_per_hour: 60,
        });
      });

      await waitFor(() => {
        expect(screen.getByText('Filtered Alpha')).toBeInTheDocument(); // Displays filtered venue
        expect(screen.queryByText('Venue Beta')).not.toBeInTheDocument(); // Original Venue Beta should be filtered out
      });
    });

    it('does not send empty or default filter values in params', async () => {
      mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
      renderWithAuthProvider(<VenuesPage />);
      await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

      mockGetVenues.mockResolvedValueOnce({ results: [mockVenuesData[0]], count: 1, next: null, previous: null });

      fireEvent.change(screen.getByLabelText(/search/i), { target: { value: 'Specific' } });
      // Capacity, availability, min/max price are left empty/default

      fireEvent.click(screen.getByRole('button', { name: /apply filters/i }));

      await waitFor(() => {
        expect(mockGetVenues).toHaveBeenLastCalledWith({
          search: 'Specific',
          // Other params should be absent
        });
      });
       // Ensure only the search param was sent
      const lastCallArgs = mockGetVenues.mock.lastCall[0];
      expect(lastCallArgs).not.toHaveProperty('capacity');
      expect(lastCallArgs).not.toHaveProperty('is_available');
      expect(lastCallArgs).not.toHaveProperty('min_price_per_hour');
      expect(lastCallArgs).not.toHaveProperty('max_price_per_hour');
    });


    it('clears filters and fetches all venues when "Clear Filters" is clicked', async () => {
      // Initial load
      mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
      renderWithAuthProvider(<VenuesPage />);
      await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

      // Apply some filters first
      fireEvent.change(screen.getByLabelText(/search/i), { target: { value: 'Alpha' } });
      fireEvent.change(screen.getByLabelText(/min. capacity/i), { target: { value: '100' } });
      fireEvent.change(screen.getByLabelText(/availability/i), { target: { value: 'true' } });

      // Mock response for filtered data
      const filteredVenue = { ...mockVenuesData[0], name: 'Filtered Alpha Only' };
      mockGetVenues.mockResolvedValueOnce({ results: [filteredVenue], count: 1, next: null, previous: null });
      fireEvent.click(screen.getByRole('button', { name: /apply filters/i }));

      await waitFor(() => expect(screen.getByText('Filtered Alpha Only')).toBeInTheDocument());
      expect(mockGetVenues).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'Alpha', capacity: 100, is_available: true }));


      // Mock response for clearing filters (back to all venues)
      // Use different names to ensure UI is re-rendering with new data
      const refreshedMockVenues = [
        { ...mockVenuesData[0], name: "Refreshed Alpha" },
        { ...mockVenuesData[1], name: "Refreshed Beta" },
      ];
      mockGetVenues.mockResolvedValueOnce({ results: refreshedMockVenues, count: refreshedMockVenues.length, next: null, previous: null });

      fireEvent.click(screen.getByRole('button', { name: /clear filters/i }));

      // Check if getVenues was called without parameters (or with an empty object)
      await waitFor(() => expect(mockGetVenues).toHaveBeenLastCalledWith()); // Called with no args for all venues

      // Check if input fields are reset
      expect((screen.getByLabelText(/search/i) as HTMLInputElement).value).toBe('');
      expect((screen.getByLabelText(/min. capacity/i) as HTMLInputElement).value).toBe('');
      expect((screen.getByLabelText(/availability/i) as HTMLSelectElement).value).toBe('');
      expect((screen.getByLabelText(/min. price\/hour/i) as HTMLInputElement).value).toBe('');
      expect((screen.getByLabelText(/max. price\/hour/i) as HTMLInputElement).value).toBe('');

      // Check if UI updates with all venues
      await waitFor(() => {
        expect(screen.getByText('Refreshed Alpha')).toBeInTheDocument();
        expect(screen.getByText('Refreshed Beta')).toBeInTheDocument();
        expect(screen.queryByText('Filtered Alpha Only')).not.toBeInTheDocument();
      });
    });
  });
});
