'use client';

import React, { ReactNode } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import LoadingSpinner from '@/components/common/LoadingSpinner';
import AlertMessage from '@/components/common/AlertMessage';

interface RoleRequiredProps {
  children: ReactNode;
  requiredRoles: string[] | string; // Can be a single role string or an array of roles
  fallbackUrl?: string; // Optional URL to redirect if unauthorized
  showError?: boolean; // Optional: show an error message instead of redirect or nothing
}

const RoleRequired: React.FC<RoleRequiredProps> = ({ children, requiredRoles, fallbackUrl = '/', showError = false }) => {
  const { user, isAuthenticated, isLoading, hasRole } = useAuth();
  const router = useRouter();

  if (isLoading) {
    return <LoadingSpinner message="Authenticating..." />;
  }

  if (!isAuthenticated) {
    // Not using useEffect for redirect here to avoid flash of content if possible,
    // but Next.js app router might require useEffect for router.push during render.
    // For client components, direct call in render phase is often discouraged.
    // However, for guards, this is a common pattern if handled carefully.
    // Alternative: return a redirect component or use middleware for route protection.
    if (typeof window !== 'undefined') { // Ensure it runs only on client
        router.push(fallbackUrl);
    }
    return <LoadingSpinner message="Redirecting..." />; // Or null, or a specific "Redirecting" component
  }

  const rolesToCheck = Array.isArray(requiredRoles) ? requiredRoles : [requiredRoles];
  const userHasRequiredRole = rolesToCheck.some(role => hasRole(role));

  if (!userHasRequiredRole) {
    if (showError) {
      return (
        <div className="container mx-auto p-4 text-center">
          <AlertMessage
            message="You are not authorized to view this page."
            type="error"
          />
          {/* Optionally, provide a link to go back or to homepage */}
        </div>
      );
    }
    if (typeof window !== 'undefined') {
        router.push(fallbackUrl);
    }
    return <LoadingSpinner message="Redirecting..." />; // Or null
  }

  return <>{children}</>;
};

export default RoleRequired;

// Example Usage in a page:
//
// import RoleRequired from '@/components/auth/RoleRequired';
// import { Role } from '@/config/roles'; // Assuming you have a roles enum/constants
//
// const AdminDashboardPage = () => {
//   return (
//     <RoleRequired requiredRoles={[Role.ADMIN]} showError={true}>
//       <div>
//         <h1>Admin Dashboard</h1>
//         {/* Admin content here */}
//       </div>
//     </RoleRequired>
//   );
// };
// export default AdminDashboardPage;
//
// For a single role:
// <RoleRequired requiredRoles={Role.EVENT_ORGANIZER}> ... </RoleRequired>
//
// Note on redirection during render:
// Next.js App Router best practices for redirection from client components are evolving.
// Using `useEffect` for router.push is safer to prevent issues during React's render phase.
// If problems arise (e.g. "Cannot update a component while rendering a different component"),
// the router.push calls should be moved into a useEffect hook:
//
// useEffect(() => {
//   if (!isLoading && !isAuthenticated) {
//     router.push(fallbackUrl);
//   } else if (!isLoading && isAuthenticated && !userHasRequiredRole) {
//     router.push(fallbackUrl);
//   }
// }, [isLoading, isAuthenticated, userHasRequiredRole, fallbackUrl, router]);
//
// If using useEffect, the component would return null or a loader while redirecting.
// For this implementation, direct router.push is used for immediate effect,
// assuming it's within a client component context where it's acceptable or
// that Next.js handles it gracefully. A <Redirect> component is another pattern.
// For now, this direct approach is chosen for simplicity in the guard pattern.
// The `typeof window !== 'undefined'` check is a safeguard.
