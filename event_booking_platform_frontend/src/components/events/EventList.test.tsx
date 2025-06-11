import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EventList from './EventList';
import * as eventService from '../../services/eventService'; // Import all as eventService
import { Event, Category } from '../../services/eventService'; // Import types

// Mock eventService
jest.mock('../../services/eventService');
const mockGetEvents = eventService.default.getEvents as jest.Mock;
const mockGetCategories = eventService.default.getCategories as jest.Mock;

// Mock lodash.debounce
jest.mock('lodash', () => ({
  ...jest.requireActual('lodash'),
  debounce: (fn: (...args: any[]) => any) => fn,
}));

const mockEvents: Event[] = [
  { id: 'evt1', name: 'Tech Conference 2024', description: 'Annual tech conf', venue: 'venue1', venue_name: 'Main Hall', organizer: 'user1', categories: ['Technology'], start_time: new Date(Date.now() + 86400000 * 5).toISOString(), end_time: new Date(Date.now() + 86400000 * 5 + 7200000).toISOString(), status: 'upcoming', ticket_price: '100.00' },
  { id: 'evt2', name: 'Music Fest', description: 'Outdoor music festival', venue: 'venue2', venue_name: 'Open Ground', organizer: 'user2', categories: ['Music', 'Festival'], start_time: new Date(Date.now() + 86400000 * 10).toISOString(), end_time: new Date(Date.now() + 86400000 * 11).toISOString(), status: 'upcoming', ticket_price: '75.00' },
];

const mockCategories: Category[] = [
  { id: 'cat1', name: 'Technology' },
  { id: 'cat2', name: 'Music' },
  { id: 'cat3', name: 'Festival' },
];

describe('EventList Component', () => {
  beforeEach(() => {
    mockGetEvents.mockClear();
    mockGetCategories.mockClear();
    mockGetCategories.mockResolvedValue(mockCategories); // Default mock for categories
    mockGetEvents.mockResolvedValue(mockEvents); // Default mock for events
  });

  test('renders loading state initially and fetches events and categories', async () => {
    render(<EventList />);
    expect(screen.getByText(/loading events.../i)).toBeInTheDocument();

    await waitFor(() => {
      expect(mockGetCategories).toHaveBeenCalledTimes(1);
      expect(mockGetEvents).toHaveBeenCalledTimes(1);
    });
    // Initial call with empty filters
    expect(mockGetEvents).toHaveBeenCalledWith({});
  });

  test('displays events correctly when API returns data', async () => {
    render(<EventList />);
    await waitFor(() => {
      expect(screen.getByText('Tech Conference 2024')).toBeInTheDocument();
      expect(screen.getByText('Music Fest')).toBeInTheDocument();
    });
  });

  test('shows error message if getEvents fails', async () => {
    mockGetEvents.mockRejectedValueOnce(new Error('API Error for Events'));
    render(<EventList />);
    await waitFor(() => {
      expect(screen.getByText(/Error: API Error for Events/i)).toBeInTheDocument();
    });
  });

  test('shows error message if getCategories fails', async () => {
    mockGetCategories.mockRejectedValueOnce(new Error('API Error for Categories'));
    mockGetEvents.mockResolvedValueOnce([]); // Prevent further errors
    render(<EventList />);
    await waitFor(() => {
      // Error from getCategories might be caught and logged, but the main error displayed might be from getEvents failing or no events
      // Depending on implementation, the component might still try to render with empty categories
      // Let's assume a general error message if data loading fails.
      expect(screen.getByText(/Error: API Error for Categories/i)).toBeInTheDocument();
    });
  });


  test('shows "no events found" message if API returns empty list', async () => {
    mockGetEvents.mockResolvedValueOnce([]);
    render(<EventList />);
    await waitFor(() => {
      expect(screen.getByText(/no events match your current filters/i)).toBeInTheDocument();
    });
  });

  test('calls getEvents with name filter', async () => {
    render(<EventList />);
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(1)); // Initial

    const nameInput = screen.getByLabelText(/event name/i);
    await userEvent.type(nameInput, 'Tech');

    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(2)); // Debounced
    expect(mockGetEvents).toHaveBeenLastCalledWith({ name: 'Tech' });
  });

  test('calls getEvents with category filter', async () => {
    render(<EventList />);
    await waitFor(() => expect(mockGetCategories).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(1));


    const categorySelect = screen.getByLabelText(/category/i);
    await userEvent.selectOptions(categorySelect, 'Technology');

    // No debounce for select, so should be called again
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(2));
    expect(mockGetEvents).toHaveBeenLastCalledWith({ category_name: 'Technology' });
  });

  test('calls getEvents with status filter', async () => {
    render(<EventList />);
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(1));

    const statusSelect = screen.getByLabelText(/status/i);
    await userEvent.selectOptions(statusSelect, 'upcoming');

    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(2));
    expect(mockGetEvents).toHaveBeenLastCalledWith({ status: 'upcoming' });
  });

  test('clear filters button resets filters and fetches with default params', async () => {
    render(<EventList />);
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(1)); // Initial

    const nameInput = screen.getByLabelText(/event name/i);
    await userEvent.type(nameInput, 'Search Term');
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(2)); // Debounced
    expect(mockGetEvents).toHaveBeenLastCalledWith({ name: 'Search Term' });

    const clearButton = screen.getByRole('button', { name: /clear filters/i });
    await userEvent.click(clearButton);

    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(3));
    expect(mockGetEvents).toHaveBeenLastCalledWith({}); // Empty filters
  });

});
