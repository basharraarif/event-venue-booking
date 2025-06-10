'use client';

import React, { useState, FormEvent } from 'react';
import {
  PaymentElement,
  useStripe,
  useElements
} from '@stripe/react-stripe-js';
import { StripePaymentElementOptions } from '@stripe/stripe-js';

interface CheckoutFormProps {
  bookingId: string;
  paymentId: string;
}

const CheckoutForm: React.FC<CheckoutFormProps> = ({ bookingId, paymentId }) => {
  const stripe = useStripe();
  const elements = useElements();

  const [message, setMessage] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!stripe || !elements) {
      // Stripe.js has not yet loaded.
      // Make sure to disable form submission until Stripe.js has loaded.
      setMessage("Stripe.js has not loaded yet. Please wait a moment and try again.");
      return;
    }

    setIsProcessing(true);
    setMessage(null); // Clear previous messages

    // TODO: Construct the return_url more dynamically if needed,
    // for example, by using window.location.origin
    const returnUrl = `${window.location.origin}/payment-status?payment_id=${paymentId}&booking_id=${bookingId}`;


    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        // Make sure to change this to your payment completion page
        return_url: returnUrl,
      },
    });

    // This point will only be reached if there is an immediate error when
    // confirming the payment. Otherwise, your customer will be redirected to
    // your `return_url`. For some payment methods like iDEAL, your customer will
    // be redirected to an intermediate site first to authorize the payment, then
    // redirected to the `return_url`.
    if (error) {
      if (error.type === "card_error" || error.type === "validation_error") {
        setMessage(error.message || "An error occurred with your card.");
      } else {
        setMessage("An unexpected error occurred.");
      }
    } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        // This case is unlikely to be hit if return_url is used correctly,
        // as Stripe will redirect. But handle for completeness / alternative flows.
        setMessage(`Payment Succeeded! Payment Intent ID: ${paymentIntent.id}. You should be redirected shortly.`);
        // Potentially redirect here if not relying on Stripe's redirect, or update UI
        // window.location.href = `/payment-success?payment_intent_id=${paymentIntent.id}`;
    } else if (paymentIntent) {
        setMessage(`Payment status: ${paymentIntent.status}. You may be redirected.`);
    }


    setIsProcessing(false);
  };

  const paymentElementOptions: StripePaymentElementOptions = {
    layout: "tabs" // or "accordion", "auto"
  };

  return (
    <form id="payment-form" onSubmit={handleSubmit}>
      <PaymentElement id="payment-element" options={paymentElementOptions} />
      <button
        disabled={isProcessing || !stripe || !elements}
        id="submit"
        className="mt-4 w-full bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50"
      >
        <span id="button-text">
          {isProcessing ? "Processing..." : "Pay now"}
        </span>
      </button>
      {/* Show any error or success messages */}
      {message && <div id="payment-message" className="mt-4 text-sm text-red-600">{message}</div>}
    </form>
  );
}

export default CheckoutForm;
