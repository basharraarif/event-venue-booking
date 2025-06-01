export default function Home() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="text-center">
        <h1 className="text-4xl font-bold mb-4">Welcome to the Event Booking Platform</h1>
        <p className="text-lg mb-2">
          This is a basic Next.js frontend.
        </p>
        <p className="text-md text-gray-700 dark:text-gray-400">
          The API base URL is configured to: <code className="font-mono bg-gray-200 dark:bg-gray-700 p-1 rounded">{apiBaseUrl || "Not set"}</code>
        </p>
        <p className="mt-4 text-sm text-gray-500">
          (This value is read from <code className="font-mono">NEXT_PUBLIC_API_BASE_URL</code> environment variable)
        </p>
      </div>
    </main>
  );
}
