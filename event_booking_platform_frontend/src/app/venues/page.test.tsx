import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VenuesPage from './page'; // Path to the VenuesPage component
import { getVenues, Venue } from '@/services/venueService'; // Import the original service
import { AuthProvider } from '@/contexts/AuthContext'; // To wrap page if it uses useAuth

// Mock the venueService
jest.mock('@/services/venueService');
const mockGetVenues = getVenues as jest.MockedFunction<typeof getVenues>;

// Mock Next.js Link and other navigation components if not globally mocked in jest.setup.js
jest.mock('next/link', () => {
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

    expect(screen.getByText(/no venues found/i)).toBeInTheDocument();
  });

  it('has a link to "Add New Venue" page', async () => {
    mockGetVenues.mockResolvedValueOnce({ results: mockVenuesData, count: mockVenuesData.length, next: null, previous: null });
    renderWithAuthProvider(<VenuesPage />);
    await waitFor(() => expect(screen.queryByText(/loading venues.../i)).not.toBeInTheDocument());

    const addVenueLink = screen.getByRole('link', { name: /add new venue/i });
    expect(addVenueLink).toBeInTheDocument();
    expect(addVenueLink).toHaveAttribute('href', '/venues/new');
  });
});
