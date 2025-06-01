import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from 'next/link';
import "./globals.css"; // Make sure this path is correct
import { AuthProvider } from '../contexts/AuthContext'; // Import AuthProvider
import AuthNav from '../components/layout/AuthNav'; // Import AuthNav

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: 'Event Booking Platform Bangladesh', // Default title
    template: '%s | Event Booking Platform BD', // Template for page-specific titles
  },
  description: 'Your go-to platform for booking venues for events in Bangladesh.',
  // Add other global meta tags like viewport, theme-color etc.
  // openGraph: {
  //   type: 'website',
  //   locale: 'en_BD', // Adjusted locale
  //   url: 'https://www.yourdomain.com.bd', // Placeholder domain
  //   siteName: 'Event Booking Platform BD',
  // },
  // twitter: {
  //   card: 'summary_large_image',
  // },
  viewport: 'width=device-width, initial-scale=1',
  // themeColor: '#ffffff', // Example theme color
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-100 flex flex-col min-h-screen`}>
        <AuthProvider>
          <header className="bg-white shadow-md">
            <nav className="container mx-auto px-6 py-3 flex justify-between items-center">
              <Link href="/" className="text-xl font-semibold text-gray-700">
                EventPlatformBD
              </Link>
              <div className="flex items-center space-x-4">
                <Link href="/" className="text-gray-700 hover:text-blue-600 px-3 py-2">
                  Home
                </Link>
                <Link href="/venues" className="text-gray-700 hover:text-blue-600 px-3 py-2">
                  Venues
                </Link>
                {/* Future links: e.g., My Bookings, Profile */}
                <AuthNav /> {/* Auth links (Login/Register or User/Logout) */}
              </div>
            </nav>
          </header>

          <main className="flex-grow container mx-auto px-4 py-8">
            {children}
          </main>

          <footer className="bg-white shadow-md py-6 text-center mt-auto">
            <p className="text-gray-600 text-sm">
              &copy; {new Date().getFullYear()} Event Booking Platform BD. All rights reserved.
            </p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
