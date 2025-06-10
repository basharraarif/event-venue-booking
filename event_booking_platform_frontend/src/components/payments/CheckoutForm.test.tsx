import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Elements, useStripe, useElements } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import CheckoutForm from './CheckoutForm';

// Mock Stripe hooks
jest.mock('@stripe/react-stripe-js', () => ({
  ...jest.requireActual('@stripe/react-stripe-js'), // import and retain default behavior
  useStripe: jest.fn(),
  useElements: jest.fn(),
  PaymentElement: () => <div data-testid="payment-element">Mocked Payment Element</div>, // Mock PaymentElement
}));

const mockStripe = {
  confirmPayment: jest.fn(),
};

const mockElements = {
  getElement: jest.fn(),
};

// Load a dummy Stripe instance for the Elements provider
const stripePromise = loadStripe('pk_test_dummykey'); // Replace with your actual dummy key if needed for tests

describe('CheckoutForm', () => {
  beforeEach(() => {
    // Reset mocks for each test
    (useStripe as jest.Mock).mockReturnValue(mockStripe);
    (useElements as jest.Mock).mockReturnValue(mockElements);
    mockStripe.confirmPayment.mockReset();
  });

  it('renders the payment element and submit button', () => {
    render(
      <Elements stripe={stripePromise}>
        <CheckoutForm bookingId="booking123" paymentId="payment123" />
      </Elements>
    );

    expect(screen.getByTestId('payment-element')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /pay now/i })).toBeInTheDocument();
  });

  it('disables button and shows processing text during submission', async () => {
    mockStripe.confirmPayment.mockResolvedValueOnce({ error: null, paymentIntent: { status: 'succeeded' } });

    render(
      <Elements stripe={stripePromise}>
        <CheckoutForm bookingId="booking123" paymentId="payment123" />
      </Elements>
    );

    const submitButton = screen.getByRole('button', { name: /pay now/i });
    fireEvent.click(submitButton);

    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/processing.../i)).toBeInTheDocument();

    // Wait for the mock submission to complete
    await waitFor(() => expect(submitButton).not.toBeDisabled());
  });

  it('calls stripe.confirmPayment on submit', async () => {
    mockStripe.confirmPayment.mockResolvedValueOnce({ error: null, paymentIntent: { status: 'succeeded', id: 'pi_123' } });

    render(
      <Elements stripe={stripePromise}>
        <CheckoutForm bookingId="booking123" paymentId="payment123" />
      </Elements>
    );

    fireEvent.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(mockStripe.confirmPayment).toHaveBeenCalledWith({
        elements: mockElements,
        confirmParams: {
          return_url: `${window.location.origin}/payment-status?payment_id=payment123&booking_id=booking123`,
        },
      });
    });
  });

  it('displays error message if confirmPayment fails', async () => {
    const errorMessage = 'Your card was declined.';
    mockStripe.confirmPayment.mockResolvedValueOnce({
      error: { type: 'card_error', message: errorMessage }
    });

    render(
      <Elements stripe={stripePromise}>
        <CheckoutForm bookingId="booking123" paymentId="payment123" />
      </Elements>
    );

    fireEvent.click(screen.getByRole('button', { name: /pay now/i }));

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('shows message if stripe or elements not loaded', async () => {
    (useStripe as jest.Mock).mockReturnValueOnce(null); // Simulate Stripe not loaded
    render(
      <Elements stripe={stripePromise}>
        <CheckoutForm bookingId="booking123" paymentId="payment123" />
      </Elements>
    );

    fireEvent.click(screen.getByRole('button', { name: /pay now/i }));
    await waitFor(() => {
        expect(screen.getByText(/Stripe.js has not loaded yet/i)).toBeInTheDocument();
    });
  });

});
