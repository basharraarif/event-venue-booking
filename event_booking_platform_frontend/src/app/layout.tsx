import type { Metadata } from "next";
import type { Metadata } from "next"; // Ensure Metadata is imported if not already
import { Inter } from "next/font/google";
import Link from 'next/link';
import "./globals.css";
// import { AuthProvider, useAuth } from '../contexts/AuthContext'; // Step 1: Comment out
// import AuthNav from '../components/layout/AuthNav';
import ErrorBoundary from '@/components/common/ErrorBoundary';

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: 'Event Booking Platform Bangladesh', // Default title
    template: '%s | Event Booking Platform BD', // Template for page-specific titles
  },
  description: 'Your go-to platform for booking venues for events in Bangladesh.',
  viewport: 'width=device-width, initial-scale=1',
};

// Step 1: Comment out AppHeader
// const AppHeader = () => {
//   const { isAuthenticated } = useAuth();
//
//   return (
//     <header className="bg-white shadow-md dark:bg-gray-800">
//       <nav className="container mx-auto px-6 py-3 flex justify-between items-center">
//         <Link href="/" className="text-xl font-semibold text-gray-700 dark:text-white">
//           EventPlatformBD
//         </Link>
//         <div className="flex items-center space-x-2 md:space-x-4">
//           <Link href="/" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">
//             Home
//           </Link>
//           <Link href="/venues" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">
//             Venues
//           </Link>
//           <Link href="/events" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">
//             Events
//           </Link>
//           {isAuthenticated && (
//             <Link href="/dashboard" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">
//               Dashboard
//             </Link>
//           )}
//           <AuthNav />
//         </div>
//       </nav>
//     </header>
//   );
// };

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col min-h-screen`}>
        {/* <AuthProvider> */} {/* Step 1: Comment out AuthProvider */}
          {/* <AppHeader /> */} {/* Step 1: Comment out AppHeader */}
          <ErrorBoundary fallbackMessage="A critical error occurred in the application.">
            <header className="bg-white shadow-md dark:bg-gray-800"> {/* Basic Header */}
              <nav className="container mx-auto px-6 py-3 flex justify-between items-center">
                <Link href="/" className="text-xl font-semibold text-gray-700 dark:text-white">EventPlatformBD</Link>
                <div className="flex items-center space-x-2 md:space-x-4">
                <Link href="/" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">Home</Link>
                <Link href="/venues" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">Venues</Link>
                <Link href="/events" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">Events</Link>
                {/* Basic login/register links if AuthNav is part of the issue */}
                <Link href="/login" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">Login</Link>
                <Link href="/register" className="text-gray-700 dark:text-gray-200 hover:text-blue-600 dark:hover:text-blue-400 px-3 py-2">Register</Link>
              </div>
            </nav>
          </header>
          <main className="flex-grow container mx-auto px-4 py-8">
            {children}
          </main>
          <footer className="bg-white dark:bg-gray-800 shadow-md py-6 text-center mt-auto">
            <p className="text-gray-600 dark:text-gray-300 text-sm">
              &copy; {new Date().getFullYear()} Event Booking Platform BD. All rights reserved.
            </p>
          </footer>
          </ErrorBoundary>
        {/* </AuthProvider> */} {/* Step 1: Comment out AuthProvider */}
      </body>
    </html>
  );
}
