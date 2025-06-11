'use client';

import React, { useState, FormEvent } from 'react';
import {
  PaymentElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';
import { StripeError, StripePaymentElementOptions } from '@stripe/stripe-js';
import AlertMessage from '@/components/common/AlertMessage';

interface CheckoutFormProps {
  bookingId: string;
  paymentId: string;
}

const CheckoutForm: React.FC<CheckoutFormProps> = ({ bookingId, paymentId }) => {
  const stripe = useStripe();
  const elements = useElements();

  const [message, setMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [stripeError, setStripeError] = useState<StripeError | null>(null); // To store Stripe error object for typing

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStripeError(null); // Clear previous Stripe error object
    setMessage(null);     // Clear previous messages

    if (!stripe || !elements) {
      setMessage("Stripe.js has not loaded yet. Please wait a moment and try again.");
      return;
    }

    setIsProcessing(true);

    const returnUrl = `${window.location.origin}/payment-status?payment_id=${paymentId}&booking_id=${bookingId}`;

    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: returnUrl,
      },
    });

    if (error) {
      // This point will only be reached if there is an immediate error when
      // confirming the payment. Otherwise, customer will be redirected.
      setMessage(error.message || "An unexpected error occurred.");
      setStripeError(error); // Store the full error object
    } else if (paymentIntent && paymentIntent.status === 'succeeded') {
      // This case is unlikely to be hit if return_url is used correctly,
      // as Stripe will redirect. But handle for completeness.
      setMessage(`Payment Succeeded! Payment Intent ID: ${paymentIntent.id}. You should be redirected shortly.`);
    } else if (paymentIntent) {
      setMessage(`Payment status: ${paymentIntent.status}. You may be redirected or need further action.`);
    }
    // If no error and no specific paymentIntent status message, Stripe is likely redirecting.
    // A general message might not be needed here unless specifically handling non-redirect cases.

    setIsProcessing(false);
  };

  const paymentElementOptions: StripePaymentElementOptions = {
    layout: "tabs" // or "accordion", "auto"
  };

  return (
    <form id="payment-form" onSubmit={handleSubmit} className="space-y-6 py-4">
      <PaymentElement id="payment-element" options={paymentElementOptions} />
      <button
        disabled={isProcessing || !stripe || !elements}
        id="submit"
        className="w-full btn btn-primary" // Use new button styles
      >
        <span id="button-text">
          {isProcessing ? "Processing..." : "Pay now"}
        </span>
      </button>

      {/* Show any error or success messages */}
      {message &&
        <div className="mt-4">
          <AlertMessage
            message={message}
            type={stripeError ? 'error' : 'info'} // Determine type based on stripeError presence
          />
        </div>
      }
    </form>
  );
}

export default CheckoutForm;
