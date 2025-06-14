// jest.setup.js
import '@testing-library/jest-dom';
import React from 'react'; // Import React for the Link mock

// You can add other global setup configurations here if needed
// For example, mocking global objects or functions:
/*
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn() })),
  useParams: jest.fn(() => ({})),
  usePathname: jest.fn(() => ''),
  useSearchParams: jest.fn(() => ({ get: jest.fn() })),
}));
*/

// Mock localStorage if your components use it directly and it's not handled by jsdom environment
// (jsdom typically provides a basic localStorage implementation)
/*
const localStorageMock = (function() {
  let store = {};
  return {
    getItem: function(key) {
      return store[key] || null;
    },
    setItem: function(key, value) {
      store[key] = value.toString();
    },
    removeItem: function(key) {
      delete store[key];
    },
    clear: function() {
      store = {};
    }
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });
*/

// If you need to mock specific environment variables:
// process.env.NEXT_PUBLIC_API_BASE_URL = 'http://localhost:3000/api/mock';

// Mock next/link
jest.mock('next/link', () => {
  // eslint-disable-next-line react/display-name
  return ({children, href, ...rest}) => { // REMOVED ALL TYPE ANNOTATIONS
    return React.createElement('a', { href, ...rest }, children);
  };
});

// Mock axios
jest.mock('axios', () => ({
  ...jest.requireActual('axios'), // Preserve other axios methods if needed
  get: jest.fn(() => Promise.resolve({ data: {} })),
  post: jest.fn(() => Promise.resolve({ data: {} })),
  put: jest.fn(() => Promise.resolve({ data: {} })),
  delete: jest.fn(() => Promise.resolve({ data: {} })),
}));
