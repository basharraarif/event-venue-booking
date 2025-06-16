// src/components/common/ErrorBoundary.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from './ErrorBoundary';
import '@testing-library/jest-dom';

// Mock console.error to prevent error logs during tests
let consoleErrorMock: jest.SpyInstance;

beforeEach(() => {
  consoleErrorMock = jest.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
  consoleErrorMock.mockRestore();
});

const ProblemChild = ({ shouldThrow }: { shouldThrow?: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error from ProblemChild');
  }
  return <div>Child component rendered successfully</div>;
};

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>
    );
    expect(screen.getByText('Child component rendered successfully')).toBeInTheDocument();
  });

  it('renders fallback UI when a child component throws an error', () => {
    render(
      <ErrorBoundary fallbackMessage="Custom fallback message.">
        <ProblemChild shouldThrow />
      </ErrorBoundary>
    );
    expect(screen.getByText('Custom fallback message.')).toBeInTheDocument();
    expect(screen.queryByText('Child component rendered successfully')).not.toBeInTheDocument();
    expect(consoleErrorMock).toHaveBeenCalledTimes(1); // Check if componentDidCatch was called
  });

  it('renders default fallback UI if no custom message is provided', () => {
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow />
      </ErrorBoundary>
    );
    expect(screen.getByText('Something went wrong. Please try refreshing the page or contact support if the issue persists.')).toBeInTheDocument();
  });

  it('shows error details in development mode', () => {
    const originalNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development'; // Simulate development environment
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow />
      </ErrorBoundary>
    );
    expect(screen.getByText('Error Details (Dev Mode)')).toBeInTheDocument();
    expect(screen.getByText(/Test error from ProblemChild/)).toBeInTheDocument(); // Check for error stack/message
    process.env.NODE_ENV = originalNodeEnv; // Restore original NODE_ENV
  });

  it('does not show error details in production mode', () => {
    const originalNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'production'; // Simulate production environment
     render(
      <ErrorBoundary>
        <ProblemChild shouldThrow />
      </ErrorBoundary>
    );
    expect(screen.queryByText('Error Details (Dev Mode)')).not.toBeInTheDocument();
    process.env.NODE_ENV = originalNodeEnv; // Restore original NODE_ENV
  });
});
