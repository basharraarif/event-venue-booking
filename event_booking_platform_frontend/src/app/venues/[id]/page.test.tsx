import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import VenueDetailPage from './page';
import { getVenueById, deleteVenue, Venue } from '@/services/venueService';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useParams } from 'next/navigation'; // Corrected import for useParams

// Mock services and navigation
jest.mock('@/services/venueService');
const mockGetVenueById = getVenueById as jest.MockedFunction<
  typeof getVenueById
>;
const mockDeleteVenue = deleteVenue as jest.MockedFunction<typeof deleteVenue>;

const mockRouterPush = jest.fn();
const mockRouterBack = jest.fn();
let mockParams = { id: 'venue1' }; // Default mock params

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: mockRouterPush, back: mockRouterBack })),
  useParams: jest.fn(() => mockParams),
  usePathname: jest.fn(() => '/venues/venue1'),
}));

// Mock AuthContext
jest.mock('@/contexts/AuthContext');
const mockUseAuth = useAuth as jest.Mock;

// Mock common components
jest.mock(
  '@/components/common/LoadingSpinner',
  () =>
    ({ message }: { message: string }) => (
      <div data-testid="loading-spinner">{message}</div>
    )
);
jest.mock(
  '@/components/common/AlertMessage',
  () =>
    ({ message, type }: { message: string; type: string }) => (
      <div data-testid="alert-message" data-type={type}>
        {message}
      </div>
    )
);

const ROLE_VENUE_MANAGER = 'VENUE_MANAGER';
const ROLE_CUSTOMER = 'CUSTOMER';

const mockVenueData: Venue = {
  id: 'venue1',
  name: 'Beautiful Hall',
  address: '123 Main St, Anytown',
  capacity: 150,
  amenities: ['WiFi', 'Projector'],
  contact_email: 'contact@beautifulhall.com',
  contact_phone: '555-1234',
  website: 'http://beautifulhall.com',
  description: 'A beautiful hall for all your event needs.',
  is_available: true,
  owner: { id: 'owner123', username: 'venueOwner' } as any, // Ensure owner has an id
  owner_username: 'venueOwner',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

// Helper to render with specific AuthContext values
const renderPage = (
  authContextValue: Partial<ReturnType<typeof useAuth>>,
  venueIdParam = 'venue1'
) => {
  mockUseAuth.mockReturnValue({
    isAuthenticated: false,
    user: null,
    isLoading: false,
    hasRole: jest.fn().mockReturnValue(false),
    login: jest.fn(),
    logout: jest.fn(),
    fetchAndUpdateUser: jest.fn().mockResolvedValue(undefined),
    token: null,
    ...authContextValue,
  });
  mockParams = { id: venueIdParam }; // Update mockParams for useParams()
  return render(<VenueDetailPage />);
};

describe('VenueDetailPage', () => {
  const venueManagerOwner = {
    id: 'owner123',
    username: 'venueOwner',
    roles: [ROLE_VENUE_MANAGER],
  };
  const venueManagerNonOwner = {
    id: 'otherVM',
    username: 'otherVM',
    roles: [ROLE_VENUE_MANAGER],
  };
  const customerUser = {
    id: 'customer1',
    username: 'customer',
    roles: [ROLE_CUSTOMER],
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockGetVenueById.mockResolvedValue(mockVenueData); // Default successful fetch
    mockDeleteVenue.mockResolvedValue({}); // Default successful delete
  });

  it('renders loading state initially', () => {
    renderPage({ isLoading: true });
    expect(screen.getByTestId('loading-spinner')).toHaveTextContent(
      'Loading venue details...'
    );
  });

  it('shows error if venueId is missing (though useParams mock usually provides it)', () => {
    renderPage({}, ''); // Pass empty string for venueIdParam
    expect(screen.getByTestId('alert-message')).toHaveTextContent(
      'Venue ID is missing.'
    );
  });

  it('fetches and displays venue details', async () => {
    renderPage({
      isAuthenticated: true,
      user: customerUser as any,
      hasRole: (r: string) => customerUser.roles.includes(r),
    });
    await waitFor(() =>
      expect(mockGetVenueById).toHaveBeenCalledWith('venue1')
    );
    expect(
      screen.getByRole('heading', { name: mockVenueData.name })
    ).toBeInTheDocument();
    expect(screen.getByText(mockVenueData.address)).toBeInTheDocument();
    expect(
      screen.getByText(`Capacity: ${mockVenueData.capacity}`)
    ).toBeInTheDocument();
  });

  it('shows error if fetching venue details fails', async () => {
    mockGetVenueById.mockRejectedValueOnce(new Error('Failed to fetch'));
    renderPage({
      isAuthenticated: true,
      user: customerUser as any,
      hasRole: (r: string) => customerUser.roles.includes(r),
    });
    await waitFor(() =>
      expect(screen.getByTestId('alert-message')).toHaveTextContent(
        'Failed to load venue details.'
      )
    );
  });

  describe('Edit and Delete Buttons Visibility', () => {
    it('shows Edit and Delete buttons for Venue Manager who owns the venue', async () => {
      renderPage({
        isAuthenticated: true,
        user: venueManagerOwner as any,
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('heading', { name: mockVenueData.name })
        ).toBeInTheDocument()
      ); // Wait for venue data
      expect(
        screen.getByRole('link', { name: /edit venue/i })
      ).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /delete venue/i })
      ).toBeInTheDocument();
    });

    it('does not show Edit and Delete buttons for Venue Manager who does not own the venue', async () => {
      renderPage({
        isAuthenticated: true,
        user: venueManagerNonOwner as any,
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('heading', { name: mockVenueData.name })
        ).toBeInTheDocument()
      );
      expect(
        screen.queryByRole('link', { name: /edit venue/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /delete venue/i })
      ).not.toBeInTheDocument();
    });

    it('does not show Edit and Delete buttons for Customer user', async () => {
      renderPage({
        isAuthenticated: true,
        user: customerUser as any,
        hasRole: (role: string) => role === ROLE_CUSTOMER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('heading', { name: mockVenueData.name })
        ).toBeInTheDocument()
      );
      expect(
        screen.queryByRole('link', { name: /edit venue/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /delete venue/i })
      ).not.toBeInTheDocument();
    });

    it('does not show Edit and Delete buttons for unauthenticated user', async () => {
      renderPage({ isAuthenticated: false });
      await waitFor(() =>
        expect(
          screen.getByRole('heading', { name: mockVenueData.name })
        ).toBeInTheDocument()
      );
      expect(
        screen.queryByRole('link', { name: /edit venue/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole('button', { name: /delete venue/i })
      ).not.toBeInTheDocument();
    });
  });

  describe('Delete Venue Functionality', () => {
    beforeEach(() => {
      // Mock window.confirm
      window.confirm = jest.fn(() => true); // Assume user always confirms deletion
    });

    it('calls deleteVenue service and redirects on successful deletion by owner', async () => {
      renderPage({
        isAuthenticated: true,
        user: venueManagerOwner as any,
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: /delete venue/i })
        ).toBeInTheDocument()
      );

      fireEvent.click(screen.getByRole('button', { name: /delete venue/i }));

      expect(window.confirm).toHaveBeenCalledWith(
        `Are you sure you want to delete venue "${mockVenueData.name}"? This action cannot be undone.`
      );

      await waitFor(() =>
        expect(mockDeleteVenue).toHaveBeenCalledWith(mockVenueData.id)
      );
      // Check for alert message (assuming alert is used for success)
      // await waitFor(() => expect(window.alert).toHaveBeenCalledWith("Venue deleted successfully.")); // The component uses setError/setSuccessMessage now
      await waitFor(() =>
        expect(mockRouterPush).toHaveBeenCalledWith('/venues')
      );
    });

    it('shows error message if deleteVenue service fails', async () => {
      mockDeleteVenue.mockRejectedValueOnce(new Error('Deletion failed'));
      renderPage({
        isAuthenticated: true,
        user: venueManagerOwner as any,
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: /delete venue/i })
        ).toBeInTheDocument()
      );

      fireEvent.click(screen.getByRole('button', { name: /delete venue/i }));

      await waitFor(() => {
        expect(screen.getByTestId('alert-message')).toHaveTextContent(
          /Failed to delete venue: Deletion failed/i
        );
      });
      expect(mockRouterPush).not.toHaveBeenCalled();
    });

    it('does not call deleteVenue if user cancels confirmation', async () => {
      window.confirm = jest.fn(() => false); // User clicks "Cancel"
      renderPage({
        isAuthenticated: true,
        user: venueManagerOwner as any,
        hasRole: (role: string) => role === ROLE_VENUE_MANAGER,
      });
      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: /delete venue/i })
        ).toBeInTheDocument()
      );

      fireEvent.click(screen.getByRole('button', { name: /delete venue/i }));

      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteVenue).not.toHaveBeenCalled();
    });
  });
});
