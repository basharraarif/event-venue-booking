import React from 'react';

interface AlertMessageProps {
  message: string;
  type: 'error' | 'success' | 'warning' | 'info';
}

const AlertMessage: React.FC<AlertMessageProps> = ({ message, type }) => {
  const baseClasses = 'p-4 rounded-md text-sm';
  let specificClasses = '';

  switch (type) {
    case 'error':
      specificClasses =
        'bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 border border-red-300 dark:border-red-700';
      break;
    case 'success':
      specificClasses =
        'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 border border-green-300 dark:border-green-700';
      break;
    case 'warning':
      specificClasses =
        'bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300 border border-yellow-300 dark:border-yellow-700';
      break;
    case 'info':
    default:
      specificClasses =
        'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700';
      break;
  }

  if (!message) return null;

  return (
    <div className={`${baseClasses} ${specificClasses}`} role="alert">
      {message}
    </div>
  );
};

export default AlertMessage;
