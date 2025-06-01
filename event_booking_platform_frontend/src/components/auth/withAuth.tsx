'use client';

import React, { ComponentType, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../contexts/AuthContext'; // Adjust path

const withAuth = <P extends object>(WrappedComponent: ComponentType<P>) => {
  const ComponentWithAuth = (props: P) => {
    const { isAuthenticated, isLoading, token } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        router.replace('/login'); // Use replace to avoid adding to history stack
      }
    }, [isLoading, isAuthenticated, router]);

    // Display a loading state while checking authentication
    if (isLoading || (!isAuthenticated && token)) { // also show loading if token exists but user not yet confirmed
      return (
        <div className="flex justify-center items-center min-h-screen">
          <p className="text-xl">Loading authentication...</p>
        </div>
      );
    }

    // If authenticated, render the wrapped component
    if (isAuthenticated) {
      return <WrappedComponent {...props} />;
    }

    // If not authenticated and not loading (should have been redirected, but as a fallback)
    return null; // Or a custom "Access Denied" component, though redirect is preferred
  };

  // Assign a display name for easier debugging in React DevTools
  ComponentWithAuth.displayName = `WithAuth(${WrappedComponent.displayName || WrappedComponent.name || 'Component'})`;

  return ComponentWithAuth;
};

export default withAuth;
