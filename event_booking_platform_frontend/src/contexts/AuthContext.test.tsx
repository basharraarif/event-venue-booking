import React from 'react';
import { render, act, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth, User } from './AuthContext'; // Assuming User type is exported
import authService from '@/services/authService';

// Mock authService
jest.mock('@/services/authService');
const mockedAuthService = authService as jest.Mocked<typeof authService>;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Test component to consume the context
const TestConsumerComponent = () => {
  const auth = useAuth();
  return (
    <div>
      <div data-testid="isLoading">{auth.isLoading.toString()}</div>
      <div data-testid="isAuthenticated">{auth.isAuthenticated.toString()}</div>
      <div data-testid="user">{JSON.stringify(auth.user)}</div>
      <div data-testid="token">{auth.token}</div>
      <div data-testid="isAdmin">{auth.hasRole('ADMIN').toString()}</div>
      <div data-testid="isCustomer">{auth.hasRole('CUSTOMER').toString()}</div>
      <button
        onClick={() =>
          auth.login('test-token', {
            id: '1',
            username: 'test',
            email: 'test@example.com',
            roles: ['CUSTOMER'],
          })
        }
      >
        Login
      </button>
      <button onClick={auth.logout}>Logout</button>
      <button onClick={() => auth.fetchAndUpdateUser()}>FetchUser</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorageMock.clear();
    jest.clearAllMocks();
  });

  it('initial state is loading, not authenticated, no user/token', () => {
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    expect(screen.getByTestId('isLoading').textContent).toBe('true'); // Initially true
    // After useEffect runs (even with no token)
    waitFor(() =>
      expect(screen.getByTestId('isLoading').textContent).toBe('false')
    );
    expect(screen.getByTestId('isAuthenticated').textContent).toBe('false');
    expect(screen.getByTestId('user').textContent).toBe('null');
    expect(screen.getByTestId('token').textContent).toBe(''); // null becomes empty string from state
  });

  it('login updates context and localStorage', () => {
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    const loginButton = screen.getByText('Login');
    act(() => {
      loginButton.click();
    });

    expect(screen.getByTestId('isAuthenticated').textContent).toBe('true');
    const user = JSON.parse(screen.getByTestId('user').textContent || '{}');
    expect(user.username).toBe('test');
    expect(user.roles).toEqual(['CUSTOMER']);
    expect(screen.getByTestId('token').textContent).toBe('test-token');
    expect(localStorageMock.getItem('authToken')).toBe('test-token');
    expect(
      JSON.parse(localStorageMock.getItem('authUser') || '{}').username
    ).toBe('test');
  });

  it('logout clears context and localStorage', () => {
    // First, login a user
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    const loginButton = screen.getByText('Login');
    act(() => {
      loginButton.click();
    });

    // Then, logout
    const logoutButton = screen.getByText('Logout');
    mockedAuthService.logout.mockResolvedValueOnce(undefined); // Mock backend logout
    act(() => {
      logoutButton.click();
    });

    expect(screen.getByTestId('isAuthenticated').textContent).toBe('false');
    expect(screen.getByTestId('user').textContent).toBe('null');
    expect(screen.getByTestId('token').textContent).toBe('');
    expect(localStorageMock.getItem('authToken')).toBeNull();
    expect(localStorageMock.getItem('authUser')).toBeNull();
    expect(mockedAuthService.logout).toHaveBeenCalledTimes(1);
  });

  it('hasRole works correctly', () => {
    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );
    const loginButton = screen.getByText('Login');
    // Login user with 'CUSTOMER' role
    act(() => {
      loginButton.click();
    });

    expect(screen.getByTestId('isCustomer').textContent).toBe('true');
    expect(screen.getByTestId('isAdmin').textContent).toBe('false');
  });

  it('fetchAndUpdateUser updates user from service and stores roles', async () => {
    const mockUserFromApi: User = {
      id: 'fetchedUser1',
      username: 'fetchedUser',
      email: 'fetched@example.com',
      roles: [{ name: 'ADMIN' }, { name: 'EVENT_ORGANIZER' }] as any, // Simulate backend role object structure
    };
    mockedAuthService.getCurrentUser.mockResolvedValue(mockUserFromApi);

    // Simulate having a token that fetchAndUpdateUser will use
    localStorageMock.setItem('authToken', 'valid-token-for-fetch');

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    // Wait for initial useEffect in AuthProvider to complete
    await waitFor(() =>
      expect(screen.getByTestId('isLoading').textContent).toBe('false')
    );

    // At this point, fetchAndUpdateUser was called by useEffect. Let's check its effect.
    await waitFor(() => {
      expect(mockedAuthService.getCurrentUser).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      const user = JSON.parse(screen.getByTestId('user').textContent || '{}');
      expect(user.username).toBe('fetchedUser');
      // The context processes roles into string array ['ADMIN', 'EVENT_ORGANIZER']
      expect(user.roles).toEqual(['ADMIN', 'EVENT_ORGANIZER']);
      expect(screen.getByTestId('isAuthenticated').textContent).toBe('true');
    });

    // Test hasRole after fetch
    expect(screen.getByTestId('isAdmin').textContent).toBe('true');
    expect(screen.getByTestId('isCustomer').textContent).toBe('false');
  });

  it('initial load from localStorage correctly sets state (including roles)', async () => {
    const storedUser: User = {
      id: 'stored1',
      username: 'storedUser',
      email: 'stored@example.com',
      roles: ['VENUE_MANAGER'],
    };
    localStorageMock.setItem('authToken', 'stored-token');
    localStorageMock.setItem('authUser', JSON.stringify(storedUser)); // AuthContext now relies on fetchUser on load

    // Mock getCurrentUser for the initial load sequence in AuthProvider
    mockedAuthService.getCurrentUser.mockResolvedValueOnce(storedUser);

    render(
      <AuthProvider>
        <TestConsumerComponent />
      </AuthProvider>
    );

    await waitFor(() =>
      expect(screen.getByTestId('isLoading').textContent).toBe('false')
    );

    await waitFor(() => {
      expect(screen.getByTestId('isAuthenticated').textContent).toBe('true');
      const user = JSON.parse(screen.getByTestId('user').textContent || '{}');
      expect(user.username).toBe('storedUser');
      expect(user.roles).toEqual(['VENUE_MANAGER']);
      expect(screen.getByTestId('token').textContent).toBe('stored-token');
    });
  });
});
