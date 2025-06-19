import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EventList from './EventList';
import eventService, { Event, Category } from '@/services/eventService';

// Mock eventService
jest.mock('@/services/eventService');
const mockGetEvents = eventService.getEvents as jest.MockedFunction<typeof eventService.getEvents>;
const mockGetCategories = eventService.getCategories as jest.MockedFunction<typeof eventService.getCategories>;

const mockCategories: Category[] = [
  { id: '1', name: 'Music' },
  { id: '2', name: 'Sports' },
  { id: '3', name: 'Tech' },
];

const mockEvents: Event[] = [
  { id: 'e1', name: 'Rock Concert', venue: 'v1', organizer: 'o1', categories: [{id: '1', name:'Music'}], start_time: '2024-08-01T19:00:00Z', end_time: '2024-08-01T22:00:00Z', status: 'upcoming', ticket_price: '50.00' },
  { id: 'e2', name: 'Football Match', venue: 'v2', organizer: 'o2', categories: [{id: '2', name:'Sports'}], start_time: '2024-08-05T15:00:00Z', end_time: '2024-08-05T17:00:00Z', status: 'upcoming', ticket_price: '30.00' },
  { id: 'e3', name: 'Tech Conference', venue: 'v3', organizer: 'o3', categories: [{id: '3', name:'Tech'}], start_time: '2024-09-10T09:00:00Z', end_time: '2024-09-12T17:00:00Z', status: 'upcoming', ticket_price: '200.00' },
  { id: 'e4', name: 'Jazz Night', venue: 'v1', organizer: 'o1', categories: [{id: '1', name:'Music'}], start_time: '2024-08-15T20:00:00Z', end_time: '2024-08-15T23:00:00Z', status: 'upcoming', ticket_price: '25.00' },
];

describe('EventList Integration Tests', () => {
  beforeEach(() => {
    // Reset mocks before each test
    mockGetEvents.mockReset();
    mockGetCategories.mockReset();

    // Default mock implementations
    mockGetCategories.mockResolvedValue(mockCategories);
    mockGetEvents.mockResolvedValue(mockEvents); // Initially return all events
  });

  test('renders initial events and categories, then filters by category', async () => {
    render(<EventList />);

    // Wait for initial data loading
    await waitFor(() => {
      expect(mockGetCategories).toHaveBeenCalledTimes(1);
      expect(mockGetEvents).toHaveBeenCalledTimes(1);
      expect(mockGetEvents).toHaveBeenCalledWith({}); // Initial call with no filters
    });

    // Check if all initial events are rendered
    expect(screen.getByText('Rock Concert')).toBeInTheDocument();
    expect(screen.getByText('Football Match')).toBeInTheDocument();
    expect(screen.getByText('Tech Conference')).toBeInTheDocument();
    expect(screen.getByText('Jazz Night')).toBeInTheDocument();

    // Check if category filter dropdown is present and populated
    const categorySelect = screen.getByLabelText('Category') as HTMLSelectElement;
    expect(categorySelect).toBeInTheDocument();
    expect(screen.getByText('All Categories')).toBeInTheDocument(); // Default option
    mockCategories.forEach(cat => {
      expect(screen.getByText(cat.name)).toBeInTheDocument();
    });

    // Simulate selecting "Music" category
    // Mock getEvents to return only music events when called with category filter
    const musicEvents = mockEvents.filter(event => event.categories.some(c => c.name === 'Music'));
    mockGetEvents.mockResolvedValueOnce(musicEvents); // For the next call after filter change

    fireEvent.change(categorySelect, { target: { value: 'Music' } });

    // Wait for the component to re-fetch and re-render
    // The useEffect in EventList triggers fetchEventsAndCategories on filterParams change
    await waitFor(() => {
      // Called once initially, then once for the filter change
      expect(mockGetEvents).toHaveBeenCalledTimes(2);
      expect(mockGetEvents).toHaveBeenCalledWith({ category_name: 'Music' });
    });

    // Check if only music events are displayed
    expect(screen.getByText('Rock Concert')).toBeInTheDocument();
    expect(screen.getByText('Jazz Night')).toBeInTheDocument();

    // Check that non-music events are NOT displayed
    expect(screen.queryByText('Football Match')).not.toBeInTheDocument();
    expect(screen.queryByText('Tech Conference')).not.toBeInTheDocument();
  });

  test('filters by event name (debounced)', async () => {
    jest.useFakeTimers(); // Use fake timers for debounce

    render(<EventList />);

    await waitFor(() => {
      expect(mockGetEvents).toHaveBeenCalledWith({}); // Initial load
    });

    const eventNameInput = screen.getByLabelText('Event Name') as HTMLInputElement;

    // Mock getEvents to return filtered events by name
    const rockConcertEvent = mockEvents.filter(event => event.name.includes('Rock Concert'));
    mockGetEvents.mockResolvedValueOnce(rockConcertEvent);

    fireEvent.change(eventNameInput, { target: { value: 'Rock Concert' } });

    // Fast-forward timers
    jest.advanceTimersByTime(700); // Advance past debounce time (700ms in component)

    await waitFor(() => {
      expect(mockGetEvents).toHaveBeenCalledTimes(2); // Initial + filter
      expect(mockGetEvents).toHaveBeenCalledWith({ name: 'Rock Concert' });
    });

    expect(screen.getByText('Rock Concert')).toBeInTheDocument();
    expect(screen.queryByText('Football Match')).not.toBeInTheDocument();

    jest.useRealTimers(); // Restore real timers
  });

  test('clears filters and re-fetches all events', async () => {
    // Initial load with a filter applied (e.g., from a previous state or direct call)
    mockGetEvents.mockResolvedValueOnce(mockEvents.filter(e => e.categories.some(c => c.name === 'Music')));
    render(<EventList />);

    await waitFor(() => {
      expect(mockGetEvents).toHaveBeenCalledTimes(1);
      // Initial call might be with a specific filter if state was restored,
      // or with {} if it's the first time. For this test, let's assume it started filtered.
      // This part is hard to test without deeper state manipulation or component props.
      // So, we'll focus on the clear action.
    });

    // Make sure music events are shown, others are not
    // (This relies on the mock above, might need adjustment if EventList always calls with {} first)
    // For simplicity, let's assume the component logic correctly applies initial filters if any.
    // The crucial part is testing the "Clear Filters" button's effect.

    // Now, set up the mock for when filters are cleared
    mockGetEvents.mockResolvedValueOnce(mockEvents); // Return all events

    const clearButton = screen.getByText('Clear Filters');
    fireEvent.click(clearButton);

    await waitFor(() => {
      // Should be called again: initial (potentially filtered), then with empty (cleared) filters
      expect(mockGetEvents).toHaveBeenCalledTimes(2);
      expect(mockGetEvents).toHaveBeenLastCalledWith({}); // Called with empty params after clear
    });

    // All events should be visible again
    expect(screen.getByText('Rock Concert')).toBeInTheDocument();
    expect(screen.getByText('Football Match')).toBeInTheDocument();
    expect(screen.getByText('Tech Conference')).toBeInTheDocument();
    expect(screen.getByText('Jazz Night')).toBeInTheDocument();
  });

  test('displays error message when fetching events fails', async () => {
    mockGetCategories.mockResolvedValue(mockCategories); // Categories load fine
    mockGetEvents.mockRejectedValueOnce(new Error('Failed to fetch events'));

    render(<EventList />);

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch events')).toBeInTheDocument();
    });
  });

  test('displays error message when fetching categories fails', async () => {
    mockGetCategories.mockRejectedValueOnce(new Error('Failed to fetch categories'));
    // getEvents might not even be called if categories fail first
    mockGetEvents.mockResolvedValue([]);

    render(<EventList />);

    await waitFor(() => {
      // The error message in EventList is generic for now
      expect(screen.getByText('Failed to fetch categories')).toBeInTheDocument();
    });
  });

  test('displays "no events match" message when filters result in empty list', async () => {
    mockGetCategories.mockResolvedValue(mockCategories);
    mockGetEvents.mockResolvedValueOnce(mockEvents); // Initial load

    render(<EventList />);
    await waitFor(() => expect(mockGetEvents).toHaveBeenCalledTimes(1));

    // Simulate selecting a filter that returns no events
    mockGetEvents.mockResolvedValueOnce([]); // Next call returns empty array

    const categorySelect = screen.getByLabelText('Category') as HTMLSelectElement;
    fireEvent.change(categorySelect, { target: { value: 'Sports' } }); // Assume "Sports" now has 0 events

    await waitFor(() => {
        expect(mockGetEvents).toHaveBeenCalledTimes(2);
        expect(mockGetEvents).toHaveBeenCalledWith({ category_name: 'Sports' });
    });

    expect(screen.getByText('No events match your current filters. Try adjusting them or clearing filters.')).toBeInTheDocument();
  });

});
