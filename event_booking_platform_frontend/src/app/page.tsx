'use client'; // Required for using client-side features like Link and router if needed

import Link from 'next/link';

export default function Home() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  // Mock booking data for demonstration
  const mockBookings = [
    {
      id: 'b09a9a59-1920-47c7-ba09-3c0a6d8459a2',
      eventName: 'Tech Conference 2024',
      status: 'pending',
      price: 100.0,
    },
    {
      id: 'c11b8b22-1234-5678-bdef-3c0a6d1234b3',
      eventName: 'Music Festival Extravaganza',
      status: 'confirmed',
      price: 75.5,
    },
    // Add more mock bookings if you want
  ];

  return (
    <main className="flex min-h-screen flex-col items-center p-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Welcome to the Event Booking Platform
        </h1>
        <p className="text-lg mb-2">This is a basic Next.js frontend.</p>
        <p className="text-md text-gray-700 dark:text-gray-400">
          The API base URL is configured to:{' '}
          <code className="font-mono bg-gray-200 dark:bg-gray-700 p-1 rounded">
            {apiBaseUrl || 'Not set'}
          </code>
        </p>
      </div>

      <div className="w-full max-w-2xl">
        <h2 className="text-2xl font-semibold mb-4">
          Your Bookings (Mock Data)
        </h2>
        {mockBookings.length === 0 ? (
          <p>You have no bookings yet.</p>
        ) : (
          <ul className="space-y-4">
            {mockBookings.map((booking) => (
              <li
                key={booking.id}
                className="p-4 border rounded-lg shadow-sm bg-white dark:bg-gray-800"
              >
                <h3 className="text-xl font-medium text-gray-900 dark:text-white">
                  {booking.eventName}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Status:{' '}
                  <span
                    className={`font-semibold ${booking.status === 'pending' ? 'text-yellow-600' : 'text-green-600'}`}
                  >
                    {booking.status}
                  </span>
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Price: ${booking.price.toFixed(2)}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Booking ID: {booking.id}
                </p>
                {booking.status === 'pending' && (
                  <div className="mt-3">
                    <Link href={`/checkout/${booking.id}`} legacyBehavior>
                      <a className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50">
                        Pay Now
                      </a>
                    </Link>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
