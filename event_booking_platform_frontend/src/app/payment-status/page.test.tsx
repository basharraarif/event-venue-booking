import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { useSearchParams } from 'next/navigation';
import { useStripe, Elements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import PaymentStatusPageWrapper from './page'; // The wrapper is the default export
import PaymentService from '@/services/PaymentService';

// Mocks
jest.mock('next/navigation', () => ({
  useSearchParams: jest.fn(),
  useRouter: jest.fn(() => ({ push: jest.fn() })),
}));

jest.mock('@stripe/react-stripe-js', () => ({
  ...jest.requireActual('@stripe/react-stripe-js'),
  useStripe: jest.fn(),
  Elements: ({ children }: { children: React.ReactNode }) => <div data-testid="stripe-elements-wrapper">{children}</div>,
}));

jest.mock('@/services/PaymentService');
jest.mock('@/components/common/LoadingSpinner', () => ({ message }: { message: string }) => <div data-testid="loading-spinner">{message}</div>);
jest.mock('@/components/common/AlertMessage', () => ({ message, type }: { message: string, type: string }) => <div data-testid="alert-message" data-type={type}>{message}</div>);

const mockUseSearchParams = useSearchParams as jest.Mock;
const mockUseStripe = useStripe as jest.Mock;
const mockPaymentService = PaymentService as jest.Mocked<typeof PaymentService>;

// A dummy Stripe promise for the Elements wrapper in the test environment
const stripePromise = loadStripe('pk_test_dummykey_for_payment_status_tests');


describe('PaymentStatusPageWrapper (including PaymentStatusPage)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default Stripe mock setup
    mockUseStripe.mockReturnValue({
      retrievePaymentIntent: jest.fn(),
    });
  });

  it('renders loading state initially', () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams()); // No params, will show loading then error
    render(<PaymentStatusPageWrapper />);
    expect(screen.getByTestId('loading-spinner')).toHaveTextContent('Verifying payment status...');
  });

  it('shows error if essential URL parameters are missing', async () => {
    mockUseSearchParams.mockReturnValue(new URLSearchParams()); // No params
    render(<PaymentStatusPageWrapper />);
    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Required payment information is missing from the URL.');
      expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'error');
    });
  });

  it('handles successful payment via Stripe.js retrievePaymentIntent', async () => {
    const mockStripe = {
      retrievePaymentIntent: jest.fn().mockResolvedValue({
        paymentIntent: { status: 'succeeded', id: 'pi_success' },
      }),
    };
    mockUseStripe.mockReturnValue(mockStripe);
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_intent_client_secret=cs_test&payment_id=local_pay_123&booking_id=booking789"
    ));

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(mockStripe.retrievePaymentIntent).toHaveBeenCalledWith('cs_test');
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Payment successful! Your booking is confirmed.');
      expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'success');
      expect(screen.getByText('View My Bookings')).toBeInTheDocument();
    });
  });

  it('handles processing payment via Stripe.js retrievePaymentIntent', async () => {
    const mockStripe = {
      retrievePaymentIntent: jest.fn().mockResolvedValue({
        paymentIntent: { status: 'processing', id: 'pi_processing' },
      }),
    };
    mockUseStripe.mockReturnValue(mockStripe);
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_intent_client_secret=cs_test_proc&payment_id=local_pay_proc&booking_id=booking_proc"
    ));

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Payment processing. We will update you when payment is received.');
      expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'success'); // Info/success for processing
    });
  });

  it('handles failed payment (requires_payment_method) via Stripe.js retrievePaymentIntent', async () => {
    const mockStripe = {
      retrievePaymentIntent: jest.fn().mockResolvedValue({
        paymentIntent: { status: 'requires_payment_method', id: 'pi_fail' },
      }),
    };
    mockUseStripe.mockReturnValue(mockStripe);
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_intent_client_secret=cs_test_fail&payment_id=local_pay_fail&booking_id=booking_fail"
    ));

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Payment requires further action or failed. Please try again or contact support.');
      expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'error');
      expect(screen.getByText('Try Payment Again')).toBeInTheDocument();
    });
  });

  it('handles successful payment via backend getPaymentDetails fallback', async () => {
    mockUseStripe.mockReturnValue(null); // Simulate Stripe.js not loaded or no client_secret
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_id=local_pay_backend_succ&booking_id=booking_backend_succ"
    ));
    mockPaymentService.getPaymentDetails.mockResolvedValue({
      id: 'local_pay_backend_succ',
      status: 'succeeded', // Ensure this matches one of the expected values in component
      // ... other payment fields
    } as any);

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(mockPaymentService.getPaymentDetails).toHaveBeenCalledWith('local_pay_backend_succ');
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Payment successful! Your booking is confirmed.');
    });
  });

  it('handles failed payment via backend getPaymentDetails fallback', async () => {
    mockUseStripe.mockReturnValue(null);
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_id=local_pay_backend_fail&booking_id=booking_backend_fail"
    ));
    mockPaymentService.getPaymentDetails.mockResolvedValue({
      id: 'local_pay_backend_fail',
      status: 'failed',
    } as any);

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Payment failed or was cancelled. Please try again or contact support.');
      expect(screen.getByTestId('alert-message')).toHaveAttribute('data-type', 'error');
    });
  });

  it('handles error when Stripe.js retrievePaymentIntent fails', async () => {
    const mockStripe = {
      retrievePaymentIntent: jest.fn().mockRejectedValue(new Error("Stripe API Error")),
    };
    mockUseStripe.mockReturnValue(mockStripe);
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_intent_client_secret=cs_test_api_error&payment_id=local_pay_api_error&booking_id=booking_api_error"
    ));

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Error verifying payment status with Stripe.');
    });
  });

  it('handles error when backend getPaymentDetails fails', async () => {
    mockUseStripe.mockReturnValue(null); // Ensure fallback is used
    mockUseSearchParams.mockReturnValue(new URLSearchParams(
      "?payment_id=local_pay_backend_error&booking_id=booking_backend_error"
    ));
    mockPaymentService.getPaymentDetails.mockRejectedValue(new Error("Backend API Error"));

    render(<PaymentStatusPageWrapper />);

    await waitFor(() => {
      expect(screen.getByTestId('alert-message')).toHaveTextContent('Could not retrieve payment status from our records.');
    });
  });

});
