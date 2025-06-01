// src/services/__mocks__/authService.ts

export const login = jest.fn((credentials) => {
  if (credentials.email === 'test@example.com' && credentials.password === 'password') {
    return Promise.resolve({
      key: 'mock-auth-token',
      user: {
        pk: 1,
        id:1,
        username: 'testuser',
        email: 'test@example.com',
        // first_name: '', last_name: ''
      },
    });
  }
  return Promise.reject({ non_field_errors: ['Unable to log in with provided credentials.'] });
});

export const register = jest.fn((data) => {
  if (data.email === 'existing@example.com') {
    return Promise.reject({ email: ['Email already exists.'] });
  }
  // Simulate successful registration, backend might return user details or just success
  // For dj-rest-auth, it might return user details and a token if configured for immediate login
  return Promise.resolve({
    // Assuming registration doesn't auto-login or return a token by default in this mock
    // key: 'new-mock-auth-token',
    user: {
      pk: Date.now(),
      id: Date.now(),
      username: data.username,
      email: data.email,
    }
  });
});

export const logout = jest.fn(() => Promise.resolve());

export const getCurrentUser = jest.fn((token: string) => {
  if (token === 'mock-auth-token') {
    return Promise.resolve({
      pk: 1,
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      // first_name: '', last_name: ''
    });
  }
  return Promise.reject(new Error('Invalid token or user not found'));
});
