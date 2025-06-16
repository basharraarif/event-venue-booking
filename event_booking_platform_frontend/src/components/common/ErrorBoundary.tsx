// src/components/common/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';
import AlertMessage from './AlertMessage'; // Assuming AlertMessage can display generic errors

interface Props {
  children: ReactNode;
  fallbackMessage?: string;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
    // You could also log the error to an error reporting service here
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-4">
          <AlertMessage
            type="error"
            message={this.props.fallbackMessage || "Something went wrong. Please try refreshing the page or contact support if the issue persists."}
          />
          {/* Optional: Display error details in dev mode */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="mt-2 text-xs text-gray-500">
              <summary>Error Details (Dev Mode)</summary>
              <pre>{this.state.error.stack}</pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
