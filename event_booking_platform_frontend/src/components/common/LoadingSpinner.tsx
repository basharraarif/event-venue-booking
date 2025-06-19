import React from 'react';

const LoadingSpinner: React.FC<{ message?: string }> = ({
  message = 'Loading...',
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-10">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-600 dark:border-indigo-400"></div>
      <p className="mt-3 text-lg text-gray-600 dark:text-gray-300">{message}</p>
    </div>
  );
};

export default LoadingSpinner;
